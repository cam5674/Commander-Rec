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
            "MemorySize": 1769,
            "Timeout": 10,
            "Environment": {
                "Variables": {
                    "REFERENCE_DATA_DIR": "data/processed",
                    "ALLOWED_ORIGINS": (
                        "http://localhost:5173,http://127.0.0.1:5173"
                    ),
                    "MAX_UPLOAD_BYTES": "4194304",
                    "ENABLE_API_DOCS": "false",
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
                "DetailedMetricsEnabled": False,
                "ThrottlingBurstLimit": 20,
                "ThrottlingRateLimit": 10,
            },
            "AccessLogSettings": {
                "DestinationArn": assertions.Match.any_value(),
                "Format": assertions.Match.any_value(),
            },
        },
    )
    template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {
            "LogGroupName": "/aws/apigateway/commander-rec-cdk-api",
            "RetentionInDays": 14,
        },
    )

    stages = template.find_resources("AWS::ApiGatewayV2::Stage")
    access_log_format = next(iter(stages.values()))["Properties"][
        "AccessLogSettings"
    ]["Format"]
    for forbidden_field in ("body", "filename", "header", "query"):
        assert forbidden_field not in access_log_format.casefold()


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
                            "ResponseHeadersPolicyId": (
                                "67f7725c-6f97-4210-82d7-5512b31e9d03"
                            ),
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
        "AlertTopicArn",
    ):
        template.has_output(output_name, {})


def test_alert_topic_and_email_subscription() -> None:
    template = synthesize_template()

    template.has_parameter(
        "AlertEmail",
        {
            "Type": "String",
            "Description": "Email address for Commander Rec operational alerts",
            "NoEcho": True,
        },
    )
    template.has_resource_properties(
        "AWS::SNS::Topic",
        {
            "TopicName": "commander-rec-cdk-alerts",
            "DisplayName": "Commander Rec operational alerts",
        },
    )
    template.has_resource_properties(
        "AWS::SNS::Subscription",
        {
            "Protocol": "email",
            "Endpoint": {"Ref": "AlertEmail"},
        },
    )


def test_operational_alarms_notify_without_automated_remediation() -> None:
    template = synthesize_template()
    alarms = template.find_resources("AWS::CloudWatch::Alarm")

    assert len(alarms) == 7
    alarm_properties = [alarm["Properties"] for alarm in alarms.values()]
    assert {
        alarm["AlarmName"]
        for alarm in alarm_properties
    } == {
        "commander-rec-cdk-lambda-invocation-spike",
        "commander-rec-cdk-lambda-throttles",
        "commander-rec-cdk-lambda-errors",
        "commander-rec-cdk-lambda-duration-p95",
        "commander-rec-cdk-api-request-volume",
        "commander-rec-cdk-api-client-errors",
        "commander-rec-cdk-api-server-errors",
    }
    assert all(len(alarm["AlarmActions"]) == 1 for alarm in alarm_properties)
    assert all(
        alarm["TreatMissingData"] == "notBreaching"
        for alarm in alarm_properties
    )

    invocation_alarm = next(
        alarm
        for alarm in alarm_properties
        if alarm["AlarmName"]
        == "commander-rec-cdk-lambda-invocation-spike"
    )
    assert invocation_alarm["MetricName"] == "Invocations"
    assert invocation_alarm["Threshold"] == 300
    assert invocation_alarm["EvaluationPeriods"] == 2
    assert invocation_alarm["DatapointsToAlarm"] == 2
    assert invocation_alarm["ComparisonOperator"] == "GreaterThanThreshold"

    duration_alarm = next(
        alarm
        for alarm in alarm_properties
        if alarm["AlarmName"] == "commander-rec-cdk-lambda-duration-p95"
    )
    assert duration_alarm["ExtendedStatistic"] == "p95"
    assert duration_alarm["Threshold"] == 8000
    assert duration_alarm["EvaluateLowSampleCountPercentile"] == "ignore"

    request_volume_alarm = next(
        alarm
        for alarm in alarm_properties
        if alarm["AlarmName"] == "commander-rec-cdk-api-request-volume"
    )
    assert request_volume_alarm["Namespace"] == "AWS/ApiGateway"
    assert request_volume_alarm["MetricName"] == "Count"
    assert request_volume_alarm["Threshold"] == 600
    assert request_volume_alarm["EvaluationPeriods"] == 2
    assert request_volume_alarm["DatapointsToAlarm"] == 2

    functions = template.find_resources("AWS::Lambda::Function")
    api_function = next(
        function["Properties"]
        for function in functions.values()
        if function["Properties"].get("FunctionName")
        == "commander-rec-cdk-api"
    )
    assert "ReservedConcurrentExecutions" not in api_function
    assert "remediation" not in str(template.to_json()).casefold()
