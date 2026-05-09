"""
Shared Error Handling for Phase 2 Content Ingestion Pipeline

This module defines custom exceptions and retry logic for Lambda functions.
"""

import time
import logging
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


# ============================================================================
# Custom Exceptions
# ============================================================================

class IngestionError(Exception):
    """Base exception for content ingestion pipeline."""
    pass


class ApifyError(IngestionError):
    """Error from Apify API client."""
    pass


class ClaudeError(IngestionError):
    """Error from Anthropic Claude API."""
    pass


class ImageProcessingError(IngestionError):
    """Error downloading, hashing, or processing images."""
    pass


class DeduplicationError(IngestionError):
    """Error during content deduplication check."""
    pass


class S3UploadError(IngestionError):
    """Error uploading content to S3."""
    pass


# ============================================================================
# Retry Logic
# ============================================================================

def retry_with_backoff(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    base_delay: int = 1,
    **kwargs: Any
) -> T:
    """
    Execute function with exponential backoff retry logic.

    Args:
        func: Function to execute
        *args: Positional arguments to pass to func
        max_retries: Maximum number of retries (default 3)
        base_delay: Initial delay in seconds (default 1s; will double each retry)
        **kwargs: Keyword arguments to pass to func

    Returns:
        Result from successful function call

    Raises:
        Exception: If all retries exhausted
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            logger.info(f"Attempt {attempt + 1}/{max_retries}")
            return func(*args, **kwargs)

        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s..."
                )
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} attempts failed")

    raise last_exception
