"""
DynamoDB Storage Module

Handles persisting ingested content to DynamoDB table.
"""

import logging
from typing import Optional
import boto3
from botocore.exceptions import ClientError
from common import config
from common.error_handlers import S3UploadError
from common.schemas import ContentItem, ContentStatus
from common.utils import get_iso8601_timestamp

logger = logging.getLogger(__name__)


class DynamoDBStorage:
    """Handler for storing content items in DynamoDB."""

    def __init__(self, dynamodb=None):
        """
        Initialize DynamoDB storage handler.

        Args:
            dynamodb: Optional boto3 DynamoDB resource. If not provided, creates new one.
        """
        self.dynamodb = dynamodb or boto3.resource("dynamodb", region_name=config.AWS_REGION)
        self.table = self.dynamodb.Table(config.DYNAMODB_TABLE_NAME)

    def save_content_item(self, content_item: ContentItem) -> bool:
        """
        Save content item to DynamoDB.

        Args:
            content_item: ContentItem Pydantic model

        Returns:
            True if successful, False otherwise

        Raises:
            S3UploadError: If DynamoDB put fails
        """
        try:
            # Convert Pydantic model to dict
            item_dict = content_item.dict()

            # Ensure required fields are set
            if not item_dict.get("created_at"):
                item_dict["created_at"] = get_iso8601_timestamp()

            if not item_dict.get("updated_at"):
                item_dict["updated_at"] = get_iso8601_timestamp()

            # Set status to RAW if not specified
            if not item_dict.get("status"):
                item_dict["status"] = ContentStatus.RAW.value

            logger.info(f"Saving item to DynamoDB: {item_dict.get('item_id')}")

            self.table.put_item(Item=item_dict)

            logger.info(f"Successfully saved item: {item_dict.get('item_id')}")
            return True

        except ClientError as e:
            raise S3UploadError(f"Failed to save item to DynamoDB: {e}")

    def update_content_item_with_caption(
        self, item_id: str, ai_caption_vi: str, ai_caption_tone: str
    ) -> bool:
        """
        Update item with AI-generated caption.

        Args:
            item_id: Item ID
            ai_caption_vi: Vietnamese caption
            ai_caption_tone: Tone used for caption

        Returns:
            True if successful

        Raises:
            S3UploadError: If update fails
        """
        try:
            self.table.update_item(
                Key={"item_id": item_id},
                UpdateExpression="SET ai_caption_vi = :cap, ai_caption_tone = :tone, processed_at = :now, updated_at = :now",
                ExpressionAttributeValues={
                    ":cap": ai_caption_vi,
                    ":tone": ai_caption_tone,
                    ":now": get_iso8601_timestamp(),
                },
            )

            logger.info(f"Updated caption for item: {item_id}")
            return True

        except ClientError as e:
            raise S3UploadError(f"Failed to update item caption: {e}")

    def update_content_item_with_error(
        self, item_id: str, error_reason: str, retry_count: int = 0
    ) -> bool:
        """
        Update item to ERROR status with error details.

        Args:
            item_id: Item ID
            error_reason: Description of error
            retry_count: Number of retries attempted

        Returns:
            True if successful

        Raises:
            S3UploadError: If update fails
        """
        try:
            self.table.update_item(
                Key={"item_id": item_id},
                UpdateExpression="SET #status = :status, error_reason = :reason, retry_count = :retries, updated_at = :now",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": ContentStatus.ERROR.value,
                    ":reason": error_reason,
                    ":retries": retry_count,
                    ":now": get_iso8601_timestamp(),
                },
            )

            logger.error(f"Marked item as ERROR: {item_id} - {error_reason}")
            return True

        except ClientError as e:
            raise S3UploadError(f"Failed to update item error status: {e}")

    def query_items_by_status(self, status: str, limit: int = 10) -> list:
        """
        Query items by status using GSI1_Status.

        Args:
            status: Status to query (RAW, APPROVED, PUBLISHED, etc.)
            limit: Maximum items to return

        Returns:
            List of items with matching status

        Raises:
            S3UploadError: If query fails
        """
        try:
            response = self.table.query(
                IndexName="GSI1_Status",
                KeyConditionExpression="#status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":status": status},
                Limit=limit,
                ScanIndexForward=False,  # Newest first
            )

            items = response.get("Items", [])
            logger.info(f"Queried {len(items)} items with status {status}")
            return items

        except ClientError as e:
            raise S3UploadError(f"Failed to query items by status: {e}")
