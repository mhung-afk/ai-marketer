"""
Unit tests for deduplication logic.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/lambdas/ingestion")))

from deduplication import check_duplicate_by_hash, check_duplicate_by_url
from common.error_handlers import DeduplicationError


@patch("deduplication.boto3.resource")
def test_check_duplicate_by_hash_found(mock_dynamodb_resource):
    """Test finding a duplicate by hash."""
    mock_table = MagicMock()
    mock_table.query.return_value = {
        "Items": [
            {"item_id": "item-1", "content_hash": "abc123"}
        ]
    }

    mock_dynamodb_resource.return_value.Table.return_value = mock_table

    is_dup, existing_id = check_duplicate_by_hash("abc123")

    assert is_dup is True
    assert existing_id == "item-1"


@patch("deduplication.boto3.resource")
def test_check_duplicate_by_hash_not_found(mock_dynamodb_resource):
    """Test when no duplicate is found."""
    mock_table = MagicMock()
    mock_table.query.return_value = {"Items": []}

    mock_dynamodb_resource.return_value.Table.return_value = mock_table

    is_dup, existing_id = check_duplicate_by_hash("new_hash")

    assert is_dup is False
    assert existing_id is None


@patch("deduplication.boto3.resource")
def test_check_duplicate_by_url_found(mock_dynamodb_resource):
    """Test finding a duplicate by URL."""
    mock_table = MagicMock()
    mock_table.scan.return_value = {
        "Items": [
            {"item_id": "item-2", "source_url": "https://tiktok.com/video/123"}
        ]
    }

    mock_dynamodb_resource.return_value.Table.return_value = mock_table

    is_dup, existing_id = check_duplicate_by_url("https://tiktok.com/video/123")

    assert is_dup is True
    assert existing_id == "item-2"


@patch("deduplication.boto3.resource")
def test_check_duplicate_by_url_not_found(mock_dynamodb_resource):
    """Test when no URL duplicate is found."""
    mock_table = MagicMock()
    mock_table.scan.return_value = {"Items": []}

    mock_dynamodb_resource.return_value.Table.return_value = mock_table

    is_dup, existing_id = check_duplicate_by_url("https://newurl.com/image")

    assert is_dup is False
    assert existing_id is None
