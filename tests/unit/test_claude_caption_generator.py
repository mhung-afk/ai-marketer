"""
Unit tests for Claude caption generator.
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/lambdas/ingestion")))

from claude_caption_generator import ClaudeClient
from common.error_handlers import ClaudeError


@pytest.fixture
def claude_client():
    """Create Claude client for testing."""
    return ClaudeClient("fake-api-key")


@patch("claude_caption_generator.Anthropic")
def test_generate_caption_success(mock_anthropic_class, claude_client):
    """Test successful caption generation."""
    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    mock_response = MagicMock()
    mock_response.content = [
    MagicMock(text="Tạo không gian ngủ yên bình với những chiếc gối êm ái\n#BedroomGoals #SleepWellness #HealingBedroom")
    ]
    mock_client.messages.create.return_value = mock_response

    # Recreate client with mocked Anthropic
    client = ClaudeClient("fake-key")
    client.client = mock_client

    caption = client.generate_caption(
        "Cozy bedroom setup for better sleep",
        "tiktok",
        tone="calming"
    )

    assert "Tạo không gian" in caption or "ngủ" in caption or "#" in caption
    mock_client.messages.create.assert_called_once()


@patch("claude_caption_generator.Anthropic")
def test_generate_caption_auth_error(mock_anthropic_class, claude_client):
    """Test authentication error handling."""
    from anthropic import APIError

    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    # Create a mock error with status_code
    error = APIError("Unauthorized", response=MagicMock(status_code=401), body={})
    mock_client.messages.create.side_effect = error

    client = ClaudeClient("fake-key")
    client.client = mock_client

    with pytest.raises(ClaudeError, match="Invalid API key"):
        client.generate_caption("test caption", "instagram")


@patch("claude_caption_generator.Anthropic")
def test_generate_caption_rate_limit(mock_anthropic_class, claude_client):
    """Test rate limit error handling."""
    from anthropic import APIError

    mock_client = MagicMock()
    mock_anthropic_class.return_value = mock_client

    error = APIError("Rate limit", response=MagicMock(status_code=429), body={})
    mock_client.messages.create.side_effect = error

    client = ClaudeClient("fake-key")
    client.client = mock_client

    with pytest.raises(ClaudeError, match="Rate limit exceeded"):
        client.generate_caption("test caption", "facebook")


def test_parse_caption_response(claude_client):
    """Test parsing Claude response."""
    response_text = """Phòng ngủ yên tĩnh là chìa khóa để ngủ ngon.
#BedroomGoals #SleepWellness #HealingBedroom"""

    caption, hashtags = claude_client.parse_caption_response(response_text)

    assert "Phòng ngủ" in caption or "yên tĩnh" in caption
    assert len(hashtags) >= 3
    assert any("BedroomGoals" in tag for tag in hashtags)


def test_parse_caption_response_single_hashtag(claude_client):
    """Test parsing response with hashtags on one line."""
    response_text = """Tạo không gian ngủ yên bình
#BedroomGoals #SleepWellness"""

    caption, hashtags = claude_client.parse_caption_response(response_text)

    assert "Tạo không gian" in caption
    assert len(hashtags) >= 2
