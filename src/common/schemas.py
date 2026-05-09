"""
Data Schema Definitions

This module defines DynamoDB item schemas and validation logic.
"""

from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field

from common import config


class ItemStatus(Enum):
    """Content item status throughout the pipeline."""
    RAW = "RAW"  # Newly scraped, awaiting processing
    PROCESSING = "PROCESSING"  # Currently being processed
    DRAFT = "DRAFT"  # Generated content awaiting approval
    APPROVED = "APPROVED"  # Approved by human review
    POSTED = "POSTED"  # Posted to social media
    FAILED = "FAILED"  # Processing failed
    ERROR = "ERROR"  # Processing error


class SourcePlatform(str, Enum):
    """Social media source platforms for Phase 2 content ingestion."""
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"


class ContentStatus(str, Enum):
    """Content processing status for Phase 2."""
    RAW = "RAW"
    APPROVED = "APPROVED"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    ERROR = "ERROR"


class CaptureTone(str, Enum):
    """AI caption tone variations for Phase 2."""
    CALMING = "calming"
    MOTIVATIONAL = "motivational"
    AESTHETIC = "aesthetic"
    ASPIRATIONAL = "aspirational"


class ContentItem(BaseModel):
    """Pydantic model for Phase 2 content ingestion items."""
    item_id: str
    source_platform: SourcePlatform
    source_url: str
    source_post_id: Optional[str] = None
    original_caption: str
    ai_caption_vi: Optional[str] = None
    ai_caption_tone: Optional[CaptureTone] = None
    s3_image_key: Optional[str] = None
    cloudfront_url: Optional[str] = None
    content_hash: Optional[str] = None
    image_size_bytes: Optional[int] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    status: ContentStatus = ContentStatus.RAW
    error_reason: Optional[str] = None
    retry_count: int = 0
    created_at: str
    processed_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ttl: Optional[int] = None

    class Config:
        use_enum_values = True


class IngestionRun(BaseModel):
    """Pydantic model for tracking Phase 2 ingestion run metadata."""
    run_id: str
    source_platform: SourcePlatform
    items_scraped: int = 0
    items_deduplicated: int = 0
    items_processed: int = 0
    items_failed: int = 0
    started_at: str
    completed_at: Optional[str] = None
    errors: list[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class ContentItemTypedDict(dict):
    """
    DynamoDB item schema for content storage.
    
    Attributes:
        item_id: Unique identifier (UUID v4)
        status: Current status in the pipeline
        created_at: ISO 8601 timestamp when item was created
        niche: Content niche/category
        source_platform: Platform where content was scraped from
        source_url: Original URL of the source content
        original_caption: Original text caption from source
        original_image_url: URL to original image
        scraped_at: ISO 8601 timestamp when content was scraped
        ai_caption: AI-generated caption (Vietnamese)
        image_s3_key: S3 key for processed image
        image_cloudfront_url: CloudFront URL for image delivery
        processed_at: ISO 8601 timestamp when processing completed
        approved_by: User ID of approver
        approved_at: ISO 8601 timestamp of approval
        post_id: Platform-specific post ID after posting
        post_url: URL to posted content
        posted_at: ISO 8601 timestamp when posted
        error_log: JSON string of error details if failed
        retry_count: Number of retry attempts
    """
    # Core attributes (required)
    item_id: str
    status: str
    created_at: str
    niche: str
    source_platform: str
    source_url: str

    # Ingestion attributes
    original_caption: str
    original_image_url: str
    scraped_at: str

    # Processing attributes
    ai_caption: str
    image_s3_key: str
    image_cloudfront_url: str
    processed_at: str

    # Approval attributes
    approved_by: str
    approved_at: str

    # Posting attributes
    post_id: str
    post_url: str
    posted_at: str

    # Error handling
    error_log: str
    retry_count: int


class DynamoDBSchema:
    """DynamoDB schema documentation and validation."""

    # Table: HealingBedroomContent
    TABLE_NAME = config.DYNAMODB_TABLE_NAME

    # Primary Key: item_id (UUID v4)
    PARTITION_KEY = "item_id"
    PARTITION_KEY_TYPE = "S"  # String

    # Global Secondary Index: GSI1_Status
    GSI_NAME = "GSI1_Status"
    GSI_PARTITION_KEY = "status"
    GSI_SORT_KEY = "created_at"

    # Attributes used for querying
    QUERY_ATTRIBUTES = [
        "item_id",
        "status",
        "created_at",
        "niche",
        "source_platform",
        "original_caption",
        "ai_caption",
        "image_cloudfront_url",
    ]

    # Attributes required for insert
    REQUIRED_ATTRIBUTES = [
        "item_id",
        "status",
        "created_at",
        "niche",
        "source_platform",
        "source_url",
    ]

    # Attributes only set during ingestion (Phase 2)
    INGESTION_ATTRIBUTES = [
        "original_caption",
        "original_image_url",
        "scraped_at",
    ]

    # Attributes only set during processing (Phase 3)
    PROCESSING_ATTRIBUTES = [
        "ai_caption",
        "image_s3_key",
        "image_cloudfront_url",
        "processed_at",
    ]

    # Attributes only set during approval (Phase 4)
    APPROVAL_ATTRIBUTES = [
        "approved_by",
        "approved_at",
    ]

    # Attributes only set during posting (Phase 5)
    POSTING_ATTRIBUTES = [
        "post_id",
        "post_url",
        "posted_at",
    ]

    # Attributes used for error handling
    ERROR_ATTRIBUTES = [
        "error_log",
        "retry_count",
    ]

    @staticmethod
    def validate_item(item: ContentItem) -> tuple[bool, Optional[str]]:
        """
        Validate a content item for required attributes.
        
        Args:
            item: ContentItem to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        for attr in DynamoDBSchema.REQUIRED_ATTRIBUTES:
            if attr not in item or not item[attr]:
                return False, f"Missing required attribute: {attr}"

        # Validate status is valid
        valid_statuses = [s.value for s in ItemStatus]
        if item.get("status") not in valid_statuses:
            return False, f"Invalid status. Must be one of: {valid_statuses}"

        return True, None

    @staticmethod
    def create_raw_item(
        item_id: str,
        created_at: str,
        niche: str,
        source_platform: str,
        source_url: str,
    ) -> ContentItem:
        """
        Create a new RAW item (Phase 1 foundation).
        
        Args:
            item_id: Unique identifier
            created_at: ISO 8601 creation timestamp
            niche: Content niche
            source_platform: Scraping source platform
            source_url: Source content URL
        
        Returns:
            ContentItem ready for DynamoDB insert
        """
        return ContentItem(
            item_id=item_id,
            status=ItemStatus.RAW.value,
            created_at=created_at,
            niche=niche,
            source_platform=source_platform,
            source_url=source_url,
        )

    @staticmethod
    def get_display_name() -> str:
        """Get human-readable table name."""
        return config.DYNAMODB_TABLE_NAME

    @staticmethod
    def get_field_description(field_name: str) -> str:
        """Get description for a field."""
        descriptions = {
            "item_id": "Unique identifier for the content item (UUID v4)",
            "status": "Current pipeline status (RAW, PROCESSING, DRAFT, APPROVED, POSTED, FAILED)",
            "created_at": "ISO 8601 timestamp when item was created",
            "niche": "Content category/niche (e.g., 'self-help', 'wellness')",
            "source_platform": "Where content was scraped from (e.g., 'tiktok', 'instagram')",
            "source_url": "Original URL of the source content",
            "original_caption": "Original text from source",
            "original_image_url": "URL to original image before processing",
            "scraped_at": "ISO 8601 timestamp when content was scraped",
            "ai_caption": "AI-generated Vietnamese caption",
            "image_s3_key": "S3 object key for processed image",
            "image_cloudfront_url": "CloudFront HTTPS URL for public image delivery",
            "processed_at": "ISO 8601 timestamp when processing completed",
            "approved_by": "User ID who approved the content",
            "approved_at": "ISO 8601 timestamp of approval",
            "post_id": "Platform-specific post ID after publishing",
            "post_url": "Direct link to published post",
            "posted_at": "ISO 8601 timestamp when posted",
            "error_log": "JSON string with error details if failed",
            "retry_count": "Number of processing retry attempts",
        }
        return descriptions.get(field_name, "")
