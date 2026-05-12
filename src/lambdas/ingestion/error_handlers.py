"""
Phase 2 Error Handling & Alerts

Coordinates error handling, dead-letter queue submission, and Telegram alerts
for the content ingestion pipeline.
"""

import json
import logging
import boto3
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from src.common import config
from src.common.utils import get_iso8601_timestamp, get_parameter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

sqs = boto3.client("sqs", region_name=config.AWS_REGION)
sns = boto3.client("sns", region_name=config.AWS_REGION)


def handle_pipeline_error(
    error_type: str,
    error_message: str,
    retry_count: int,
    item_data: Optional[Dict[str, Any]] = None,
    apify_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Handle pipeline errors: publish SNS alert and optionally send to DLQ.

    Args:
        error_type: Error classification (e.g., "APIFY_ERROR", "CLAUDE_TIMEOUT", "S3_UPLOAD_ERROR")
        error_message: Descriptive error message
        retry_count: Number of retry attempts made
        item_data: Optional content item data for context
        apify_metadata: Optional Apify run metadata (run_id, status, etc.)

    Raises:
        None (errors logged, does not propagate)
    """
    try:
        timestamp = get_iso8601_timestamp()

        # Log structured error for CloudWatch analysis with full context
        error_log = {
            "timestamp": timestamp,
            "error_type": error_type,
            "error_message": error_message,
            "retry_count": retry_count,
            "max_retries": config.MAX_RETRY_ATTEMPTS,
            "item_context": (
                {
                    "item_id": item_data.get("item_id") if item_data else None,
                    "source_platform": item_data.get("source_platform") if item_data else None,
                    "source_url": item_data.get("source_url") if item_data else None,
                }
                if item_data
                else None
            ),
            "recovery_hint": _get_remediation_hint(error_type),
            "suggested_actions": [
                "Check CloudWatch logs for detailed error stack trace",
                f"Review error type: {error_type}",
                "Verify credentials in Parameter Store",
                "Check AWS service quotas and limits",
                "If recurring, escalate to on-call DevOps",
            ],
        }

        logger.error(json.dumps(error_log))

        # Publish SNS alert for Telegram delivery
        _publish_error_alert(error_type, error_message, retry_count, item_data)

        # If max retries exhausted, send to DLQ for manual investigation
        if retry_count >= config.MAX_RETRY_ATTEMPTS and item_data:
            _send_to_dlq(error_type, error_message, retry_count, item_data, apify_metadata)

    except Exception as e:
        logger.error(f"Failed to handle pipeline error: {str(e)}", exc_info=True)


def _publish_error_alert(
    error_type: str,
    error_message: str,
    retry_count: int,
    item_data: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Publish SNS message for Telegram alert delivery.

    Args:
        error_type: Error classification
        error_message: Error message
        retry_count: Retry count
        item_data: Optional content item context
    """
    try:
        # Construct alert message
        alert_message = f"""
🚨 **Ingestion Pipeline Alert**

**Error Type**: {error_type}
**Message**: {error_message}
**Retries**: {retry_count}/{config.MAX_RETRY_ATTEMPTS}
"""

        if item_data:
            alert_message += f"**Platform**: {item_data.get('source_platform', 'unknown')}\n"
            if item_data.get("item_id"):
                alert_message += f"**Item ID**: {item_data['item_id']}\n"

        # Suggest remediation based on error type
        remediation = _get_remediation_hint(error_type)
        if remediation:
            alert_message += f"\n**Recovery Hint**: {remediation}\n"

        # Publish to SNS topic (Phase 1 notifier Lambda will forward to Telegram)
        sns.publish(
            TopicArn=config.SNS_TOPIC_ALERTS_ARN,
            Subject=f"Ingestion Pipeline Alert: {error_type}",
            Message=alert_message,
        )

        logger.info(f"Error alert published to SNS: {error_type}")

    except Exception as e:
        logger.error(f"Failed to publish error alert: {str(e)}", exc_info=True)


def _send_to_dlq(
    error_type: str,
    error_message: str,
    retry_count: int,
    item_data: Dict[str, Any],
    apify_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Send failed item to SQS dead-letter queue for manual investigation.

    Args:
        error_type: Error classification
        error_message: Error message
        retry_count: Retry count
        item_data: Content item data
        apify_metadata: Optional Apify run metadata
    """
    try:
        dlq_message = {
            "item_id": item_data.get("item_id"),
            "source_platform": item_data.get("source_platform"),
            "source_url": item_data.get("source_url"),
            "failure_reason": error_message,
            "error_code": error_type,
            "last_error_message": error_message,
            "retry_count": retry_count,
            "first_attempt_at": item_data.get("created_at"),
            "moved_to_dlq_at": get_iso8601_timestamp(),
            "original_caption": item_data.get("original_caption"),
            "metadata": {
                "apify_run_id": apify_metadata.get("run_id") if apify_metadata else None,
                "apify_status": apify_metadata.get("status") if apify_metadata else None,
                "s3_upload_status": item_data.get("s3_upload_status"),
                "claude_attempt_count": retry_count,
            },
        }

        # Send to SQS DLQ
        sqs.send_message(QueueUrl=config.SQS_INGESTION_DLQ_URL, MessageBody=json.dumps(dlq_message))

        logger.info(f"Item {item_data.get('item_id')} moved to DLQ after {retry_count} retries")

    except Exception as e:
        logger.error(f"Failed to send item to DLQ: {str(e)}", exc_info=True)


def _get_remediation_hint(error_type: str) -> Optional[str]:
    """
    Return remediation hint based on error type.

    Args:
        error_type: Error classification

    Returns:
        Remediation hint string, or None if no hint available
    """
    hints = {
        "APIFY_ERROR": "Check Apify token in Parameter Store; verify actor ID is valid; check rate limits",
        "APIFY_AUTH_ERROR": "Verify PARAM_APIFY_API_TOKEN in Parameter Store; regenerate token if expired",
        "APIFY_RATE_LIMIT": "Apify rate limit reached; wait 60 seconds and retry; consider scheduling fewer parallel runs",
        "CLAUDE_TIMEOUT": "Claude API timeout; check network connectivity; may indicate high API load; retry with exponential backoff",
        "CLAUDE_AUTH_ERROR": "Verify PARAM_ANTHROPIC_API_KEY in Parameter Store; check API key is not revoked",
        "CLAUDE_RATE_LIMIT": "Claude rate limit reached; wait 60 seconds; consider reducing caption batch size",
        "IMAGE_PROCESSING_ERROR": "Check image URL is valid and accessible; verify S3 bucket permissions; check image format support",
        "S3_UPLOAD_ERROR": "Check S3 bucket exists; verify IAM role has PutObject permission; check bucket policy",
        "DEDUPLICATION_ERROR": "Check DynamoDB table exists; verify GSI_ContentHash is created; check IAM permissions",
        "DYNAMODB_ERROR": "Check DynamoDB table HealingBedroomContent exists; verify on-demand billing is enabled; check IAM permissions",
    }
    return hints.get(error_type)
