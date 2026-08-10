import json
from pathlib import Path

from aws_cdk import (
    CfnOutput,
    CfnParameter,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigateway,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_integrations as apigwv2_integrations,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as cloudfront_origins,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_deployment as s3_deployment,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
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

        alert_email = CfnParameter(
            self,
            "AlertEmail",
            type="String",
            description="Email address for Commander Rec operational alerts",
            no_echo=True,
        )
        alert_topic = sns.Topic(
            self,
            "AlertTopic",
            topic_name="commander-rec-cdk-alerts",
            display_name="Commander Rec operational alerts",
        )
        alert_topic.add_subscription(
            sns_subscriptions.EmailSubscription(alert_email.value_as_string)
        )
        alarm_action = cloudwatch_actions.SnsAction(alert_topic)

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
                "ENABLE_API_DOCS": "false",
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

        api_access_log_group = logs.LogGroup(
            self,
            "ApiAccessLogGroup",
            log_group_name="/aws/apigateway/commander-rec-cdk-api",
            retention=logs.RetentionDays.TWO_WEEKS,
            removal_policy=RemovalPolicy.RETAIN,
        )
        access_log_format = apigateway.AccessLogFormat.custom(
            json.dumps(
                {
                    "requestId": "$context.requestId",
                    "sourceIp": "$context.identity.sourceIp",
                    "requestTime": "$context.requestTime",
                    "httpMethod": "$context.httpMethod",
                    "routeKey": "$context.routeKey",
                    "status": "$context.status",
                    "responseLength": "$context.responseLength",
                    "integrationLatency": "$context.integrationLatency",
                },
                separators=(",", ":"),
            )
        )
        default_stage = apigwv2.HttpStage(
            self,
            "DefaultStage",
            http_api=http_api,
            stage_name="$default",
            auto_deploy=True,
            detailed_metrics_enabled=False,
            throttle=apigwv2.ThrottleSettings(
                rate_limit=10,
                burst_limit=20,
            ),
        )
        access_log_destination = apigwv2.LogGroupLogDestination(
            api_access_log_group
        ).bind(default_stage)
        cfn_default_stage = default_stage.node.default_child
        if not isinstance(cfn_default_stage, apigwv2.CfnStage):
            raise TypeError("DefaultStage must synthesize an API Gateway stage")
        cfn_default_stage.access_log_settings = (
            apigwv2.CfnStage.AccessLogSettingsProperty(
                destination_arn=access_log_destination.destination_arn,
                format=access_log_format.to_string(),
            )
        )

        self._create_alarm(
            "LambdaInvocationSpikeAlarm",
            alarm_name="commander-rec-cdk-lambda-invocation-spike",
            metric=api_function.metric_invocations(
                period=Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=300,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=(
                cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
            ),
            alarm_action=alarm_action,
        )
        self._create_alarm(
            "LambdaThrottlesAlarm",
            alarm_name="commander-rec-cdk-lambda-throttles",
            metric=api_function.metric_throttles(
                period=Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=5,
            alarm_action=alarm_action,
        )
        self._create_alarm(
            "LambdaErrorsAlarm",
            alarm_name="commander-rec-cdk-lambda-errors",
            metric=api_function.metric_errors(
                period=Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=5,
            alarm_action=alarm_action,
        )
        self._create_alarm(
            "LambdaDurationAlarm",
            alarm_name="commander-rec-cdk-lambda-duration-p95",
            metric=api_function.metric_duration(
                period=Duration.minutes(5),
                statistic="p95",
            ),
            threshold=8_000,
            comparison_operator=(
                cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
            ),
            evaluate_low_sample_count_percentile="ignore",
            alarm_action=alarm_action,
        )

        api_metric_dimensions = {
            "ApiId": http_api.http_api_id,
            "Stage": "$default",
        }
        self._create_alarm(
            "ApiRequestVolumeAlarm",
            alarm_name="commander-rec-cdk-api-request-volume",
            metric=self._api_gateway_metric(
                "Count",
                api_metric_dimensions,
            ),
            threshold=600,
            evaluation_periods=2,
            datapoints_to_alarm=2,
            comparison_operator=(
                cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
            ),
            alarm_action=alarm_action,
        )
        self._create_alarm(
            "ApiClientErrorsAlarm",
            alarm_name="commander-rec-cdk-api-client-errors",
            metric=self._api_gateway_metric(
                "4xx",
                api_metric_dimensions,
            ),
            threshold=50,
            comparison_operator=(
                cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD
            ),
            alarm_action=alarm_action,
        )
        self._create_alarm(
            "ApiServerErrorsAlarm",
            alarm_name="commander-rec-cdk-api-server-errors",
            metric=self._api_gateway_metric(
                "5xx",
                api_metric_dimensions,
            ),
            threshold=5,
            alarm_action=alarm_action,
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
                response_headers_policy=(
                    cloudfront.ResponseHeadersPolicy.SECURITY_HEADERS
                ),
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
        CfnOutput(self, "AlertTopicArn", value=alert_topic.topic_arn)

    def _create_alarm(
        self,
        construct_id: str,
        *,
        alarm_name: str,
        metric: cloudwatch.IMetric,
        threshold: float,
        alarm_action: cloudwatch_actions.SnsAction,
        evaluation_periods: int = 1,
        datapoints_to_alarm: int | None = None,
        comparison_operator: cloudwatch.ComparisonOperator = (
            cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD
        ),
        evaluate_low_sample_count_percentile: str | None = None,
    ) -> cloudwatch.Alarm:
        alarm = cloudwatch.Alarm(
            self,
            construct_id,
            alarm_name=alarm_name,
            metric=metric,
            threshold=threshold,
            evaluation_periods=evaluation_periods,
            datapoints_to_alarm=datapoints_to_alarm,
            comparison_operator=comparison_operator,
            evaluate_low_sample_count_percentile=(
                evaluate_low_sample_count_percentile
            ),
            treat_missing_data=cloudwatch.TreatMissingData.NOT_BREACHING,
        )
        alarm.add_alarm_action(alarm_action)
        return alarm

    @staticmethod
    def _api_gateway_metric(
        metric_name: str,
        dimensions_map: dict[str, str],
    ) -> cloudwatch.Metric:
        return cloudwatch.Metric(
            namespace="AWS/ApiGateway",
            metric_name=metric_name,
            dimensions_map=dimensions_map,
            period=Duration.minutes(5),
            statistic="Sum",
        )
