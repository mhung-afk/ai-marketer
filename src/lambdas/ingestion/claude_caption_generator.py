"""
Claude Caption Generator for Vietnamese Captions

Generates brand-aligned Vietnamese captions with hashtags using Anthropic Claude.
"""

import logging
from typing import Tuple, List

from anthropic import Anthropic, APIError, RateLimitError, AuthenticationError

from common.error_handlers import ClaudeError, retry_with_backoff

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for generating Vietnamese captions using Claude."""

    SYSTEM_PROMPT = """You are a creative copywriter for "Healing Bedroom", a Vietnamese wellness brand focused on bedroom aesthetics, sleep quality, and self-care.

Your tone should be: calming, aspirational, wellness-focused, and authentic. Never hard sell.

Task: Transform the original caption into a beautiful Vietnamese caption that fits the brand voice.
Include 3-5 relevant hashtags at the end.

Rules:
- Output ONLY the caption + hashtags. No explanations.
- Caption should be natural and warm.
- Maximum 280 characters for the caption part."""

    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-haiku-4-5"   # Latest fast model (as of 2026)
        self.max_tokens = 400

    def generate_caption(
        self, 
        original_caption: str, 
        source_platform: str = "social",
        source_url: str = "",
        tone: str = "aesthetic"
    ) -> str:
        """
        Generate Vietnamese brand-aligned caption.
        """
        user_message = f"""Original caption from {source_platform}: "{original_caption}"

Source URL: {source_url} You MUST visit this URL to gain more infomation.

Create a calming, aspirational Vietnamese caption in {tone} tone for Healing Bedroom.
Include 3-5 relevant hashtags at the end."""

        try:
            def call_claude():
                return self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=0.7,
                    system=self.SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": user_message}],
                )

            response = retry_with_backoff(call_claude, max_retries=3, base_delay=1.5)
            
            caption_text = response.content[0].text.strip()
            logger.info(f"Claude generated caption ({len(caption_text)} chars): {caption_text}")
            return caption_text

        except AuthenticationError:
            raise ClaudeError("Invalid Anthropic API key")
        except RateLimitError:
            raise ClaudeError("Rate limit exceeded - try again later")
        except APIError as e:
            raise ClaudeError(f"Anthropic API error: {e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            raise ClaudeError(f"Failed to generate caption: {str(e)}")

    def parse_caption_response(self, response_text: str) -> Tuple[str, List[str]]:
        """
        Robust parser for Claude response.
        """
        if not response_text:
            return "", []

        lines = [line.strip() for line in response_text.strip().split("\n") if line.strip()]

        caption_parts = []
        hashtags = []

        for line in lines:
            if line.startswith("#"):
                # Extract all hashtags from this line
                hashtags.extend([tag for tag in line.split() if tag.startswith("#")])
            else:
                caption_parts.append(line)

        caption = " ".join(caption_parts).strip()

        # Clean duplicate hashtags
        hashtags = list(dict.fromkeys(hashtags))  # preserve order

        return caption, hashtags[:5]  # max 5 hashtags