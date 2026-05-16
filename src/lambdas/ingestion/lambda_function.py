"""
Phase 2 Content Ingestion Pipeline Lambda

Orchestrates scraping, caption generation, and storage of content from social media.
Triggered by EventBridge Scheduler on configurable cron schedule.
"""

import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from typing import Dict, Any

import boto3

from common import config
from common.utils import (
    generate_item_id,
    get_iso8601_timestamp,
    get_parameter,
)
from common.schemas import ContentItem, ContentStatus, CaptureTone
from common.error_handlers import IngestionError, ApifyError, ClaudeError

import apify_actor_client
import claude_caption_generator
import deduplication
import dynamodb_storage

# Local error handlers (same folder, so direct import)
import error_handlers as ingestion_error_handlers

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def _log_structured(level: str, message: str, **kwargs) -> None:
    """
    Log a message in structured JSON format for CloudWatch Insights analysis.

    Args:
        level: Log level (INFO, ERROR, WARNING)
        message: Log message
        **kwargs: Additional fields to include in JSON log
    """
    log_entry = {"timestamp": get_iso8601_timestamp(), "level": level, "message": message, **kwargs}

    log_message = json.dumps(log_entry)

    if level == "ERROR":
        logger.error(log_message)
    elif level == "WARNING":
        logger.warning(log_message)
    else:
        logger.info(log_message)


class IngestionPipeline:
    """Orchestrates the entire content ingestion pipeline."""

    def __init__(self):
        """Initialize pipeline with AWS clients and API keys."""
        self.apify_token = get_parameter(config.PARAM_APIFY_API_TOKEN, with_decryption=True)
        self.claude_key = get_parameter(config.PARAM_ANTHROPIC_API_KEY, with_decryption=True)

        if not self.apify_token or not self.claude_key:
            raise IngestionError("Missing required API credentials in Parameter Store")

        self.apify_client = apify_actor_client.ApifyClientWrapper(self.apify_token)
        self.claude_client = claude_caption_generator.ClaudeClient(self.claude_key)
        self.storage = dynamodb_storage.DynamoDBStorage()
        self.cloudwatch = boto3.client("cloudwatch", region_name=config.AWS_REGION)

        # Metrics for this run
        self.metrics = {
            "items_scraped": 0,
            "items_deduplicated": 0,
            "items_processed": 0,
            "items_failed": 0,
            "errors": [],
        }

    def process_source(self, source_name: str, source_config: Dict[str, Any]) -> None:
        """
        Process a single social media source.

        Args:
            source_name: Source name (tiktok, instagram, facebook)
            source_config: Source configuration (actor_id, options, etc.)
        """
        logger.info(f"Processing source: {source_name}")

        try:
            # Start Apify actor run
            actor_id = source_config["actor_id"]
            options = source_config["options"]

            run_id = self.apify_client.start_actor_run(actor_id, options)
            logger.info(f"Started Apify run: {run_id} for {source_name}")

            # Wait for the run to complete
            self.apify_client.wait_for_run_to_finish(run_id, timeout_secs=300)
            logger.info(f"Apify run {run_id} finished for {source_name}")

            # Retrieve results
            results = self.apify_client.retrieve_results(run_id, limit=20)
            self.metrics["items_scraped"] += len(results)

            # Process each scraped item
            for scraped_item in results:
                self._process_scraped_item(scraped_item, source_name)

        except ApifyError as e:
            error_msg = f"Apify error for {source_name}: {str(e)}"
            logger.error(error_msg)
            self.metrics["errors"].append(error_msg)
            self.metrics["items_failed"] += 1
            # Use centralized error handler
            ingestion_error_handlers.handle_pipeline_error(
                error_type="APIFY_ERROR",
                error_message=error_msg,
                retry_count=0,
                item_data={"source_platform": source_name},
            )

    def _process_scraped_item(self, scraped_item: Dict[str, Any], source_platform: str) -> None:
        """
        Process a single scraped item through the pipeline.

        Args:
            scraped_item: Scraped content from Apify
            source_platform: Source platform (tiktok, instagram, facebook)
        """
        try:
            item_id = generate_item_id()
            source_url = scraped_item.get("url", "")
            original_caption = scraped_item.get("caption", "")

            logger.info(f"Processing item {item_id} from {source_platform}")

            # 1. Check for duplicates
            if not original_caption:
                logger.warning(f"Skipping item {item_id}: missing caption")
                self.metrics["items_failed"] += 1
                return

            # 4. Generate caption with Claude
            retry_count = 0
            caption_error = None
            try:
                caption_response = self.claude_client.generate_caption(
                    original_caption, source_platform, source_url, tone=CaptureTone.AESTHETIC.value
                )
                ai_caption_vi, hashtags = self.claude_client.parse_caption_response(
                    caption_response
                )
            except ClaudeError as e:
                retry_count = getattr(e, "retry_count", 0)
                caption_error = str(e)
                logger.error(f"Caption generation failed for {item_id}: {e}")
                self.metrics["items_failed"] += 1
                # Use centralized error handler
                ingestion_error_handlers.handle_pipeline_error(
                    error_type="CLAUDE_ERROR",
                    error_message=caption_error,
                    retry_count=retry_count,
                    item_data={
                        "item_id": item_id,
                        "source_platform": source_platform,
                        "source_url": source_url,
                        "original_caption": original_caption,
                    },
                )
                return

            # 5. Store in DynamoDB
            content_item = ContentItem(
                item_id=item_id,
                source_platform=source_platform,
                source_url=source_url,
                original_caption=original_caption,
                ai_caption_vi=ai_caption_vi,
                ai_caption_tone=CaptureTone.AESTHETIC.value,
                status=ContentStatus.RAW,
                created_at=get_iso8601_timestamp(),
                metadata={
                    "short_code": scraped_item.get("shortCode", {}),
                    "source_author": scraped_item.get("ownerUsername", ""),
                    "hashtags_added": hashtags,
                },
            )

            self.storage.save_content_item(content_item)
            self.metrics["items_processed"] += 1
            logger.info(f"Successfully processed item {item_id}")

        except Exception as e:
            logger.error(f"Error processing item from {source_platform}: {e}", exc_info=True)
            self.metrics["items_failed"] += 1
            # Use centralized error handler for unexpected errors
            ingestion_error_handlers.handle_pipeline_error(
                error_type="PROCESSING_ERROR",
                error_message=str(e),
                retry_count=0,
                item_data={
                    "item_id": item_id,
                    "source_platform": source_platform,
                    "source_url": source_url,
                    "original_caption": original_caption,
                },
            )

    def _emit_metrics_to_cloudwatch(self) -> None:
        """
        Emit custom CloudWatch metrics for this pipeline execution.
        """
        try:
            metric_data = [
                {
                    "MetricName": "processed_items",
                    "Value": self.metrics["items_processed"],
                    "Unit": "Count",
                    "Timestamp": datetime.now(timezone.utc),
                },
                {
                    "MetricName": "items_scraped",
                    "Value": self.metrics["items_scraped"],
                    "Unit": "Count",
                    "Timestamp": datetime.now(timezone.utc),
                },
                {
                    "MetricName": "duplicate_skipped",
                    "Value": self.metrics["items_deduplicated"],
                    "Unit": "Count",
                    "Timestamp": datetime.now(timezone.utc),
                },
                {
                    "MetricName": "errors_total",
                    "Value": self.metrics["items_failed"],
                    "Unit": "Count",
                    "Timestamp": datetime.now(timezone.utc),
                },
            ]

            self.cloudwatch.put_metric_data(
                Namespace=config.CLOUDWATCH_METRICS_NAMESPACE, MetricData=metric_data
            )

            logger.info(f"CloudWatch metrics emitted: {self.metrics}")

        except Exception as e:
            logger.error(f"Failed to emit CloudWatch metrics: {e}", exc_info=True)

    def run(self) -> Dict[str, Any]:
        """
        Execute the complete ingestion pipeline.

        Returns:
            Metrics and status of the run
        """
        import time

        run_start = time.time()
        timestamp = get_iso8601_timestamp()

        _log_structured(
            "INFO",
            "Starting Phase 2 content ingestion pipeline",
            request_id=id(self),
            start_timestamp=timestamp,
        )

        try:
            # Process each configured source
            for source_name, source_config in config.SOURCES_CONFIG.items():
                self.process_source(source_name, source_config)

            # Calculate execution time
            execution_time_ms = int((time.time() - run_start) * 1000)

            # Log final metrics in structured format
            _log_structured(
                "INFO",
                "Pipeline execution completed",
                request_id=id(self),
                items_scraped=self.metrics["items_scraped"],
                items_deduplicated=self.metrics["items_deduplicated"],
                items_processed=self.metrics["items_processed"],
                items_failed=self.metrics["items_failed"],
                execution_time_ms=execution_time_ms,
            )

            # Emit metrics to CloudWatch
            self._emit_metrics_to_cloudwatch()

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": "Ingestion pipeline completed",
                        "run_start": timestamp,
                        "run_end": get_iso8601_timestamp(),
                        "execution_time_ms": execution_time_ms,
                        "metrics": self.metrics,
                    }
                ),
            }

        except Exception as e:
            execution_time_ms = int((time.time() - run_start) * 1000)

            _log_structured(
                "ERROR",
                "Pipeline execution failed",
                request_id=id(self),
                error_message=str(e),
                error_type=type(e).__name__,
                execution_time_ms=execution_time_ms,
                traceback=traceback.format_exc(),
            )

            ingestion_error_handlers.handle_pipeline_error(
                error_type="PIPELINE_FAILURE", error_message=str(e), retry_count=0
            )

            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": "Pipeline failed",
                        "message": str(e),
                        "execution_time_ms": execution_time_ms,
                        "metrics": self.metrics,
                    }
                ),
            }


def lambda_handler(event, context=None):
    """
    AWS Lambda handler for content ingestion pipeline.

    Args:
        event: Lambda event (from EventBridge)
        context: Lambda context (unused)

    Returns:
        Response with status and metrics
    """
    logger.info(f"Pipeline invoked with event: {json.dumps(event)}")

    try:
        pipeline = IngestionPipeline()
        result = pipeline.run()
        logger.info(f"Pipeline response: {result}")
        return result

    except IngestionError as e:
        logger.error(f"Ingestion error: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Ingestion pipeline error", "message": str(e)}),
        }

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Unexpected error", "message": str(e)}),
        }
