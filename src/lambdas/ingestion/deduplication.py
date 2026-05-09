"""
Deduplication Logic for Content Ingestion

Checks for duplicate content using content hash and source URL lookups.
"""

import boto3
import logging
from typing import Tuple, Optional, Dict, Any
from botocore.exceptions import ClientError
from common import config
from common.error_handlers import DeduplicationError

logger = logging.getLogger(__name__)


def check_duplicate_by_hash(content_hash: str) -> Tuple[bool, Optional[str]]:
    """
    Check if content hash already exists in DynamoDB GSI.

    Args:
        content_hash: MD5 hash of content

    Returns:
        Tuple of (is_duplicate, existing_item_id). existing_item_id is None if
        content is new.

    Raises:
        DeduplicationError: If DynamoDB query fails
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name=config.AWS_REGION)
        table = dynamodb.Table(config.DYNAMODB_TABLE_NAME)

        response = table.query(
            IndexName="GSI_ContentHash",
            KeyConditionExpression="content_hash = :hash",
            ExpressionAttributeValues={":hash": content_hash}
        )

        if response.get("Items"):
            existing_item = response["Items"][0]
            item_id = existing_item.get("item_id")
            logger.info(f"Duplicate found for hash {content_hash}: {item_id}")
            return True, item_id

        logger.info(f"No duplicate found for hash {content_hash}")
        return False, None

    except ClientError as e:
        raise DeduplicationError(f"Failed to query GSI for duplicate: {e}")


def check_duplicate_by_url(source_url: str) -> Tuple[bool, Optional[str]]:
    """
    Check if source URL already exists in DynamoDB.

    Handles edge case where same image URL is reposted from different accounts.

    Args:
        source_url: Original source platform URL

    Returns:
        Tuple of (is_duplicate, existing_item_id). existing_item_id is None if
        URL is new.

    Raises:
        DeduplicationError: If DynamoDB query fails
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name=config.AWS_REGION)
        table = dynamodb.Table(config.DYNAMODB_TABLE_NAME)

        # Query by GSI1_Status to find items with same source_url
        response = table.scan(
            FilterExpression="source_url = :url",
            ExpressionAttributeValues={":url": source_url}
        )

        if response.get("Items"):
            existing_item = response["Items"][0]
            item_id = existing_item.get("item_id")
            logger.info(f"Duplicate URL found: {source_url} -> {item_id}")
            return True, item_id

        logger.info(f"No duplicate URL found: {source_url}")
        return False, None

    except ClientError as e:
        raise DeduplicationError(f"Failed to check URL duplicate: {e}")
