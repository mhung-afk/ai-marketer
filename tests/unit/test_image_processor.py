"""
Unit tests for image processor.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/lambdas/ingestion")))

from image_processor import ImageProcessor
from common.error_handlers import ImageProcessingError


@pytest.fixture
def processor():
    """Create an image processor for testing."""
    return ImageProcessor()


@patch("image_processor.requests.get")
def test_download_image_success(mock_get, processor):
    """Test successful image download."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"fake_image_data"
    mock_response.headers = {"content-type": "image/jpeg"}
    mock_get.return_value = mock_response

    image_bytes, ext = processor.download_image("https://example.com/image.jpg")

    assert image_bytes == b"fake_image_data"
    assert ext == "jpg"


@patch("image_processor.requests.get")
def test_download_image_timeout(mock_get, processor):
    """Test image download timeout."""
    import requests
    mock_get.side_effect = requests.RequestException("Timeout")

    with pytest.raises(ImageProcessingError, match="Failed to download"):
        processor.download_image("https://example.com/image.jpg")


def test_compute_content_hash(processor):
    """Test MD5 hash computation."""
    image_bytes = b"test_image_data"
    hash_value = processor.compute_content_hash(image_bytes)

    # Verify hash is a 32-character hex string
    assert len(hash_value) == 32
    assert all(c in "0123456789abcdef" for c in hash_value)

    # Verify same input produces same hash
    hash_value2 = processor.compute_content_hash(image_bytes)
    assert hash_value == hash_value2


@patch("image_processor.boto3.client")
def test_upload_to_s3_success(mock_s3_client, processor):
    """Test successful S3 upload."""
    mock_client = MagicMock()
    mock_client.put_object.return_value = {"ETag": "fake-etag"}
    processor.s3_client = mock_client

    cloudfront_url = processor.upload_to_s3(b"image_data", "jpg")

    assert "cloudfront.net" in cloudfront_url
    assert cloudfront_url.startswith("https://")
    mock_client.put_object.assert_called_once()


@patch("image_processor.boto3.client")
def test_upload_to_s3_failure(mock_s3_client, processor):
    """Test S3 upload failure."""
    from botocore.exceptions import ClientError

    mock_client = MagicMock()
    error_response = {"Error": {"Code": "AccessDenied"}}
    mock_client.put_object.side_effect = ClientError(error_response, "PutObject")
    processor.s3_client = mock_client

    with pytest.raises(ImageProcessingError, match="Failed to upload"):
        processor.upload_to_s3(b"image_data", "jpg")


def test_extract_extension():
    """Test file extension extraction."""
    ext1 = ImageProcessor._extract_extension("image/jpeg", "http://example.com/pic.jpg")
    assert ext1 == "jpg"

    ext2 = ImageProcessor._extract_extension("image/png", "")
    assert ext2 == "png"

    ext3 = ImageProcessor._extract_extension("", "http://example.com/pic.gif")
    assert ext3 == "gif"


def test_get_content_type():
    """Test MIME type mapping."""
    assert ImageProcessor._get_content_type("jpg") == "image/jpeg"
    assert ImageProcessor._get_content_type("png") == "image/png"
    assert ImageProcessor._get_content_type("gif") == "image/gif"
