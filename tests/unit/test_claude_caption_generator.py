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
    with patch("claude_caption_generator.Anthropic"):
        client = ClaudeClient("fake-api-key")
        client.client = MagicMock()  # Replace with mock after init
        return client


def test_generate_caption_success(claude_client):
    """Test successful caption generation."""
    mock_response = MagicMock()
    mock_response.content = [
        MagicMock(text="Tạo không gian ngủ yên bình với những chiếc gối êm ái\n#BedroomGoals #SleepWellness #HealingBedroom")
    ]
    claude_client.client.messages.create.return_value = mock_response

    caption = claude_client.generate_caption(
        "Cozy bedroom setup for better sleep",
        "tiktok",
        tone="calming"
    )

    assert "Tạo không gian" in caption or "ngủ" in caption or "#" in caption
    claude_client.client.messages.create.assert_called_once()


def test_generate_caption_auth_error(claude_client):
    """Test authentication error handling."""
    # Test that 401 errors are handled correctly
    with patch("claude_caption_generator.retry_with_backoff") as mock_retry:
        error = Exception("Auth failed")
        error.status_code = 401
        mock_retry.side_effect = error

        with pytest.raises(ClaudeError, match="Invalid API key"):
            claude_client.generate_caption("test caption", "instagram")


def test_generate_caption_rate_limit(claude_client):
    """Test rate limit error handling."""
    # Test that 429 errors are handled correctly
    with patch("claude_caption_generator.retry_with_backoff") as mock_retry:
        error = Exception("Rate limit")
        error.status_code = 429
        mock_retry.side_effect = error

        with pytest.raises(ClaudeError, match="Rate limit exceeded"):
            claude_client.generate_caption("test caption", "facebook")


def test_parse_caption_response():
    """Test parsing Claude response."""
    with patch("claude_caption_generator.Anthropic"):
        client = ClaudeClient("fake-key")

    response_text = """Phòng ngủ yên tĩnh là chìa khóa để ngủ ngon.
#BedroomGoals #SleepWellness #HealingBedroom"""

    caption, hashtags = client.parse_caption_response(response_text)

    assert "Phòng ngủ" in caption or "yên tĩnh" in caption
    assert len(hashtags) >= 3
    assert any("BedroomGoals" in tag for tag in hashtags)


def test_parse_caption_response_single_hashtag():
    """Test parsing response with hashtags on one line."""
    with patch("claude_caption_generator.Anthropic"):
        client = ClaudeClient("fake-key")

    response_text = """Tạo không gian ngủ yên bình
#BedroomGoals #SleepWellness"""

    caption, hashtags = client.parse_caption_response(response_text)

    assert "Tạo không gian" in caption
    assert len(hashtags) >= 2
