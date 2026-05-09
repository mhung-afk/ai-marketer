"""
Claude Caption Generator for Vietnamese Captions

Generates brand-aligned Vietnamese captions with hashtags using Anthropic Claude.
"""

import logging
from typing import Optional
from anthropic import Anthropic, APIError
from common import config
from common.error_handlers import ClaudeError, retry_with_backoff

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for generating Vietnamese captions using Claude Haiku."""

    SYSTEM_PROMPT = """You are a creative copywriter for "Healing Bedroom", a Vietnamese wellness brand focused on bedroom aesthetics, sleep quality, and self-care.

Your tone should be: calming, aspirational, wellness-focused, and authentic. Avoid hard selling.

Your task: Transform original captions into brand-aligned Vietnamese captions with 3-5 relevant hashtags.

Format your response ONLY as:
[Vietnamese caption here with natural language]
#hashtag1 #hashtag2 #hashtag3"""

    def __init__(self, api_key: str):
        """
        Initialize Claude caption generator.

        Args:
            api_key: Anthropic API key
        """
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-3-5-haiku-20241022"  # Latest Haiku model
        self.max_tokens = 300

    def generate_caption(
        self,
        original_caption: str,
        source_platform: str,
        tone: str = "aesthetic"
    ) -> str:
        """
        Generate Vietnamese caption from original caption.

        Args:
            original_caption: Original caption from social media
            source_platform: Source platform (tiktok, instagram, facebook)
            tone: Caption tone (calming, motivational, aesthetic, aspirational)

        Returns:
            Vietnamese caption with hashtags

        Raises:
            ClaudeError: If API call fails
        """
        user_message = f"""Original caption from {source_platform}: "{original_caption}"

Generate a Vietnamese caption in {tone} tone. Include 3-5 relevant hashtags.
Keep the caption to max 300 characters."""

        try:
            # Use retry logic for API calls
            def call_claude():
                return self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=self.SYSTEM_PROMPT,
                    messages=[
                        {"role": "user", "content": user_message}
                    ]
                )

            response = retry_with_backoff(
                call_claude,
                max_retries=3,
                base_delay=1
            )

            caption = response.content[0].text
            logger.info(f"Generated caption: {caption[:50]}...")
            return caption

        except Exception as e:
            # Check for status code (APIError or mock objects)
            status_code = getattr(e, 'status_code', None)
            if status_code == 401:
                raise ClaudeError("Invalid API key")
            elif status_code == 429:
                raise ClaudeError("Rate limit exceeded")
            else:
                raise ClaudeError(f"Failed to generate caption: {e}")

    def parse_caption_response(self, response_text: str) -> tuple[str, list[str]]:
        """
        Parse Claude response to extract caption and hashtags.

        Args:
            response_text: Raw response from Claude

        Returns:
            Tuple of (vietnamese_caption, hashtags_list)
        """
        lines = response_text.strip().split("\n")

        caption = ""
        hashtags = []

        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                # Extract hashtags
                hashtags = line.split()
            elif line:
                # First non-hashtag line is the caption
                if not caption:
                    caption = line

        return caption, hashtags
