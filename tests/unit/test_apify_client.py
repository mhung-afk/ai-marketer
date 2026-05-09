"""
Unit tests for Apify client.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/lambdas/ingestion")))

from apify_client import ApifyClient
from common.error_handlers import ApifyError


@pytest.fixture
def apify_client():
    """Create an Apify client for testing."""
    return ApifyClient("fake-api-token")


@patch("apify_client.requests.post")
def test_start_actor_run_success(mock_post, apify_client):
    """Test successful actor run start."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {"id": "run-123"}
    }
    mock_post.return_value = mock_response

    run_id = apify_client.start_actor_run(
        "tiktok-actor-id",
        {"hashtags": ["test"], "max_posts": 10}
    )

    assert run_id == "run-123"
    mock_post.assert_called_once()


@patch("apify_client.requests.post")
def test_start_actor_run_auth_error(mock_post, apify_client):
    """Test authentication error handling."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Invalid API token"
    mock_post.return_value = mock_response

    with pytest.raises(ApifyError, match="Authentication failed"):
        apify_client.start_actor_run("actor-id", {})


@patch("apify_client.requests.post")
def test_start_actor_run_rate_limit(mock_post, apify_client):
    """Test rate limit error handling."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limit exceeded"
    mock_post.return_value = mock_response

    with pytest.raises(ApifyError, match="Rate limit exceeded"):
        apify_client.start_actor_run("actor-id", {})


@patch("apify_client.requests.get")
def test_get_run_status(mock_get, apify_client):
    """Test retrieving run status."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "id": "run-123",
            "status": "SUCCEEDED",
            "itemsCount": 15
        }
    }
    mock_get.return_value = mock_response

    status = apify_client.get_run_status("run-123")

    assert status["id"] == "run-123"
    assert status["status"] == "SUCCEEDED"


@patch("apify_client.requests.get")
def test_retrieve_results(mock_get, apify_client):
    """Test retrieving results from completed run."""
    items = [
        {"id": "item-1", "caption": "test caption 1"},
        {"id": "item-2", "caption": "test caption 2"}
    ]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = items
    mock_get.return_value = mock_response

    results = apify_client.retrieve_results("run-123", limit=10)

    assert len(results) == 2
    assert results[0]["id"] == "item-1"
