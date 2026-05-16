"""
Unit Tests for Error Handling & Alerts (Phase 6 - US4)

Tests for error handler, DLQ submission, and SNS alert publishing.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone

# Mock AWS clients before importing modules
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.lambdas.ingestion import error_handlers
from src.common import config


class TestErrorHandling:
    """Tests for handle_pipeline_error function."""

    @patch("src.lambdas.ingestion.error_handlers.sns")
    @patch("src.lambdas.ingestion.error_handlers.sqs")
    def test_handle_pipeline_error_publishes_sns_alert(self, mock_sqs, mock_sns):
        """Test that pipeline errors publish SNS alerts."""
        error_handlers.handle_pipeline_error(
            error_type="APIFY_ERROR",
            error_message="Apify actor failed: invalid API token",
            retry_count=0,
            item_data={
                "item_id": "test-item-001",
                "source_platform": "tiktok",
                "source_url": "https://www.tiktok.com/@user/video/123",
                "original_caption": "test caption"
            }
        )

        # Verify SNS publish was called
        mock_sns.publish.assert_called_once()
        call_kwargs = mock_sns.publish.call_args[1]
        assert "APIFY_ERROR" in call_kwargs["Subject"]
        assert "Apify actor failed" in call_kwargs["Message"]

    @patch("src.lambdas.ingestion.error_handlers.sns")
    @patch("src.lambdas.ingestion.error_handlers.sqs")
    def test_handle_pipeline_error_sends_to_dlq_on_max_retries(self, mock_sqs, mock_sns):
        """Test that errors are sent to DLQ after max retries."""
        item_data = {
            "item_id": "test-item-001",
            "source_platform": "tiktok",
            "source_url": "https://www.tiktok.com/@user/video/123",
            "original_caption": "test caption",
            "created_at": "2026-05-09T10:00:00Z"
        }

        # Trigger error with max retries
        error_handlers.handle_pipeline_error(
            error_type="CLAUDE_TIMEOUT",
            error_message="Claude API timeout after 30 seconds",
            retry_count=config.MAX_RETRY_ATTEMPTS,
            item_data=item_data
        )

        # Verify SQS send_message was called (DLQ submission)
        mock_sqs.send_message.assert_called_once()
        call_kwargs = mock_sqs.send_message.call_args[1]

        # Verify DLQ message structure
        dlq_message = json.loads(call_kwargs["MessageBody"])
        assert dlq_message["item_id"] == "test-item-001"
        assert dlq_message["error_code"] == "CLAUDE_TIMEOUT"
        assert dlq_message["retry_count"] == config.MAX_RETRY_ATTEMPTS
        assert "moved_to_dlq_at" in dlq_message

    @patch("src.lambdas.ingestion.error_handlers.sns")
    def test_handle_pipeline_error_does_not_send_to_dlq_if_retries_remain(self, mock_sns):
        """Test that errors are NOT sent to DLQ if retries remain."""
        with patch("src.lambdas.ingestion.error_handlers.sqs") as mock_sqs:
            error_handlers.handle_pipeline_error(
                error_type="APIFY_ERROR",
                error_message="Temporary network error",
                retry_count=1,  # Less than MAX_RETRY_ATTEMPTS
                item_data={"item_id": "test-001", "source_platform": "tiktok"}
            )

            # Verify SQS was NOT called (should retry first)
            mock_sqs.send_message.assert_not_called()

    @patch("src.lambdas.ingestion.error_handlers.sns")
    def test_handle_pipeline_error_remediation_hints(self, mock_sns):
        """Test that remediation hints are included in logs."""
        with patch("src.lambdas.ingestion.error_handlers.logger") as mock_logger:
            error_handlers.handle_pipeline_error(
                error_type="APIFY_AUTH_ERROR",
                error_message="Invalid API token",
                retry_count=0
            )

            # Verify error was logged with remediation hint
            mock_logger.error.assert_called_once()
            log_call = mock_logger.error.call_args[0][0]
            log_data = json.loads(log_call)

            assert "recovery_hint" in log_data
            assert "Parameter Store" in log_data["recovery_hint"]


class TestSNSAlertPublishing:
    """Tests for SNS alert publishing."""

    @patch("src.lambdas.ingestion.error_handlers.sns")
    def test_publish_error_alert_formats_message_correctly(self, mock_sns):
        """Test that error alerts are formatted correctly for Telegram."""
        error_handlers._publish_error_alert(
            error_type="CLAUDE_RATE_LIMIT",
            error_message="Rate limit exceeded: 100 requests/min",
            retry_count=2,
            item_data={
                "item_id": "test-001",
                "source_platform": "instagram"
            }
        )

        mock_sns.publish.assert_called_once()
        call_kwargs = mock_sns.publish.call_args[1]

        # Verify message contains key information
        message = call_kwargs["Message"]
        assert "CLAUDE_RATE_LIMIT" in message
        assert "Rate limit exceeded" in message
        assert "instagram" in message
        assert "Recovery Hint" in message

    @patch("src.lambdas.ingestion.error_handlers.sns")
    def test_publish_error_alert_without_item_data(self, mock_sns):
        """Test error alert publishing without item data."""
        error_handlers._publish_error_alert(
            error_type="PIPELINE_FAILURE",
            error_message="Unexpected exception",
            retry_count=0
        )

        mock_sns.publish.assert_called_once()
        call_kwargs = mock_sns.publish.call_args[1]
        message = call_kwargs["Message"]

        assert "PIPELINE_FAILURE" in message
        assert "Unexpected exception" in message


class TestDLQSubmission:
    """Tests for dead-letter queue submission."""

    @patch("src.lambdas.ingestion.error_handlers.sqs")
    def test_send_to_dlq_includes_all_metadata(self, mock_sqs):
        """Test that DLQ messages include complete metadata."""
        item_data = {
            "item_id": "test-001",
            "source_platform": "facebook",
            "source_url": "https://www.facebook.com/post/123",
            "original_caption": "Original caption text",
            "created_at": "2026-05-09T10:00:00Z",
            "s3_upload_status": "succeeded"
        }

        apify_metadata = {
            "run_id": "apify-run-xyz123",
            "status": "succeeded"
        }

        error_handlers._send_to_dlq(
            error_type="IMAGE_PROCESSING_ERROR",
            error_message="Image validation failed",
            retry_count=3,
            item_data=item_data,
            apify_metadata=apify_metadata
        )

        mock_sqs.send_message.assert_called_once()
        call_kwargs = mock_sqs.send_message.call_args[1]
        dlq_message = json.loads(call_kwargs["MessageBody"])

        # Verify DLQ message structure
        assert dlq_message["item_id"] == "test-001"
        assert dlq_message["source_platform"] == "facebook"
        assert dlq_message["error_code"] == "IMAGE_PROCESSING_ERROR"
        assert dlq_message["retry_count"] == 3
        assert dlq_message["metadata"]["apify_run_id"] == "apify-run-xyz123"
        assert dlq_message["metadata"]["s3_upload_status"] == "succeeded"
        assert "moved_to_dlq_at" in dlq_message


class TestRemediationHints:
    """Tests for remediation hint generation."""

    def test_remediation_hint_for_apify_error(self):
        """Test that APIFY_ERROR returns proper remediation hint."""
        hint = error_handlers._get_remediation_hint("APIFY_ERROR")
        assert hint is not None
        assert "Parameter Store" in hint
        assert "actor ID" in hint.lower()

    def test_remediation_hint_for_claude_timeout(self):
        """Test that CLAUDE_TIMEOUT returns proper remediation hint."""
        hint = error_handlers._get_remediation_hint("CLAUDE_TIMEOUT")
        assert hint is not None
        assert "timeout" in hint.lower()
        assert "network" in hint.lower()

    def test_remediation_hint_for_s3_upload_error(self):
        """Test that S3_UPLOAD_ERROR returns proper remediation hint."""
        hint = error_handlers._get_remediation_hint("S3_UPLOAD_ERROR")
        assert hint is not None
        assert "S3" in hint
        assert "PutObject" in hint

    def test_remediation_hint_for_unknown_error(self):
        """Test that unknown error type returns None."""
        hint = error_handlers._get_remediation_hint("UNKNOWN_ERROR_TYPE")
        assert hint is None


class TestErrorContextLogging:
    """Tests for error context logging."""

    @patch("src.lambdas.ingestion.error_handlers.logger")
    def test_error_logging_includes_full_context(self, mock_logger):
        """Test that error logging captures full context."""
        item_data = {
            "item_id": "test-001",
            "source_platform": "tiktok",
            "source_url": "https://tiktok.com/@user/video/123",
            "original_caption": "test caption"
        }

        error_handlers.handle_pipeline_error(
            error_type="DYNAMODB_ERROR",
            error_message="Unable to connect to DynamoDB",
            retry_count=1,
            item_data=item_data
        )

        mock_logger.error.assert_called_once()
        log_call = mock_logger.error.call_args[0][0]
        log_data = json.loads(log_call)

        # Verify context is logged
        assert log_data["error_type"] == "DYNAMODB_ERROR"
        assert log_data["item_context"]["item_id"] == "test-001"
        assert log_data["item_context"]["source_platform"] == "tiktok"
        assert "suggested_actions" in log_data
        assert len(log_data["suggested_actions"]) > 0
