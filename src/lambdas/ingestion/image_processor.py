"""
Image Processing Module

Handles downloading images, computing hashes, and uploading to S3.
"""

import hashlib
import requests
import uuid
from datetime import datetime, timezone
from typing import Tuple, Optional
import logging
import boto3
from botocore.exceptions import ClientError
from common import config
from common.error_handlers import ImageProcessingError
from common.utils import get_iso8601_timestamp

logger = logging.getLogger(__name__)


class ImageProcessor:
    """Processor for handling image downloads, hashing, and S3 uploads."""

    SUPPORTED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

    def __init__(self, s3_client=None):
        """
        Initialize image processor.

        Args:
            s3_client: Optional boto3 S3 client. If not provided, creates new one.
        """
        self.s3_client = s3_client or boto3.client("s3", region_name=config.AWS_REGION)

    def download_image(self, image_url: str) -> Tuple[bytes, str]:
        """
        Download image from URL.

        Args:
            image_url: URL to image

        Returns:
            Tuple of (image_bytes, file_extension)

        Raises:
            ImageProcessingError: If download fails
        """
        try:
            response = requests.get(
                image_url,
                timeout=30,
                headers={"User-Agent": "Healing-Bedroom-Bot/1.0"}
            )
            response.raise_for_status()

            # Determine file extension from content-type or URL
            content_type = response.headers.get("content-type", "").lower()
            extension = self._extract_extension(content_type, image_url)

            if extension not in self.SUPPORTED_EXTENSIONS:
                raise ImageProcessingError(
                    f"Unsupported image type: {extension}"
                )

            logger.info(f"Downloaded image: {len(response.content)} bytes")
            return response.content, extension

        except requests.RequestException as e:
            raise ImageProcessingError(f"Failed to download image: {e}")

    def compute_content_hash(self, image_bytes: bytes) -> str:
        """
        Compute MD5 hash of image bytes for deduplication.

        Args:
            image_bytes: Raw image data

        Returns:
            Hex-encoded MD5 hash string
        """
        hash_obj = hashlib.md5()
        hash_obj.update(image_bytes)
        hash_value = hash_obj.hexdigest()

        logger.info(f"Computed content hash: {hash_value}")
        return hash_value

    def upload_to_s3(
        self,
        image_bytes: bytes,
        extension: str,
        bucket_name: Optional[str] = None
    ) -> str:
        """
        Upload image to S3 and return CloudFront URL.

        Args:
            image_bytes: Raw image data
            extension: File extension (e.g., jpg, png)
            bucket_name: S3 bucket name. If None, uses config.

        Returns:
            CloudFront URL for the uploaded image

        Raises:
            ImageProcessingError: If upload fails
        """
        bucket_name = bucket_name or config.get_bucket_name()

        # Generate S3 object key with timestamp and UUID
        now = datetime.now(timezone.utc)
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H-%M-%S")
        unique_id = str(uuid.uuid4())[:8]
        object_key = f"raw/{date_str}/{time_str}-{unique_id}.{extension}"

        try:
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=object_key,
                Body=image_bytes,
                ContentType=self._get_content_type(extension),
                ServerSideEncryption="AES256"
            )

            logger.info(f"Uploaded to S3: s3://{bucket_name}/{object_key}")

            # Generate CloudFront URL
            # Note: In production, retrieve CloudFront domain from CDK stack output
            cloudfront_domain = f"d{config.AWS_ACCOUNT_ID}.cloudfront.net"
            cloudfront_url = f"https://{cloudfront_domain}/{object_key}"

            logger.info(f"CloudFront URL: {cloudfront_url}")
            return cloudfront_url

        except ClientError as e:
            raise ImageProcessingError(f"Failed to upload to S3: {e}")

    @staticmethod
    def _extract_extension(content_type: str, url: str) -> str:
        """Extract file extension from content-type or URL."""
        # Try content-type first
        if "image/jpeg" in content_type or "image/jpg" in content_type:
            return "jpg"
        elif "image/png" in content_type:
            return "png"
        elif "image/gif" in content_type:
            return "gif"
        elif "image/webp" in content_type:
            return "webp"

        # Fall back to URL extension
        if "." in url.split("/")[-1]:
            ext = url.split(".")[-1].lower().split("?")[0]
            if ext in ImageProcessor.SUPPORTED_EXTENSIONS:
                return ext

        return "jpg"  # Default to jpg

    @staticmethod
    def _get_content_type(extension: str) -> str:
        """Map file extension to MIME type."""
        types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "webp": "image/webp"
        }
        return types.get(extension, "application/octet-stream")
