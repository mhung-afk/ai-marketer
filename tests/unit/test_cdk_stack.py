"""
CDK Stack Unit Tests

Tests for the Healing Bedroom infrastructure stack using CDK assertions.
"""

import pytest
from aws_cdk import assertions, aws_dynamodb, aws_s3, aws_cloudfront, aws_iam, aws_logs
from cdk.stack import HealingBedroomStack
from aws_cdk import App, Environment


@pytest.fixture
def template():
    """Create a CDK template for testing."""
    app = App()
    stack = HealingBedroomStack(
        app,
        "TestStack",
        env=Environment(region="us-east-1", account="123456789012"),
    )
    return assertions.Template.from_stack(stack)


def test_dynamodb_table_exists(template):
    """Test that DynamoDB table is created with correct configuration."""
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "TableName": "HealingBedroomContent",
            "BillingMode": "PAY_PER_REQUEST",
            "AttributeDefinitions": [
                {"AttributeName": "item_id", "AttributeType": "S"},
            ],
            "KeySchema": [
                {"AttributeName": "item_id", "KeyType": "HASH"},
            ],
        },
    )


def test_dynamodb_gsi_exists(template):
    """Test that GSI1_Status global secondary index exists."""
    template.has_resource_properties(
        "AWS::DynamoDB::Table",
        {
            "GlobalSecondaryIndexes": assertions.Match.array_with([
                assertions.Match.object_like({
                    "IndexName": "GSI1_Status",
                    "Keys": assertions.Match.any(),
                    "Projection": {"ProjectionType": "ALL"},
                })
            ])
        },
    )


def test_s3_bucket_created(template):
    """Test that S3 bucket is created with correct policies."""
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "BucketEncryption": assertions.Match.any(),
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True,
            },
        },
    )


def test_s3_lifecycle_policy(template):
    """Test that S3 bucket has lifecycle policy for 7-day expiration."""
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "LifecycleConfiguration": assertions.Match.object_like({
                "Rules": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "ExpirationInDays": 7,
                        "Status": "Enabled",
                    })
                ])
            })
        },
    )


def test_cloudfront_distribution_created(template):
    """Test that CloudFront distribution is created."""
    template.has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": assertions.Match.object_like({
                "DefaultBehavior": assertions.Match.any(),
                "Enabled": True,
            })
        },
    )


def test_lambda_iam_role_created(template):
    """Test that Lambda IAM role is created."""
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "RoleName": "lambda-healing-bedroom-role",
            "AssumeRolePolicyDocument": assertions.Match.object_like({
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Principal": {"Service": "lambda.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    })
                ])
            })
        },
    )


def test_lambda_role_dynamodb_permissions(template):
    """Test that Lambda role has DynamoDB permissions."""
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": assertions.Match.object_like({
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Action": assertions.Match.array_with([
                            "dynamodb:GetItem",
                            "dynamodb:PutItem",
                            "dynamodb:UpdateItem",
                            "dynamodb:Query",
                            "dynamodb:Scan",
                        ]),
                        "Effect": "Allow",
                    })
                ])
            })
        },
    )


def test_lambda_role_s3_permissions(template):
    """Test that Lambda role has S3 permissions."""
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": assertions.Match.object_like({
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Action": assertions.Match.array_with([
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject",
                            "s3:ListBucket",
                        ]),
                        "Effect": "Allow",
                    })
                ])
            })
        },
    )


def test_lambda_role_parameter_store_permissions(template):
    """Test that Lambda role has Parameter Store permissions."""
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": assertions.Match.object_like({
                "Statement": assertions.Match.array_with([
                    assertions.Match.object_like({
                        "Action": [
                            "ssm:GetParameter",
                            "ssm:GetParameters",
                        ],
                        "Effect": "Allow",
                    })
                ])
            })
        },
    )


def test_cloudwatch_log_group_created(template):
    """Test that CloudWatch log group is created."""
    template.has_resource_properties(
        "AWS::Logs::LogGroup",
        {
            "LogGroupName": "/aws/lambda/healing-bedroom",
            "RetentionInDays": 7,
        },
    )


def test_sns_topic_created(template):
    """Test that SNS topic for budget alerts is created."""
    template.has_resource_properties(
        "AWS::SNS::Topic",
        {
            "TopicName": "healing-bedroom-budget-alerts",
        },
    )


def test_budget_alarm_created(template):
    """Test that AWS Budget is created with correct thresholds."""
    template.has_resource_properties(
        "AWS::Budgets::Budget",
        {
            "Budget": assertions.Match.object_like({
                "BudgetName": "HealingBedroom-Monthly-Budget",
                "BudgetLimit": {"Amount": "40", "Unit": "USD"},
                "BudgetType": "COST",
                "TimeUnit": "MONTHLY",
            })
        },
    )


def test_parameter_store_parameters_created(template):
    """Test that Parameter Store parameters are created."""
    # Test that multiple SSM parameters are created
    template.resource_count_is(
        "AWS::SSM::Parameter",
        6,  # 4 Phase 1 + 2 Phase 2+ placeholders
    )


def test_stack_outputs_exist(template):
    """Test that all expected stack outputs are defined."""
    template.has_output(
        "DynamoDBTableName",
        assertions.Match.any(),
    )
    template.has_output(
        "S3BucketName",
        assertions.Match.any(),
    )
    template.has_output(
        "CloudFrontDistributionDomain",
        assertions.Match.any(),
    )
    template.has_output(
        "CloudFrontDistributionId",
        assertions.Match.any(),
    )
    template.has_output(
        "LambdaRoleArn",
        assertions.Match.any(),
    )
    template.has_output(
        "LogGroupName",
        assertions.Match.any(),
    )
    template.has_output(
        "SNSTopicArn",
        assertions.Match.any(),
    )
    template.has_output(
        "ParameterStorePrefix",
        assertions.Match.any(),
    )
