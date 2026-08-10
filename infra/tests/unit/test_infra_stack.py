import aws_cdk as cdk
from aws_cdk import assertions, aws_lambda as lambda_

from infra.infra_stack import InfraStack


def synthesize_template() -> assertions.Template:
    app = cdk.App()
    stack = InfraStack(
        app,
        "TestStack",
        api_code=lambda_.Code.from_inline(
            "def handler(event, context):\n    return {'statusCode': 200}\n"
        ),
    )
    return assertions.Template.from_stack(stack)


def test_lambda_configuration_and_logs() -> None:
    template = synthesize_template()

    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "FunctionName": "commander-rec-cdk-api",
            "Runtime": "python3.12",
            "Architectures": ["arm64"],
            "Handler": "backend.lambda_handler.handler",
            "MemorySize": 1024,
            "Timeout": 10,
            "Environment": {
                "Variables": {
                    "REFERENCE_DATA_DIR": "data/processed",
                    "ALLOWED_ORIGINS": (
                        "http://localhost:5173,http://127.0.0.1:5173"
                    ),
                    "MAX_UPLOAD_BYTES": "4194304",
                }
            },
        },
    )
    template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {
            "LogGroupName": "/aws/lambda/commander-rec-cdk-api",
            "RetentionInDays": 14,
        },
    )


def test_http_api_routes_and_throttling() -> None:
    template = synthesize_template()

    template.has_resource_properties(
        "AWS::ApiGatewayV2::Route",
        {"RouteKey": "GET /config"},
    )
    template.has_resource_properties(
        "AWS::ApiGatewayV2::Route",
        {"RouteKey": "POST /recommendations"},
    )
    template.has_resource_properties(
        "AWS::ApiGatewayV2::Stage",
        {
            "StageName": "$default",
            "AutoDeploy": True,
            "DefaultRouteSettings": {
                "ThrottlingBurstLimit": 20,
                "ThrottlingRateLimit": 10,
            },
        },
    )


def test_private_frontend_bucket_and_origin_access_control() -> None:
    template = synthesize_template()

    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {
                        "ServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            },
            "OwnershipControls": {
                "Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
        },
    )
    template.has_resource_properties(
        "AWS::CloudFront::OriginAccessControl",
        {
            "OriginAccessControlConfig": {
                "OriginAccessControlOriginType": "s3",
                "SigningBehavior": "always",
                "SigningProtocol": "sigv4",
            }
        },
    )


def test_cloudfront_routes_frontend_and_api() -> None:
    template = synthesize_template()

    template.has_resource_properties(
        "AWS::CloudFront::Function",
        {
            "Name": "commander-rec-cdk-strip-api-prefix",
            "FunctionConfig": {
                "Comment": assertions.Match.any_value(),
                "Runtime": "cloudfront-js-2.0",
            },
            "FunctionCode": assertions.Match.string_like_regexp(
                "request\\.uri\\.substring\\(4\\)"
            ),
        },
    )
    template.has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": assertions.Match.object_like(
                {
                    "DefaultRootObject": "index.html",
                    "PriceClass": "PriceClass_100",
                    "DefaultCacheBehavior": assertions.Match.object_like(
                        {
                            "AllowedMethods": ["GET", "HEAD"],
                            "Compress": True,
                            "ViewerProtocolPolicy": "redirect-to-https",
                        }
                    ),
                    "CacheBehaviors": assertions.Match.array_with(
                        [
                            assertions.Match.object_like(
                                {
                                    "PathPattern": "/api/*",
                                    "AllowedMethods": [
                                        "GET",
                                        "HEAD",
                                        "OPTIONS",
                                        "PUT",
                                        "PATCH",
                                        "POST",
                                        "DELETE",
                                    ],
                                    "CachePolicyId": (
                                        "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
                                    ),
                                    "OriginRequestPolicyId": (
                                        "b689b0a8-53d0-40ab-baf2-68738e2966ac"
                                    ),
                                    "Compress": True,
                                    "ViewerProtocolPolicy": "redirect-to-https",
                                    "FunctionAssociations": assertions.Match.array_with(
                                        [
                                            assertions.Match.object_like(
                                                {"EventType": "viewer-request"}
                                            )
                                        ]
                                    ),
                                }
                            )
                        ]
                    ),
                }
            )
        },
    )


def test_frontend_cache_controls_and_outputs() -> None:
    template = synthesize_template()

    template.has_resource_properties(
        "Custom::CDKBucketDeployment",
        {"SystemMetadata": {"cache-control": "no-cache"}},
    )
    template.has_resource_properties(
        "Custom::CDKBucketDeployment",
        {
            "SystemMetadata": {
                "cache-control": "public,max-age=31536000,immutable"
            }
        },
    )
    for output_name in (
        "CloudFrontUrl",
        "CloudFrontDistributionId",
        "FrontendBucketName",
        "ApiUrl",
        "LambdaFunctionName",
    ):
        template.has_output(output_name, {})
