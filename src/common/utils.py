"""
Shared Utilities Module

This module provides common utilities used across the application.
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
ssm_client = boto3.client("ssm")
logger = logging.getLogger(__name__)


def generate_item_id() -> str:
    """
    Generate a unique item ID using UUID v4.

    Returns:
        A new UUID v4 string.
    """
    return str(uuid.uuid4())


def get_iso8601_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Get current timestamp in ISO 8601 format (UTC).

    Args:
        dt: Optional datetime object. If not provided, uses current UTC time.

    Returns:
        ISO 8601 formatted timestamp string.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_parameter(parameter_name: str, with_decryption: bool = False) -> Optional[str]:
    """
    Retrieve a single parameter from AWS Systems Manager Parameter Store.

    Args:
        parameter_name: Name of the parameter to retrieve.
        with_decryption: Whether to decrypt the parameter value.

    Returns:
        The parameter value, or None if not found.

    Raises:
        ClientError: If AWS API call fails.
    """
    try:
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=with_decryption)
        logger.info(f"Successfully retrieved parameter: {parameter_name}")
        return response["Parameter"]["Value"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ParameterNotFound":
            logger.warning(f"Parameter not found: {parameter_name}")
            return None
        logger.error(f"Error retrieving parameter {parameter_name}: {e}")
        raise


def get_parameters(
    parameter_names: list[str], with_decryption: bool = False
) -> Dict[str, Optional[str]]:
    """
    Retrieve multiple parameters from AWS Systems Manager Parameter Store.

    Args:
        parameter_names: List of parameter names to retrieve.
        with_decryption: Whether to decrypt parameter values.

    Returns:
        Dictionary mapping parameter names to values. Missing parameters map to None.

    Raises:
        ClientError: If AWS API call fails.
    """
    if not parameter_names:
        return {}

    try:
        response = ssm_client.get_parameters(Names=parameter_names, WithDecryption=with_decryption)

        # Create result dictionary with all requested parameters
        results = {name: None for name in parameter_names}

        # Fill in found parameters
        for param in response["Parameters"]:
            results[param["Name"]] = param["Value"]

        # Log missing parameters
        if response["InvalidParameters"]:
            logger.warning(f"Parameters not found: {response['InvalidParameters']}")

        logger.info(
            f"Successfully retrieved {len(response['Parameters'])} of {len(parameter_names)} parameters"
        )
        return results

    except ClientError as e:
        logger.error(f"Error retrieving parameters: {e}")
        raise


def parse_json(json_string: str) -> Optional[Dict[str, Any]]:
    """
    Parse JSON string safely.

    Args:
        json_string: JSON string to parse.

    Returns:
        Parsed dictionary, or None if parsing fails.
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")
        return None


def to_json(obj: Any, indent: bool = False) -> str:
    """
    Convert object to JSON string.

    Args:
        obj: Object to serialize.
        indent: Whether to pretty-print the JSON.

    Returns:
        JSON string representation.
    """
    return json.dumps(obj, indent=2 if indent else None, default=str)


# ============================================================================
# Phase 2: Content Ingestion Pipeline Utilities
# ============================================================================


def generate_cloudfront_url(distribution_domain: str, s3_object_key: str) -> str:
    """
    Generate a CloudFront public URL for an S3 object.

    Args:
        distribution_domain: CloudFront distribution domain (e.g., d123.cloudfront.net)
        s3_object_key: S3 object key (e.g., raw/2026-05-09/image.jpg)

    Returns:
        Full CloudFront URL.
    """
    domain = distribution_domain.strip("/")
    key = s3_object_key.lstrip("/")
    return f"https://{domain}/{key}"


def get_dynamodb_gsi_by_hash(
    table_name: str, content_hash: str, gsi_name: str = "GSI_ContentHash"
) -> Optional[Dict[str, Any]]:
    """
    Query DynamoDB GSI to check for duplicate content by hash.

    Args:
        table_name: DynamoDB table name
        content_hash: MD5 hash of content
        gsi_name: Global Secondary Index name

    Returns:
        Existing item if duplicate found, else None.
    """
    from common import config

    dynamodb = boto3.resource("dynamodb", region_name=config.AWS_REGION)
    table = dynamodb.Table(table_name)

    try:
        response = table.query(
            IndexName=gsi_name,
            KeyConditionExpression="content_hash = :hash",
            ExpressionAttributeValues={":hash": content_hash},
        )

        if response.get("Items"):
            logger.info(f"Duplicate found for hash {content_hash}")
            return response["Items"][0]

        return None

    except ClientError as e:
        logger.error(f"Error querying GSI {gsi_name}: {e}")
        raise


def send_ingestion_alert(
    alert_type: str,
    error_message: str,
    retry_count: int = 0,
    context_data: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Send ingestion pipeline error alert to Telegram via SNS.

    Args:
        alert_type: Type of alert (e.g., "APIFY_ERROR", "CLAUDE_TIMEOUT")
        error_message: Error details
        retry_count: Number of retries attempted
        context_data: Additional context (platform, item_id, etc.)

    Returns:
        True if alert sent successfully, False otherwise.
    """
    from common import config

    sns = boto3.client("sns", region_name=config.AWS_REGION)

    message = f"""🚨 **Ingestion Pipeline Error**

📋 Alert Type: {alert_type}
📝 Error Message: {error_message}
🔄 Retries Attempted: {retry_count}
🕐 Timestamp: {get_iso8601_timestamp()}

"""

    if context_data:
        message += "**Context:**\n"
        for key, value in context_data.items():
            message += f"  • {key}: {value}\n"

    message += "\n🔧 **Action Required**: Check CloudWatch logs and investigate"

    try:
        sns.publish(
            TopicArn=f"arn:aws:sns:{config.AWS_REGION}:{config.AWS_ACCOUNT_ID}:{config.SNS_TOPIC_INGESTION_ALERTS}",
            Subject=f"Ingestion Error: {alert_type}",
            Message=message,
        )
        logger.info(f"Ingestion alert sent for {alert_type}")
        return True

    except ClientError as e:
        logger.error(f"Failed to send ingestion alert: {e}")
        return False
