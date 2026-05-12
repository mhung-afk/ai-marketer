"""
Shared Configuration Module

This module provides centralized configuration constants for the entire application.
Used by both CDK infrastructure-as-code and runtime Lambda/application code.
"""

import os
from typing import Dict

# ============================================================================
# AWS Configuration
# ============================================================================
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID", "")

# ============================================================================
# Project Names
# ============================================================================
PROJECT_NAME = "HealingBedroom"
ENVIRONMENT = os.getenv("ENVIRONMENT_NAME", "phase1")

# ============================================================================
# Parameter Store Paths
# ============================================================================
PARAM_PREFIX = "/healing-bedroom"
PARAM_ANTHROPIC_API_KEY = f"{PARAM_PREFIX}/anthropic-api-key"
PARAM_FAL_AI_KEY = f"{PARAM_PREFIX}/fal-ai-key"
PARAM_TELEGRAM_BOT_TOKEN = f"{PARAM_PREFIX}/telegram-bot-token"
PARAM_TELEGRAM_CHAT_ID = f"{PARAM_PREFIX}/telegram-chat-id"
PARAM_APIFY_API_TOKEN = f"{PARAM_PREFIX}/apify-api-token"
PARAM_FACEBOOK_PAGE_ACCESS_TOKEN = f"{PARAM_PREFIX}/facebook-page-access-token"

# ============================================================================
# CloudWatch Log Groups
# ============================================================================
LOG_GROUP_NAME = "/aws/lambda/healing-bedroom"
LOG_RETENTION_DAYS = 7

# ============================================================================
# DynamoDB
# ============================================================================
DYNAMODB_TABLE_NAME = "HealingBedroomContent"

# ============================================================================
# S3
# ============================================================================
S3_BUCKET_PREFIX = "healing-bedroom-images"
S3_BUCKET_SUFFIX = "ai-marketer"
S3_LIFECYCLE_DAYS = 7

# ============================================================================
# CloudFront CDN
# ============================================================================
CLOUDFRONT_CACHE_TTL_DEFAULT = 86400
CLOUDFRONT_CACHE_TTL_METADATA = 3600

# ============================================================================
# SNS Topics
# ============================================================================
SNS_TOPIC_BUDGET_ALERTS = "healing-bedroom-budget-alerts"
SNS_TOPIC_INGESTION_ALERTS = "healing-bedroom-ingestion-alerts"

# ============================================================================
# Lambda Functions
# ============================================================================
LAMBDA_NOTIFIER_NAME = "healing-bedroom-notifier"
LAMBDA_INGESTION_NAME = "healing-bedroom-ingestion"

# ============================================================================
# Phase 2: Content Ingestion Pipeline
# ============================================================================
INGESTION_SCHEDULE_CRON = os.getenv("INGESTION_SCHEDULE_CRON", "0 */6 * * ? *")

# Apify configuration for social media scraping
SOURCES_CONFIG = {
    "tiktok": {
        "actor_id": "sKvq8dqWIB7QvZyPf",
        "options": {
            "hashtags": ["bedroom", "sleep", "selfcare", "wellness"],
            "max_posts": 20,
            "sort_type": "latest",
        },
    },
    "instagram": {
        "actor_id": "apify/instagram-hashtag-scraper",
        "options": {
            "hashtags": ["bedroominspo", "sleepwellness", "bedroomgoals"],
            "max_posts": 20,
            "sort_type": "latest",
        },
    },
    "facebook": {
        "actor_id": "apify/facebook-graph-scraper",
        "options": {"hashtags": ["bedroom", "sleep", "wellness"], "max_posts": 15},
    },
}

# SQS Dead-Letter Queue
SQS_DLQ_NAME = "healing-bedroom-ingestion-dlq"
SQS_DLQ_RETENTION_SECONDS = 345600  # 4 days
SQS_DLQ_VISIBILITY_TIMEOUT = 300  # 5 minutes
SQS_INGESTION_DLQ_URL = os.getenv(
    "SQS_INGESTION_DLQ_URL",
    f"https://sqs.{AWS_REGION}.amazonaws.com/{AWS_ACCOUNT_ID}/{SQS_DLQ_NAME}",
)

# EventBridge
EVENTBRIDGE_SCHEDULER_NAME = "healing-bedroom-ingestion-scheduler"

# ============================================================================
# Phase 6: Pipeline Monitoring & Error Handling
# ============================================================================

# Retry Configuration
MAX_RETRY_ATTEMPTS = 3
RETRY_BACKOFF_BASE = 2  # Exponential backoff: 2^n seconds

# SNS Topic ARN for ingestion alerts
SNS_INGESTION_ALERTS_TOPIC_ARN = os.getenv(
    "SNS_INGESTION_ALERTS_TOPIC_ARN",
    f"arn:aws:sns:{AWS_REGION}:{AWS_ACCOUNT_ID}:{SNS_TOPIC_INGESTION_ALERTS}",
)

# CloudWatch Metrics
CLOUDWATCH_METRICS_NAMESPACE = "HealingBedroom/Ingestion"
CLOUDWATCH_METRICS = {
    "processed_items": "Count of items processed in current run",
    "successful_captions": "Count of successful caption generations",
    "failed_captions": "Count of failed caption attempts",
    "duplicate_skipped": "Count of items skipped due to deduplication",
    "errors_total": "Total error count in current run",
    "dlq_messages": "Dead-letter queue message count",
    "lambda_duration_ms": "Lambda execution time in milliseconds",
}

# ============================================================================
# IAM Configuration
# ============================================================================
LAMBDA_ROLE_NAME = "lambda-healing-bedroom-role"
LAMBDA_ROLE_DESCRIPTION = (
    "IAM role for Healing Bedroom Lambda functions with least-privilege permissions"
)

# ============================================================================
# Budget Configuration
# ============================================================================
BUDGET_LIMIT = float(os.getenv("BUDGET_LIMIT", 20))
BUDGET_ALERT_50_THRESHOLD = 0.5 * BUDGET_LIMIT
BUDGET_ALERT_80_THRESHOLD = 0.8 * BUDGET_LIMIT

# ============================================================================
# Helper Functions
# ============================================================================


def get_bucket_name() -> str:
    """Generate S3 bucket name with optional suffix."""
    return f"{S3_BUCKET_PREFIX}-{S3_BUCKET_SUFFIX}".lower()


def get_tags() -> Dict[str, str]:
    """Return default tags for all AWS resources."""
    return {"Project": PROJECT_NAME, "Environment": ENVIRONMENT, "ManagedBy": "CDK"}
