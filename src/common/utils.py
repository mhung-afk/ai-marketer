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
        response = ssm_client.get_parameter(
            Name=parameter_name,
            WithDecryption=with_decryption
        )
        logger.info(f"Successfully retrieved parameter: {parameter_name}")
        return response["Parameter"]["Value"]
    except ClientError as e:
        if e.response["Error"]["Code"] == "ParameterNotFound":
            logger.warning(f"Parameter not found: {parameter_name}")
            return None
        logger.error(f"Error retrieving parameter {parameter_name}: {e}")
        raise


def get_parameters(
    parameter_names: list[str],
    with_decryption: bool = False
) -> Dict[str, Optional[str]]:
    """
    Retrieve multiple parameters from AWS Systems Manager Parameter Store.
    
    Args:
        parameter_names: List of parameter names to retrieve.
        with_decryption: Whether to decrypt parameter values.
    
    Returns:
        Dictionary mapping parameter names to values. Missing parameters map to None.
    
    Raises:
        ClientError: If AWS API call fails.
    """
    if not parameter_names:
        return {}

    try:
        response = ssm_client.get_parameters(
            Names=parameter_names,
            WithDecryption=with_decryption
        )

        # Create result dictionary with all requested parameters
        results = {name: None for name in parameter_names}

        # Fill in found parameters
        for param in response["Parameters"]:
            results[param["Name"]] = param["Value"]

        # Log missing parameters
        if response["InvalidParameters"]:
            logger.warning(f"Parameters not found: {response['InvalidParameters']}")

        logger.info(f"Successfully retrieved {len(response['Parameters'])} of {len(parameter_names)} parameters")
        return results

    except ClientError as e:
        logger.error(f"Error retrieving parameters: {e}")
        raise


def parse_json(json_string: str) -> Optional[Dict[str, Any]]:
    """
    Parse JSON string safely.
    
    Args:
        json_string: JSON string to parse.
    
    Returns:
        Parsed dictionary, or None if parsing fails.
    """
    try:
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")
        return None


def to_json(obj: Any, indent: bool = False) -> str:
    """
    Convert object to JSON string.
    
    Args:
        obj: Object to serialize.
        indent: Whether to pretty-print the JSON.
    
    Returns:
        JSON string representation.
    """
    return json.dumps(obj, indent=2 if indent else None, default=str)
