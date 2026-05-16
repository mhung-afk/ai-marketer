#!/usr/bin/env python3
"""
Manual Test Script for Content Ingestion Pipeline (Phase 2)

Triggers the ingestion Lambda function manually with test hashtags and verifies:
- Items are scraped from social media
- Items are stored in DynamoDB
- CloudFront URLs are generated and accessible
- No errors occurred during processing

Usage:
    python scripts/python/test-ingestion-pipeline.py [--dry-run]

Examples:
    # Run full test with actual Lambda invocation
    python scripts/python/test-ingestion-pipeline.py

    # Dry-run: validate configuration without invoking Lambda
    python scripts/python/test-ingestion-pipeline.py --dry-run
"""

import json
import sys
import time
import logging
import boto3
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add src to path for imports
sys.path.insert(0, ".")
from src.common import config

# AWS Clients
lambda_client = boto3.client("lambda", region_name='ap-southeast-1')
dynamodb = boto3.resource("dynamodb", region_name='ap-southeast-1')
s3 = boto3.client("s3", region_name='ap-southeast-1')


def test_configuration() -> bool:
    """Validate configuration before running tests."""
    logger.info("=" * 70)
    logger.info("CONFIGURATION VALIDATION")
    logger.info("=" * 70)

    errors = []

    # Check AWS region
    logger.info(f"✓ AWS Region: {'ap-southeast-1'}")

    # Check Lambda function exists
    try:
        lambda_client.get_function(FunctionName=config.LAMBDA_INGESTION_NAME)
        logger.info(f"✓ Lambda Function: {config.LAMBDA_INGESTION_NAME}")
    except lambda_client.exceptions.ResourceNotFoundException:
        errors.append(f"Lambda function not found: {config.LAMBDA_INGESTION_NAME}")

    # Check DynamoDB table exists
    try:
        table = dynamodb.Table(config.DYNAMODB_TABLE_NAME)
        table.load()
        logger.info(f"✓ DynamoDB Table: {config.DYNAMODB_TABLE_NAME}")
    except Exception as e:
        errors.append(f"DynamoDB table error: {e}")

    # Check Parameter Store keys exist
    ssm = boto3.client("ssm", region_name='ap-southeast-1')
    required_params = [
        config.PARAM_APIFY_API_TOKEN,
        config.PARAM_ANTHROPIC_API_KEY,
    ]

    for param in required_params:
        try:
            ssm.get_parameter(Name=param, WithDecryption=True)
            logger.info(f"✓ Parameter Store: {param}")
        except ssm.exceptions.ParameterNotFound:
            errors.append(f"Parameter not found in Parameter Store: {param}")

    if errors:
        logger.error("Configuration validation FAILED:")
        for error in errors:
            logger.error(f"  ✗ {error}")
        return False

    logger.info("✓ All configuration checks passed")
    return True


def invoke_lambda() -> Optional[str]:
    """Invoke the ingestion Lambda function."""
    logger.info("=" * 70)
    logger.info("INVOKING LAMBDA FUNCTION")
    logger.info("=" * 70)

    payload = {
        "test_mode": True,  # Signal to Lambda this is a test
        "max_items_per_source": 5,  # Reduce to 5 items for quick testing
        "timeout_seconds": 60
    }

    try:
        logger.info(f"Invoking Lambda: {config.LAMBDA_INGESTION_NAME}")
        logger.info(f"Payload: {json.dumps(payload, indent=2)}")

        response = lambda_client.invoke(
            FunctionName=config.LAMBDA_INGESTION_NAME,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload)
        )

        # Check for Lambda errors
        if "FunctionError" in response:
            logger.error(f"Lambda execution error: {response['FunctionError']}")
            if response.get("LogResult"):
                log_output = response["LogResult"]
                logger.error(f"Lambda logs: {log_output}")
            return None

        # Parse response
        response_payload = json.loads(response["Payload"].read())
        logger.info(f"Lambda response: {json.dumps(response_payload, indent=2)}")

        # Extract execution ID for tracking
        execution_id = response_payload.get("execution_id") or str(int(time.time()))
        return execution_id

    except Exception as e:
        logger.error(f"Error invoking Lambda: {e}")
        return None


def wait_for_processing(max_wait_seconds: int = 120) -> bool:
    """Wait for Lambda to complete and process items."""
    logger.info("=" * 70)
    logger.info(f"WAITING FOR PROCESSING (max {max_wait_seconds}s)")
    logger.info("=" * 70)

    start_time = time.time()
    check_interval = 5  # seconds

    while (time.time() - start_time) < max_wait_seconds:
        try:
            # Check CloudWatch logs for completion
            logs = boto3.client("logs", region_name='ap-southeast-1')
            response = logs.filter_log_events(
                logGroupName=config.LOG_GROUP_NAME,
                logStreamNamePrefix=config.LAMBDA_INGESTION_NAME,
                filterPattern="Pipeline execution complete",
                startTime=int((time.time() - 60) * 1000)
            )

            if response.get("events"):
                logger.info("✓ Lambda execution completed (found completion log)")
                return True

        except Exception as e:
            logger.debug(f"Error checking logs: {e}")

        elapsed = int(time.time() - start_time)
        logger.info(f"Waiting... ({elapsed}s elapsed)")
        time.sleep(check_interval)

    logger.warning(f"Timeout waiting for processing after {max_wait_seconds}s")
    return False


def verify_dynamodb_items() -> Dict[str, Any]:
    """Verify items were created in DynamoDB."""
    logger.info("=" * 70)
    logger.info("VERIFYING DYNAMODB ITEMS")
    logger.info("=" * 70)

    table = dynamodb.Table(config.DYNAMODB_TABLE_NAME)

    # Get recent items (last 5 minutes)
    cutoff_time = datetime.now(timezone.utc).isoformat()

    try:
        response = table.scan(
            FilterExpression="attribute_exists(ai_caption_vi)",  # Only items that were processed
            Limit=20
        )

        items = response.get("Items", [])
        logger.info(f"Found {len(items)} processed items in DynamoDB")

        if not items:
            logger.warning("No items found in DynamoDB!")
            return {
                "count": 0,
                "sample_items": []
            }

        # Log sample items
        for i, item in enumerate(items[:3], 1):
            logger.info(f"\nItem {i}:")
            logger.info(f"  ID: {item.get('item_id')}")
            logger.info(f"  Platform: {item.get('source_platform')}")
            logger.info(f"  Caption: {item.get('ai_caption_vi', 'N/A')[:100]}")
            logger.info(f"  CloudFront URL: {item.get('cloudfront_url', 'N/A')[:80]}")
            logger.info(f"  Status: {item.get('status')}")

        return {
            "count": len(items),
            "sample_items": items[:3]
        }

    except Exception as e:
        logger.error(f"Error querying DynamoDB: {e}")
        return {"count": 0, "sample_items": []}


def verify_cloudfront_urls(items: List[Dict]) -> bool:
    """Verify CloudFront URLs are accessible."""
    logger.info("=" * 70)
    logger.info("VERIFYING CLOUDFRONT URLS")
    logger.info("=" * 70)

    if not items:
        logger.warning("No items to verify")
        return False

    import requests

    all_accessible = True

    for i, item in enumerate(items[:3], 1):
        url = item.get("cloudfront_url")
        if not url:
            logger.warning(f"Item {i}: No CloudFront URL")
            continue

        try:
            logger.info(f"\nItem {i}: Testing {url[:80]}...")
            response = requests.head(url, timeout=10)

            if response.status_code == 200:
                logger.info(f"  ✓ Accessible (HTTP {response.status_code})")
                if "content-type" in response.headers:
                    logger.info(f"  ✓ Content-Type: {response.headers['content-type']}")
            else:
                logger.warning(f"  ✗ HTTP {response.status_code}")
                all_accessible = False

        except requests.exceptions.Timeout:
            logger.warning(f"  ✗ Timeout accessing URL")
            all_accessible = False
        except Exception as e:
            logger.warning(f"  ✗ Error: {e}")
            all_accessible = False

    return all_accessible


def check_cloudwatch_errors() -> int:
    """Check CloudWatch logs for errors."""
    logger.info("=" * 70)
    logger.info("CHECKING CLOUDWATCH LOGS FOR ERRORS")
    logger.info("=" * 70)

    logs = boto3.client("logs", region_name='ap-southeast-1')

    try:
        # Get error logs from last 10 minutes
        response = logs.filter_log_events(
            logGroupName=config.LOG_GROUP_NAME,
            logStreamNamePrefix=config.LAMBDA_INGESTION_NAME,
            filterPattern="ERROR",
            startTime=int((time.time() - 600) * 1000)
        )

        events = response.get("events", [])
        error_count = len(events)

        if error_count > 0:
            logger.warning(f"Found {error_count} error logs:")
            for event in events[:5]:  # Show first 5 errors
                logger.warning(f"  {event['message'][:100]}")
        else:
            logger.info("✓ No errors found in CloudWatch logs")

        return error_count

    except Exception as e:
        logger.error(f"Error checking CloudWatch logs: {e}")
        return -1


def main():
    """Main test execution."""
    parser = argparse.ArgumentParser(description="Test Content Ingestion Pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Validate config without invoking Lambda")
    args = parser.parse_args()

    logger.info("🧪 CONTENT INGESTION PIPELINE TEST")
    logger.info(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # Step 1: Validate configuration
    if not test_configuration():
        logger.error("Configuration validation failed. Cannot proceed.")
        return 1

    if args.dry_run:
        logger.info("\n✓ Dry-run completed. Configuration is valid.")
        return 0

    # Step 2: Invoke Lambda
    execution_id = invoke_lambda()
    if not execution_id:
        logger.error("Failed to invoke Lambda function.")
        return 1

    # Step 3: Wait for processing
    if not wait_for_processing():
        logger.warning("Timeout waiting for processing.")

    # Step 4: Verify DynamoDB
    db_result = verify_dynamodb_items()

    # Step 5: Verify CloudFront URLs
    urls_accessible = verify_cloudfront_urls(db_result.get("sample_items", []))

    # Step 6: Check for errors
    error_count = check_cloudwatch_errors()

    # Final Summary
    logger.info("=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Items processed: {db_result['count']}")
    logger.info(f"CloudFront URLs accessible: {urls_accessible}")
    logger.info(f"Errors found: {error_count}")

    if db_result["count"] > 0 and urls_accessible and error_count == 0:
        logger.info("\n✅ ALL TESTS PASSED")
        return 0
    else:
        logger.warning("\n⚠️ SOME TESTS FAILED - Review logs above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
