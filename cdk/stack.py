"""
AWS CDK Stack Definition

This module defines the main Healing Bedroom infrastructure stack.
"""

from aws_cdk import (
    BundlingOptions,
    Stack,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as cf_origins,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subs,
    aws_sqs as sqs,
    aws_events as events,
    aws_events_targets as targets,
    aws_budgets as budgets,
    aws_cloudwatch as cloudwatch,
    Duration,
    RemovalPolicy,
    Tags,
)
from constructs import Construct
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.common import config


class HealingBedroomStack(Stack):
    """Main CDK Stack for Healing Bedroom Phase 1 infrastructure."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Initialize the Healing Bedroom infrastructure stack.

        Args:
            scope: CDK scope (App)
            construct_id: Stack identifier
            **kwargs: Additional stack properties
        """
        super().__init__(scope, construct_id, **kwargs)

        # Create core infrastructure
        self.dynamodb_table = self._create_dynamodb_table()
        self.s3_bucket = self._create_s3_bucket()
        self.cloudfront_distribution = self._create_cloudfront_distribution()
        self.lambda_role = self._create_lambda_role()
        self.log_group = self._create_cloudwatch_log_group()
        self.sns_topic = self._create_sns_topic()
        self.dlq = self._create_sqs_dlq()
        self.common_layer = lambda_.LayerVersion(
            self,
            "SharedCommonLayer",
            code=lambda_.Code.from_asset(
                "src",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    user="root",
                    command=[
                        "bash", "-c",
                        """
                        set -e
                        mkdir -p /asset-output/python
                        cp -r /asset-input/common /asset-output/python/
                        find /asset-output -name "__pycache__" -exec rm -rf {} + || true
                        find /asset-output -name "*.pyc" -delete || true
                        ls -la /asset-output/python/common/
                        """
                    ]
                )
            ),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Shared utilities, config, SSM helpers",
            layer_version_name="healing-bedroom-common",
        )
        self.notifier_lambda = self._create_lambda_notifier()
        self.ingestion_lambda = self._create_ingestion_lambda()
        self.ingestion_scheduler = self._create_ingestion_scheduler()
        self.budget_alarm = self._create_budget_alarm()
        self.ingestion_dashboard = self._create_ingestion_dashboard()

        # Apply tags to all resources
        for key, value in config.get_tags().items():
            Tags.of(self).add(key, value)

    def _create_dynamodb_table(self) -> dynamodb.Table:
        """Create DynamoDB table for content storage."""
        table = dynamodb.Table(
            self,
            "HealingBedroomContentTable",
            table_name=config.DYNAMODB_TABLE_NAME,
            partition_key=dynamodb.Attribute(name="item_id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=False,
            encryption=dynamodb.TableEncryption.DEFAULT,
        )

        # Global Secondary Index on status and created_at
        table.add_global_secondary_index(
            index_name="GSI1_Status",
            partition_key=dynamodb.Attribute(name="status", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="created_at", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL,
        )

        # Phase 2: Global Secondary Index on content_hash for deduplication
        # table.add_global_secondary_index(
        #     index_name="GSI_ContentHash",
        #     partition_key=dynamodb.Attribute(
        #         name="content_hash", type=dynamodb.AttributeType.STRING
        #     ),
        #     sort_key=dynamodb.Attribute(name="created_at", type=dynamodb.AttributeType.STRING),
        #     projection_type=dynamodb.ProjectionType.INCLUDE,
        #     non_key_attributes=["source_url", "item_id"],
        # )

        return table

    def _create_s3_bucket(self) -> s3.Bucket:
        """Create S3 bucket for image storage."""
        bucket = s3.Bucket(
            self,
            "HealingBedroomImagesBucket",
            bucket_name=config.get_bucket_name(),
            removal_policy=RemovalPolicy.DESTROY,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            encryption=s3.BucketEncryption.S3_MANAGED,
            versioned=False,
        )

        bucket.add_lifecycle_rule(
            expiration=Duration.days(config.S3_LIFECYCLE_DAYS),
        )

        return bucket

    def _create_cloudfront_distribution(self) -> cloudfront.Distribution:
        """Create CloudFront distribution for image delivery."""
        # Create distribution with S3 origin
        distribution = cloudfront.Distribution(
            self,
            "HealingBedroomDistribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=cf_origins.S3Origin(
                    self.s3_bucket,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
            ),
            enable_ipv6=False,
            comment="Healing Bedroom CDN",
        )

        # Update bucket policy to allow CloudFront access
        self.s3_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("cloudfront.amazonaws.com", region=self.region)],
                actions=["s3:GetObject"],
                resources=[self.s3_bucket.arn_for_objects("*")],
                conditions={
                    "StringEquals": {
                        "aws:SourceArn": f"arn:aws:cloudfront::{self.account}:distribution/{distribution.distribution_id}"
                    }
                },
            )
        )

        return distribution

    def _create_lambda_role(self) -> iam.Role:
        """Create IAM role for Lambda functions with least-privilege permissions."""
        role = iam.Role(
            self,
            "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            role_name=config.LAMBDA_ROLE_NAME,
            description=config.LAMBDA_ROLE_DESCRIPTION,
        )

        # DynamoDB permissions (scoped to HealingBedroomContent table)
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                ],
                resources=[
                    self.dynamodb_table.table_arn,
                    f"{self.dynamodb_table.table_arn}/index/*",
                ],
            )
        )

        # S3 permissions (scoped to bucket objects)
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBucket",
                ],
                resources=[
                    self.s3_bucket.bucket_arn,
                    self.s3_bucket.arn_for_objects("*"),
                ],
            )
        )

        # Parameter Store permissions (scoped to /healing-bedroom/* path)
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "ssm:GetParameter",
                    "ssm:GetParameters",
                ],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter{config.PARAM_PREFIX}/*"
                ],
            )
        )

        # CloudWatch Logs permissions
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[
                    f"arn:aws:logs:{self.region}:{self.account}:log-group:{config.LOG_GROUP_NAME}-*:*"
                ],
            )
        )

        # Phase 2: SQS permissions for dead-letter queue
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sqs:SendMessage",
                ],
                resources=[f"arn:aws:sqs:{self.region}:{self.account}:{config.SQS_DLQ_NAME}"],
            )
        )

        # SNS permissions for alerts
        role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "sns:Publish",
                ],
                resources=[
                    f"arn:aws:sns:{self.region}:{self.account}:*"
                ],
            )
        )

        return role

    def _create_cloudwatch_log_group(self) -> logs.LogGroup:
        """Create CloudWatch log group for Lambda functions."""
        log_group = logs.LogGroup(
            self,
            "LambdaLogGroup",
            log_group_name=config.LOG_GROUP_NAME,
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )
        return log_group

    def _create_sns_topic(self) -> sns.Topic:
        """Create SNS topic for alerts."""
        topic = sns.Topic(
            self,
            "AlertsTopic",
            topic_name=config.SNS_TOPIC_ALERTS,
            display_name="Healing Bedroom Alerts",
        )
        return topic

    def _create_lambda_notifier(self) -> lambda_.Function:
        """Create Lambda function for sending Telegram notifications."""
        notifier = lambda_.Function(
            self,
            "LambdaNotifier",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("src/lambdas/notifier"),
            role=self.lambda_role,
            timeout=Duration.seconds(30),
            memory_size=256,
            log_retention=logs.RetentionDays.ONE_WEEK,
            layers=[self.common_layer],
            function_name=config.LAMBDA_NOTIFIER_NAME
        )

        # Subscribe Lambda to SNS topic
        self.sns_topic.add_subscription(sns_subs.LambdaSubscription(notifier))

        return notifier

    def _create_sqs_dlq(self) -> sqs.Queue:
        """Create SQS dead-letter queue for failed ingestion items."""
        dlq = sqs.Queue(
            self,
            "IngestionDLQ",
            queue_name=config.SQS_DLQ_NAME,
            retention_period=Duration.hours(96),  # 4 days
            visibility_timeout=Duration.seconds(300),
            enforce_ssl=True,
        )
        return dlq

    def _create_ingestion_lambda(self) -> lambda_.Function:
        """Create Lambda function for Phase 2 content ingestion pipeline."""
        
        # Dependencies Layer (unchanged)
        deps_layer = lambda_.LayerVersion(
            self,
            "IngestionDepsLayer",
            code=lambda_.Code.from_asset(
                "src/lambdas/ingestion",
                bundling=BundlingOptions(
                    image=lambda_.Runtime.PYTHON_3_12.bundling_image,
                    user="root",
                    command=[
                        "bash", "-c",
                        """
                        set -e
                        mkdir -p /asset-output/python
                        pip install -r requirements.prod.txt -t /asset-output/python \
                            --no-cache-dir --platform manylinux2014_x86_64 --only-binary=:all:
                        find /asset-output -name "__pycache__" -exec rm -rf {} + || true
                        find /asset-output -name "*.pyc" -delete || true
                        rm -rf /asset-output/python/bin
                        """
                    ]
                )
            ),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_12],
            description="Production dependencies"
        )

        ingestion_lambda = lambda_.Function(
            self,
            "IngestionLambda",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="lambda_function.lambda_handler",
            code=lambda_.Code.from_asset("src/lambdas/ingestion",
                exclude=["**/__pycache__", "**/*.pyc", "requirements.prod.txt", ".git"]
            ),
            # No custom bundling on main code!
            role=self.lambda_role,
            timeout=Duration.seconds(600),
            memory_size=512,
            log_retention=logs.RetentionDays.ONE_WEEK,
            layers=[deps_layer],
            function_name=config.LAMBDA_INGESTION_NAME
        )
        return ingestion_lambda

    def _create_ingestion_scheduler(self) -> events.Rule:
        """Create EventBridge Scheduler rule for periodic ingestion."""
        rule = events.Rule(
            self,
            "IngestionScheduler",
            schedule=events.Schedule.expression(f"cron({config.INGESTION_SCHEDULE_CRON})"),
            description="Trigger content ingestion pipeline on schedule",
        )

        # Add Lambda as target
        rule.add_target(targets.LambdaFunction(self.ingestion_lambda))

        # Grant EventBridge permission to invoke Lambda
        self.ingestion_lambda.grant_invoke(iam.ServicePrincipal("events.amazonaws.com"))

        return rule

    def _create_ingestion_dashboard(self) -> cloudwatch.Dashboard:
        """Create CloudWatch dashboard for ingestion pipeline monitoring."""
        dashboard = cloudwatch.Dashboard(
            self, "IngestionDashboard", dashboard_name="HealingBedroom-Ingestion-Pipeline"
        )

        # Add metrics widgets
        processed_items = cloudwatch.Metric(
            namespace=config.CLOUDWATCH_METRICS_NAMESPACE,
            metric_name="processed_items",
            statistic="Sum",
            period=Duration.minutes(1),
            label="Items Processed",
        )

        items_scraped = cloudwatch.Metric(
            namespace=config.CLOUDWATCH_METRICS_NAMESPACE,
            metric_name="items_scraped",
            statistic="Sum",
            period=Duration.minutes(1),
            label="Items Scraped",
        )

        duplicate_skipped = cloudwatch.Metric(
            namespace=config.CLOUDWATCH_METRICS_NAMESPACE,
            metric_name="duplicate_skipped",
            statistic="Sum",
            period=Duration.minutes(1),
            label="Duplicates Skipped",
        )

        errors_total = cloudwatch.Metric(
            namespace=config.CLOUDWATCH_METRICS_NAMESPACE,
            metric_name="errors_total",
            statistic="Sum",
            period=Duration.minutes(1),
            label="Total Errors",
        )

        # DLQ message count
        dlq_messages = cloudwatch.Metric(
            namespace="AWS/SQS",
            metric_name="ApproximateNumberOfMessagesVisible",
            dimensions_map={"QueueName": config.SQS_DLQ_NAME},
            statistic="Average",
            period=Duration.minutes(1),
            label="DLQ Messages",
        )

        # Lambda duration
        lambda_duration = cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name="Duration",
            dimensions_map={"FunctionName": config.LAMBDA_INGESTION_NAME},
            statistic="Average",
            period=Duration.minutes(1),
            label="Lambda Duration (ms)",
        )

        # Lambda error count
        lambda_errors = cloudwatch.Metric(
            namespace="AWS/Lambda",
            metric_name="Errors",
            dimensions_map={"FunctionName": config.LAMBDA_INGESTION_NAME},
            statistic="Sum",
            period=Duration.minutes(1),
            label="Lambda Errors",
        )

        # Add widgets to dashboard
        dashboard.add_widgets(
            cloudwatch.GraphWidget(
                title="Ingestion Pipeline Metrics",
                left=[processed_items, items_scraped, duplicate_skipped],
                right=[errors_total],
                width=12,
                height=6,
            ),
            cloudwatch.GraphWidget(
                title="Dead-Letter Queue Status", left=[dlq_messages], width=12, height=6
            ),
            cloudwatch.GraphWidget(
                title="Lambda Performance",
                left=[lambda_duration],
                right=[lambda_errors],
                width=12,
                height=6,
            ),
        )

        return dashboard

    def _create_budget_alarm(self) -> budgets.CfnBudget:
        """Create AWS Budget for cost monitoring."""
        budget = budgets.CfnBudget(
            self,
            "HealingBedroomBudget",
            budget=budgets.CfnBudget.BudgetDataProperty(
                budget_name=f"{config.PROJECT_NAME}-Monthly-Budget",
                budget_limit=budgets.CfnBudget.SpendProperty(
                    amount=config.BUDGET_LIMIT, unit="USD"
                ),
                budget_type="COST",
                time_period=budgets.CfnBudget.TimePeriodProperty(
                    start="1735689600",  # 2026-01-01 00:00:00 UTC (epoch seconds)
                    end="3660825600",  # 2086-01-01 00:00:00 UTC (epoch seconds)
                ),
                time_unit="MONTHLY",
            ),
            notifications_with_subscribers=[
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator="GREATER_THAN",
                        notification_type="ACTUAL",
                        threshold=config.BUDGET_ALERT_50_THRESHOLD,
                        threshold_type="ABSOLUTE_VALUE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            address=self.sns_topic.topic_arn, subscription_type="SNS"
                        )
                    ],
                ),
                budgets.CfnBudget.NotificationWithSubscribersProperty(
                    notification=budgets.CfnBudget.NotificationProperty(
                        comparison_operator="GREATER_THAN",
                        notification_type="ACTUAL",
                        threshold=config.BUDGET_ALERT_80_THRESHOLD,
                        threshold_type="ABSOLUTE_VALUE",
                    ),
                    subscribers=[
                        budgets.CfnBudget.SubscriberProperty(
                            address=self.sns_topic.topic_arn, subscription_type="SNS"
                        )
                    ],
                ),
            ],
        )
        return budget
