#!/usr/bin/env python3
"""
Health Check Script for Content Ingestion Pipeline (Phase 2)

Verifies that all Phase 2 AWS resources are deployed and functional:
- Lambda function exists and is configured correctly
- EventBridge scheduler is active
- SQS dead-letter queue exists
- DynamoDB GSI created successfully
- Parameter Store credentials accessible
- External API connectivity (Apify, Claude)

Usage:
    python scripts/python/health-check-ingestion.py

Exit Codes:
    0: All checks passed
    1: Some checks failed
    2: Critical failures (cannot proceed)
"""

import sys
import json
import logging
import boto3
from typing import Dict, List, Tuple

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
lambda_client = boto3.client("lambda", region_name=config.AWS_REGION)
events_client = boto3.client("events", region_name=config.AWS_REGION)
sqs_client = boto3.client("sqs", region_name=config.AWS_REGION)
dynamodb_client = boto3.client("dynamodb", region_name=config.AWS_REGION)
ssm_client = boto3.client("ssm", region_name=config.AWS_REGION)


class HealthCheck:
    """Performs comprehensive health checks on Phase 2 resources."""

    def __init__(self):
        """Initialize health check state."""
        self.checks_passed = []
        self.checks_failed = []
        self.critical_failures = []

    def log_pass(self, check_name: str, details: str = ""):
        """Log a passed check."""
        logger.info(f"✅ {check_name}")
        if details:
            logger.info(f"   {details}")
        self.checks_passed.append(check_name)

    def log_fail(self, check_name: str, reason: str, is_critical: bool = False):
        """Log a failed check."""
        symbol = "🔴" if is_critical else "⚠️"
        logger.warning(f"{symbol} {check_name}")
        logger.warning(f"   Reason: {reason}")
        self.checks_failed.append(check_name)
        if is_critical:
            self.critical_failures.append(check_name)

    def check_lambda_function(self) -> bool:
        """Check if Lambda function exists and is configured correctly."""
        logger.info("\n" + "=" * 70)
        logger.info("LAMBDA FUNCTION")
        logger.info("=" * 70)

        try:
            response = lambda_client.get_function(
                FunctionName=config.LAMBDA_INGESTION_NAME
            )

            func_config = response["Configuration"]
            func_arn = func_config["FunctionArn"]

            self.log_pass(
                "Lambda function exists",
                f"ARN: {func_arn}"
            )

            # Check runtime
            runtime = func_config.get("Runtime", "unknown")
            if "python3" in runtime:
                self.log_pass(f"Lambda runtime is Python: {runtime}")
            else:
                self.log_fail("Lambda runtime incorrect", f"Expected Python, got {runtime}")

            # Check timeout
            timeout = func_config.get("Timeout", 0)
            if timeout >= 300:
                self.log_pass(f"Lambda timeout is sufficient: {timeout}s")
            else:
                self.log_fail("Lambda timeout too short", f"Got {timeout}s, need ≥300s")

            # Check memory
            memory = func_config.get("MemorySize", 0)
            if memory >= 512:
                self.log_pass(f"Lambda memory allocation: {memory} MB")
            else:
                self.log_fail("Lambda memory too low", f"Got {memory}MB, recommend ≥512MB")

            # Check environment variables
            env_vars = func_config.get("Environment", {}).get("Variables", {})
            if "AWS_REGION" in env_vars:
                self.log_pass("Lambda environment configured")
            else:
                logger.warning("Lambda environment variables may be missing")

            return True

        except lambda_client.exceptions.ResourceNotFoundException:
            self.log_fail(
                "Lambda function not found",
                f"Function name: {config.LAMBDA_INGESTION_NAME}",
                is_critical=True
            )
            return False
        except Exception as e:
            self.log_fail("Error checking Lambda", str(e), is_critical=True)
            return False

    def check_eventbridge_scheduler(self) -> bool:
        """Check if EventBridge scheduler rule is active."""
        logger.info("\n" + "=" * 70)
        logger.info("EVENTBRIDGE SCHEDULER")
        logger.info("=" * 70)

        try:
            response = events_client.describe_rule(
                Name="healing-bedroom-ingestion-scheduler"
            )

            state = response.get("State", "unknown")

            if state == "ENABLED":
                self.log_pass(
                    "EventBridge scheduler is ENABLED",
                    f"Schedule: {response.get('ScheduleExpression', 'N/A')}"
                )
                return True
            else:
                self.log_fail(
                    "EventBridge scheduler not active",
                    f"State: {state}"
                )
                return False

        except events_client.exceptions.ResourceNotFoundException:
            self.log_fail(
                "EventBridge scheduler rule not found",
                "Rule name: healing-bedroom-ingestion-scheduler",
                is_critical=True
            )
            return False
        except Exception as e:
            self.log_fail("Error checking EventBridge", str(e), is_critical=True)
            return False

    def check_sqs_dlq(self) -> bool:
        """Check if SQS dead-letter queue exists."""
        logger.info("\n" + "=" * 70)
        logger.info("SQS DEAD-LETTER QUEUE")
        logger.info("=" * 70)

        try:
            # Get queue URL
            response = sqs_client.get_queue_url(QueueName=config.SQS_DLQ_NAME)
            queue_url = response["QueueUrl"]

            # Get queue attributes
            attrs = sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=["All"]
            )

            attributes = attrs.get("Attributes", {})
            msg_count = int(attributes.get("ApproximateNumberOfMessages", 0))

            self.log_pass(
                "SQS dead-letter queue exists",
                f"URL: {queue_url} | Messages: {msg_count}"
            )

            # Check if too many messages are queued
            if msg_count > 10:
                logger.warning(f"⚠️ DLQ has high message count ({msg_count}). Items may be stuck.")

            return True

        except sqs_client.exceptions.QueueDoesNotExist:
            self.log_fail(
                "SQS dead-letter queue not found",
                f"Queue name: {config.SQS_DLQ_NAME}",
                is_critical=True
            )
            return False
        except Exception as e:
            self.log_fail("Error checking SQS", str(e), is_critical=True)
            return False

    def check_dynamodb_gsi(self) -> bool:
        """Check if DynamoDB GSI exists."""
        logger.info("\n" + "=" * 70)
        logger.info("DYNAMODB GLOBAL SECONDARY INDEX")
        logger.info("=" * 70)

        try:
            response = dynamodb_client.describe_table(
                TableName=config.DYNAMODB_TABLE_NAME
            )

            table_desc = response.get("Table", {})
            gsi_list = table_desc.get("GlobalSecondaryIndexes", [])

            # Look for GSI_ContentHash
            gsi_found = False
            for gsi in gsi_list:
                if gsi["IndexName"] == "GSI_ContentHash":
                    gsi_found = True
                    status = gsi.get("IndexStatus", "unknown")

                    if status == "ACTIVE":
                        self.log_pass(
                            "DynamoDB GSI_ContentHash is ACTIVE",
                            f"Key: {gsi.get('KeySchema', [])}"
                        )
                    else:
                        self.log_fail(
                            "DynamoDB GSI not active",
                            f"Status: {status}"
                        )
                    break

            if not gsi_found:
                self.log_fail(
                    "DynamoDB GSI_ContentHash not found",
                    "GSI must be created for deduplication",
                    is_critical=True
                )
                return False

            return True

        except dynamodb_client.exceptions.ResourceNotFoundException:
            self.log_fail(
                "DynamoDB table not found",
                f"Table name: {config.DYNAMODB_TABLE_NAME}",
                is_critical=True
            )
            return False
        except Exception as e:
            self.log_fail("Error checking DynamoDB", str(e), is_critical=True)
            return False

    def check_parameter_store(self) -> bool:
        """Check if all required Parameter Store keys are accessible."""
        logger.info("\n" + "=" * 70)
        logger.info("PARAMETER STORE CREDENTIALS")
        logger.info("=" * 70)

        required_params = [
            (config.PARAM_APIFY_API_TOKEN, "Apify API Token"),
            (config.PARAM_ANTHROPIC_API_KEY, "Anthropic API Key"),
            (config.PARAM_TELEGRAM_BOT_TOKEN, "Telegram Bot Token"),
            (config.PARAM_TELEGRAM_CHAT_ID, "Telegram Chat ID"),
        ]

        all_accessible = True

        for param_name, param_desc in required_params:
            try:
                response = ssm_client.get_parameter(
                    Name=param_name,
                    WithDecryption=True
                )

                # Mask sensitive values in logs
                value = response["Parameter"]["Value"]
                if len(value) > 10:
                    masked_value = value[:4] + "..." + value[-4:]
                else:
                    masked_value = "***"

                self.log_pass(
                    f"Parameter Store key accessible: {param_desc}",
                    f"Path: {param_name}"
                )

            except ssm_client.exceptions.ParameterNotFound:
                self.log_fail(
                    f"Parameter Store key missing: {param_desc}",
                    f"Path: {param_name}"
                )
                all_accessible = False

            except Exception as e:
                self.log_fail(
                    f"Error accessing {param_desc}",
                    str(e)
                )
                all_accessible = False

        return all_accessible

    def check_api_connectivity(self) -> bool:
        """Check connectivity to external APIs."""
        logger.info("\n" + "=" * 70)
        logger.info("EXTERNAL API CONNECTIVITY")
        logger.info("=" * 70)

        import requests

        # Check Apify connectivity
        try:
            token = ssm_client.get_parameter(
                Name=config.PARAM_APIFY_API_TOKEN,
                WithDecryption=True
            )["Parameter"]["Value"]

            response = requests.get(
                "https://api.apify.com/v2/users/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                user_email = data.get("data", {}).get("email", "unknown")
                self.log_pass(
                    "Apify API connectivity verified",
                    f"User: {user_email}"
                )
            else:
                self.log_fail(
                    "Apify API returned error",
                    f"HTTP {response.status_code}: {response.text[:100]}"
                )

        except Exception as e:
            self.log_fail("Error checking Apify connectivity", str(e))

        # Check Claude/Anthropic connectivity
        try:
            api_key = ssm_client.get_parameter(
                Name=config.PARAM_ANTHROPIC_API_KEY,
                WithDecryption=True
            )["Parameter"]["Value"]

            response = requests.get(
                "https://api.anthropic.com/v1/account",
                headers={"x-api-key": api_key},
                timeout=10
            )

            if response.status_code == 200:
                self.log_pass(
                    "Claude/Anthropic API connectivity verified"
                )
            elif response.status_code == 401:
                self.log_fail(
                    "Claude/Anthropic API authentication failed",
                    "Check API key in Parameter Store"
                )
            else:
                self.log_fail(
                    "Claude/Anthropic API returned error",
                    f"HTTP {response.status_code}"
                )

        except Exception as e:
            self.log_fail("Error checking Claude connectivity", str(e))

        return True

    def generate_report(self) -> int:
        """Generate final health check report."""
        logger.info("\n" + "=" * 70)
        logger.info("HEALTH CHECK REPORT")
        logger.info("=" * 70)

        logger.info(f"✅ Checks Passed: {len(self.checks_passed)}")
        logger.info(f"⚠️ Checks Failed: {len(self.checks_failed)}")
        logger.info(f"🔴 Critical Failures: {len(self.critical_failures)}")

        if self.critical_failures:
            logger.error("\n🔴 CRITICAL FAILURES DETECTED:")
            for failure in self.critical_failures:
                logger.error(f"  - {failure}")

            logger.error("\n❌ HEALTH CHECK FAILED - Cannot deploy")
            return 2

        elif self.checks_failed:
            logger.warning("\n⚠️ SOME CHECKS FAILED:")
            for failure in self.checks_failed:
                logger.warning(f"  - {failure}")

            logger.warning("\n✅ HEALTH CHECK PASSED (with warnings)")
            return 1

        else:
            logger.info("\n✅ ALL CHECKS PASSED - System is healthy")
            return 0


def main():
    """Main health check execution."""
    logger.info("🏥 CONTENT INGESTION PIPELINE HEALTH CHECK")
    logger.info(f"Region: {config.AWS_REGION}")

    checker = HealthCheck()

    # Run all checks
    checker.check_lambda_function()
    checker.check_eventbridge_scheduler()
    checker.check_sqs_dlq()
    checker.check_dynamodb_gsi()
    checker.check_parameter_store()
    checker.check_api_connectivity()

    # Generate report and return exit code
    exit_code = checker.generate_report()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
