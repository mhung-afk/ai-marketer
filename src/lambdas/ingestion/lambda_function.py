"""
Phase 2 Content Ingestion Pipeline Lambda

Orchestrates scraping, caption generation, and storage of content from social media.
Triggered by EventBridge Scheduler on configurable cron schedule.
"""

import json
import logging
from typing import Dict, Any
from datetime import datetime, timezone

import sys
import os
import json
import logging
import boto3

# Handle both direct execution and module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from common import config
from common.utils import (
    generate_item_id,
    get_iso8601_timestamp,
    get_parameter,
    send_ingestion_alert
)
from common.schemas import ContentItem, ContentStatus, CaptureTone
from common.error_handlers import IngestionError, ApifyError, ClaudeError

# Import local modules (from same directory)
if __name__ != "__main__":
    # When imported as a module
    from . import apify_client
    from . import claude_caption_generator
    from . import image_processor
    from . import deduplication
    from . import dynamodb_storage
else:
    # When run directly
    import apify_client
    import claude_caption_generator
    import image_processor
    import deduplication
    import dynamodb_storage

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class IngestionPipeline:
    """Orchestrates the entire content ingestion pipeline."""

    def __init__(self):
        """Initialize pipeline with AWS clients and API keys."""
        self.apify_token = get_parameter(config.PARAM_APIFY_API_TOKEN, with_decryption=True)
        self.claude_key = get_parameter(config.PARAM_ANTHROPIC_API_KEY, with_decryption=True)

        if not self.apify_token or not self.claude_key:
            raise IngestionError("Missing required API credentials in Parameter Store")

        self.apify_client = apify_client.ApifyClient(self.apify_token)
        self.claude_client = claude_caption_generator.ClaudeClient(self.claude_key)
        self.image_processor = image_processor.ImageProcessor()
        self.storage = dynamodb_storage.DynamoDBStorage()
        self.sqs = boto3.client("sqs", region_name=config.AWS_REGION)

        # Metrics for this run
        self.metrics = {
            "items_scraped": 0,
            "items_deduplicated": 0,
            "items_processed": 0,
            "items_failed": 0,
            "errors": []
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
            send_ingestion_alert("APIFY_ERROR", error_msg, context_data={"source": source_name})

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
            original_caption = scraped_item.get("caption", scraped_item.get("text", ""))
            image_url = scraped_item.get("image", "")

            logger.info(f"Processing item {item_id} from {source_platform}")

            # 1. Check for duplicates
            if not original_caption or not image_url:
                logger.warning(f"Skipping item {item_id}: missing caption or image")
                self.metrics["items_failed"] += 1
                return

            # 2. Download and hash image
            image_bytes, extension = self.image_processor.download_image(image_url)
            content_hash = self.image_processor.compute_content_hash(image_bytes)

            # Check hash-based duplicate
            is_dup_hash, existing_id = deduplication.check_duplicate_by_hash(content_hash)
            if is_dup_hash:
                logger.info(f"Duplicate by hash detected: {item_id} matches {existing_id}")
                self.metrics["items_deduplicated"] += 1
                return

            # 3. Upload image to S3
            cloudfront_url = self.image_processor.upload_to_s3(image_bytes, extension)

            # 4. Generate caption with Claude
            try:
                caption_response = self.claude_client.generate_caption(
                    original_caption,
                    source_platform,
                    tone=CaptureTone.AESTHETIC.value
                )
                ai_caption_vi, hashtags = self.claude_client.parse_caption_response(caption_response)
            except ClaudeError as e:
                logger.error(f"Caption generation failed for {item_id}: {e}")
                self.metrics["items_failed"] += 1
                send_ingestion_alert("CLAUDE_ERROR", str(e), context_data={"item_id": item_id})
                return

            # 5. Store in DynamoDB
            content_item = ContentItem(
                item_id=item_id,
                source_platform=source_platform,
                source_url=source_url,
                original_caption=original_caption,
                ai_caption_vi=ai_caption_vi,
                ai_caption_tone=CaptureTone.AESTHETIC.value,
                s3_image_key=cloudfront_url.split("/", 3)[-1],  # Extract path from URL
                cloudfront_url=cloudfront_url,
                content_hash=content_hash,
                status=ContentStatus.RAW,
                created_at=get_iso8601_timestamp(),
                metadata={
                    "source_engagement": scraped_item.get("engagement", {}),
                    "source_author": scraped_item.get("author", ""),
                    "hashtags_added": hashtags
                }
            )

            self.storage.save_content_item(content_item)
            self.metrics["items_processed"] += 1
            logger.info(f"Successfully processed item {item_id}")

        except Exception as e:
            logger.error(f"Error processing item from {source_platform}: {e}", exc_info=True)
            self.metrics["items_failed"] += 1
            send_ingestion_alert(
                "PROCESSING_ERROR",
                str(e),
                context_data={"source": source_platform}
            )

    def run(self) -> Dict[str, Any]:
        """
        Execute the complete ingestion pipeline.

        Returns:
            Metrics and status of the run
        """
        logger.info("Starting Phase 2 content ingestion pipeline")
        run_start = get_iso8601_timestamp()

        try:
            # Process each configured source
            for source_name, source_config in config.SOURCES_CONFIG.items():
                self.process_source(source_name, source_config)

            # Log final metrics
            logger.info(
                f"Pipeline complete. Scraped: {self.metrics['items_scraped']}, "
                f"Deduplicated: {self.metrics['items_deduplicated']}, "
                f"Processed: {self.metrics['items_processed']}, "
                f"Failed: {self.metrics['items_failed']}"
            )

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Ingestion pipeline completed",
                    "run_start": run_start,
                    "run_end": get_iso8601_timestamp(),
                    "metrics": self.metrics
                })
            }

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            send_ingestion_alert("PIPELINE_FAILURE", str(e))

            return {
                "statusCode": 500,
                "body": json.dumps({
                    "error": "Pipeline failed",
                    "message": str(e),
                    "metrics": self.metrics
                })
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
            "body": json.dumps({
                "error": "Ingestion pipeline error",
                "message": str(e)
            })
        }

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Unexpected error",
                "message": str(e)
            })
        }
