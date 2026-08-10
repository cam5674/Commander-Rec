from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_integrations,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as cloudfront_origins,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
)
from constructs import Construct


class InfraStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        api_code: lambda_.Code | None = None,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        repository_root = Path(__file__).resolve().parents[2]
        frontend_dist = repository_root / "frontend" / "dist"

        if not frontend_dist.joinpath("index.html").is_file():
            raise FileNotFoundError(
                "frontend/dist/index.html is missing; run npm run build in frontend first"
            )

        function_role = iam.Role(
            self,
            "ApiFunctionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        function_log_group = logs.LogGroup(
            self,
            "ApiFunctionLogGroup",
            log_group_name="/aws/lambda/commander-rec-cdk-api",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.RETAIN,
        )

        if api_code is None:
            api_code = lambda_.Code.from_docker_build(
                str(repository_root),
                file="infra/lambda.Dockerfile",
                image_path="/asset",
                platform="linux/arm64",
            )

        api_function = lambda_.Function(
            self,
            "ApiFunction",
            function_name="commander-rec-cdk-api",
            runtime=lambda_.Runtime.PYTHON_3_12,
            architecture=lambda_.Architecture.ARM_64,
            handler="backend.lambda_handler.handler",
            code=api_code,
            memory_size=1024,
            timeout=Duration.seconds(10),
            role=function_role,
            log_group=function_log_group,
            environment={
                "REFERENCE_DATA_DIR": "data/processed",
                "ALLOWED_ORIGINS": (
                    "http://localhost:5173,http://127.0.0.1:5173"
                ),
                "MAX_UPLOAD_BYTES": "4194304",
            },
        )

        http_api = apigwv2.HttpApi(
            self,
            "HttpApi",
            api_name="commander-rec-cdk-api",
            create_default_stage=False,
        )
        api_integration = apigwv2_integrations.HttpLambdaIntegration(
            "ApiIntegration",
            api_function,
            scope_permission_to_route=False,
        )
        http_api.add_routes(
            path="/config",
            methods=[apigwv2.HttpMethod.GET],
            integration=api_integration,
        )
        http_api.add_routes(
            path="/recommendations",
            methods=[apigwv2.HttpMethod.POST],
            integration=api_integration,
        )
        apigwv2.HttpStage(
            self,
            "DefaultStage",
            http_api=http_api,
            stage_name="$default",
            auto_deploy=True,
            throttle=apigwv2.ThrottleSettings(
                rate_limit=10,
                burst_limit=20,
            ),
        )

        frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            removal_policy=RemovalPolicy.RETAIN,
            auto_delete_objects=False,
        )

        strip_api_prefix = cloudfront.Function(
            self,
            "StripApiPrefixFunction",
            function_name="commander-rec-cdk-strip-api-prefix",
            runtime=cloudfront.FunctionRuntime.JS_2_0,
            code=cloudfront.FunctionCode.from_inline(
                """function handler(event) {
    var request = event.request;
    if (request.uri.indexOf('/api/') === 0) {
        request.uri = request.uri.substring(4);
    }
    return request;
}
"""
            ),
        )

        api_domain_name = (
            f"{http_api.http_api_id}.execute-api."
            f"{Stack.of(self).region}.{Stack.of(self).url_suffix}"
        )
        distribution = cloudfront.Distribution(
            self,
            "Distribution",
            comment="Commander recommendation frontend and API",
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
            default_behavior=cloudfront.BehaviorOptions(
                origin=cloudfront_origins.S3BucketOrigin.with_origin_access_control(
                    frontend_bucket
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
            ),
            additional_behaviors={
                "/api/*": cloudfront.BehaviorOptions(
                    origin=cloudfront_origins.HttpOrigin(
                        api_domain_name,
                        protocol_policy=cloudfront.OriginProtocolPolicy.HTTPS_ONLY,
                    ),
                    viewer_protocol_policy=(
                        cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
                    ),
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
                    origin_request_policy=(
                        cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER
                    ),
                    compress=True,
                    function_associations=[
                        cloudfront.FunctionAssociation(
                            function=strip_api_prefix,
                            event_type=cloudfront.FunctionEventType.VIEWER_REQUEST,
                        )
                    ],
                )
            },
        )

        deployment_log_group = logs.LogGroup(
            self,
            "FrontendDeploymentLogGroup",
            log_group_name="/aws/lambda/commander-rec-cdk-bucket-deployment",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.RETAIN,
        )

        static_deployment = s3_deployment.BucketDeployment(
            self,
            "DeployStaticFiles",
            sources=[s3_deployment.Source.asset(str(frontend_dist))],
            destination_bucket=frontend_bucket,
            exclude=["assets/*"],
            cache_control=[s3_deployment.CacheControl.from_string("no-cache")],
            distribution=distribution,
            distribution_paths=["/index.html"],
            prune=True,
            retain_on_delete=True,
            log_group=deployment_log_group,
        )
        assets_deployment = s3_deployment.BucketDeployment(
            self,
            "DeployHashedAssets",
            sources=[s3_deployment.Source.asset(str(frontend_dist / "assets"))],
            destination_bucket=frontend_bucket,
            destination_key_prefix="assets",
            cache_control=[
                s3_deployment.CacheControl.from_string(
                    "public,max-age=31536000,immutable"
                )
            ],
            distribution=distribution,
            distribution_paths=["/assets/*"],
            prune=True,
            retain_on_delete=True,
            log_group=deployment_log_group,
        )
        assets_deployment.node.add_dependency(static_deployment)

        CfnOutput(
            self,
            "CloudFrontUrl",
            value=f"https://{distribution.distribution_domain_name}",
        )
        CfnOutput(
            self,
            "CloudFrontDistributionId",
            value=distribution.distribution_id,
        )
        CfnOutput(self, "FrontendBucketName", value=frontend_bucket.bucket_name)
        CfnOutput(self, "ApiUrl", value=http_api.api_endpoint)
        CfnOutput(self, "LambdaFunctionName", value=api_function.function_name)
