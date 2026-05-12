"""
Shared Utilities Module

This module provides common utilities used across the application.
"""

import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
ssm_client = boto3.client("ssm")
logger = logging.getLogger(__name__)


def generate_item_id() -> str:
    """
    Generate a unique item ID using UUID v4.

    Returns:
        A new UUID v4 string.
    """
    return str(uuid.uuid4())


def get_iso8601_timestamp(dt: Optional[datetime] = None) -> str:
    """
    Get current timestamp in ISO 8601 format (UTC).

    Args:
        dt: Optional datetime object. If not provided, uses current UTC time.

    Returns:
        ISO 8601 formatted timestamp string.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def get_parameter(parameter_name: str, with_decryption: bool = False) -> Optional[str]:
    """
    Retrieve a single parameter from AWS Systems Manager Parameter Store.

    Args:
        parameter_name: Name of the parameter to retrieve.
        with_decryption: Whether to decrypt the parameter value.

    Returns:
        The parameter value, or None if not found.

    Raises:
        ClientError: If AWS API call fails.
    """
    try:
        response = ssm_client.get_parameter(Name=parameter_name, WithDecryption=with_decryption)
        logger.info(f"Successfully retrieved parameter: {parameter_name}")
        return response["Parameter"]["Value"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ParameterNotFound":
            logger.warning(f"Parameter not found: {parameter_name}")
            return None
        logger.error(f"Error retrieving parameter {parameter_name}: {e}")
        raise
