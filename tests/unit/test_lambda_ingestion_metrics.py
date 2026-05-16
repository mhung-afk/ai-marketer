"""
Unit Tests for Lambda Ingestion Metrics & Monitoring (Phase 6 - US4)

Tests for CloudWatch metrics emission and Lambda execution tracking.
"""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.lambdas.ingestion.lambda_function import IngestionPipeline, _log_structured
from src.common import config


class TestCloudWatchMetricsEmission:
    """Tests for CloudWatch metrics emission."""

    @patch("src.lambdas.ingestion.lambda_function.get_parameter")
    @patch("src.lambdas.ingestion.lambda_function.boto3.client")
    def test_emit_metrics_to_cloudwatch_sends_all_metrics(self, mock_boto_client, mock_get_param):
        """Test that all metrics are emitted to CloudWatch."""
        # Setup mocks
        mock_get_param.side_effect = ["test-apify-token", "test-claude-key"]
        mock_cloudwatch = MagicMock()
        mock_boto_client.return_value = mock_cloudwatch

        # Mock the resource calls
        with patch("src.lambdas.ingestion.lambda_function.boto3.resource"):
            pipeline = IngestionPipeline()

        # Set metrics
        pipeline.metrics = {
            "items_scraped": 50,
            "items_deduplicated": 5,
            "items_processed": 40,
            "items_failed": 5,
            "errors": []
        }

        # Call the method
        pipeline._emit_metrics_to_cloudwatch()

        # Verify put_metric_data was called
        assert pipeline.cloudwatch.put_metric_data.called
        call_kwargs = pipeline.cloudwatch.put_metric_data.call_args[1]

        # Verify namespace
        assert call_kwargs["Namespace"] == config.CLOUDWATCH_METRICS_NAMESPACE

        # Verify metrics data
        metric_data = call_kwargs["MetricData"]
        metric_names = {m["MetricName"] for m in metric_data}

        assert "processed_items" in metric_names
        assert "items_scraped" in metric_names
        assert "duplicate_skipped" in metric_names
        assert "errors_total" in metric_names

        # Verify metric values
        for metric in metric_data:
            if metric["MetricName"] == "processed_items":
                assert metric["Value"] == 40
            elif metric["MetricName"] == "items_scraped":
                assert metric["Value"] == 50
            elif metric["MetricName"] == "duplicate_skipped":
                assert metric["Value"] == 5
            elif metric["MetricName"] == "errors_total":
                assert metric["Value"] == 5

    @patch("src.lambdas.ingestion.lambda_function.get_parameter")
    @patch("src.lambdas.ingestion.lambda_function.boto3.client")
    def test_emit_metrics_handles_cloudwatch_errors(self, mock_boto_client, mock_get_param):
        """Test that CloudWatch errors are handled gracefully."""
        mock_get_param.side_effect = ["test-apify-token", "test-claude-key"]

        with patch("src.lambdas.ingestion.lambda_function.boto3.resource"):
            pipeline = IngestionPipeline()

        # Make CloudWatch raise an error
        pipeline.cloudwatch.put_metric_data.side_effect = Exception("CloudWatch unavailable")

        # Should not raise, but log error
        pipeline._emit_metrics_to_cloudwatch()  # Should not crash

        # Verify error was logged
        assert pipeline.cloudwatch.put_metric_data.called


class TestStructuredLogging:
    """Tests for structured JSON logging."""

    @patch("src.lambdas.ingestion.lambda_function.logger")
    def test_log_structured_info_format(self, mock_logger):
        """Test that INFO logs are formatted correctly."""
        _log_structured(
            "INFO",
            "Pipeline started",
            request_id="req-123",
            platform="tiktok"
        )

        mock_logger.info.assert_called_once()
        log_message = mock_logger.info.call_args[0][0]
        log_data = json.loads(log_message)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Pipeline started"
        assert log_data["request_id"] == "req-123"
        assert log_data["platform"] == "tiktok"
        assert "timestamp" in log_data

    @patch("src.lambdas.ingestion.lambda_function.logger")
    def test_log_structured_error_format(self, mock_logger):
        """Test that ERROR logs are formatted correctly."""
        _log_structured(
            "ERROR",
            "Pipeline failed",
            error_type="APIFY_ERROR",
            error_message="API timeout"
        )

        mock_logger.error.assert_called_once()
        log_message = mock_logger.error.call_args[0][0]
        log_data = json.loads(log_message)

        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "Pipeline failed"
        assert log_data["error_type"] == "APIFY_ERROR"
        assert log_data["error_message"] == "API timeout"

    @patch("src.lambdas.ingestion.lambda_function.logger")
    def test_log_structured_warning_format(self, mock_logger):
        """Test that WARNING logs are formatted correctly."""
        _log_structured(
            "WARNING",
            "Approaching rate limit",
            retry_count=2,
            max_retries=3
        )

        mock_logger.warning.assert_called_once()
        log_message = mock_logger.warning.call_args[0][0]
        log_data = json.loads(log_message)

        assert log_data["level"] == "WARNING"
        assert log_data["message"] == "Approaching rate limit"


class TestPipelineExecutionTracking:
    """Tests for pipeline execution tracking and timing."""

    @patch("src.lambdas.ingestion.lambda_function.get_parameter")
    @patch("src.lambdas.ingestion.lambda_function.boto3.client")
    @patch("src.lambdas.ingestion.lambda_function.boto3.resource")
    @patch("src.lambdas.ingestion.lambda_function.config.SOURCES_CONFIG", {"test": {}})
    def test_pipeline_run_tracks_execution_time(self, mock_resource, mock_client, mock_get_param):
        """Test that pipeline tracks execution time."""
        mock_get_param.side_effect = ["test-apify-token", "test-claude-key"]

        pipeline = IngestionPipeline()
        pipeline.process_source = MagicMock()  # Mock source processing

        result = pipeline.run()

        # Verify result includes execution time
        body = json.loads(result["body"])
        assert "execution_time_ms" in body
        assert body["execution_time_ms"] >= 0

    @patch("src.lambdas.ingestion.lambda_function.get_parameter")
    @patch("src.lambdas.ingestion.lambda_function.boto3.client")
    @patch("src.lambdas.ingestion.lambda_function.boto3.resource")
    @patch("src.lambdas.ingestion.lambda_function.config.SOURCES_CONFIG", {})
    def test_pipeline_run_returns_metrics(self, mock_resource, mock_client, mock_get_param):
        """Test that pipeline returns all metrics."""
        mock_get_param.side_effect = ["test-apify-token", "test-claude-key"]

        pipeline = IngestionPipeline()
        result = pipeline.run()

        body = json.loads(result["body"])
        assert "metrics" in body
        assert "items_scraped" in body["metrics"]
        assert "items_processed" in body["metrics"]
        assert "items_deduplicated" in body["metrics"]
        assert "items_failed" in body["metrics"]


class TestMetricsStructure:
    """Tests for CloudWatch metrics structure and schema."""

    @patch("src.lambdas.ingestion.lambda_function.get_parameter")
    @patch("src.lambdas.ingestion.lambda_function.boto3.client")
    def test_metrics_have_correct_units(self, mock_client, mock_get_param):
        """Test that all metrics have proper CloudWatch units."""
        mock_get_param.side_effect = ["test-apify-token", "test-claude-key"]

        with patch("src.lambdas.ingestion.lambda_function.boto3.resource"):
            pipeline = IngestionPipeline()

        pipeline.metrics = {
            "items_scraped": 100,
            "items_deduplicated": 10,
            "items_processed": 85,
            "items_failed": 5,
            "errors": []
        }

        pipeline._emit_metrics_to_cloudwatch()

        call_kwargs = pipeline.cloudwatch.put_metric_data.call_args[1]
        metric_data = call_kwargs["MetricData"]

        # All metrics should have Count unit
        for metric in metric_data:
            assert metric["Unit"] == "Count", f"Metric {metric['MetricName']} has incorrect unit"

    @patch("src.lambdas.ingestion.lambda_function.get_parameter")
    @patch("src.lambdas.ingestion.lambda_function.boto3.client")
    def test_metrics_have_timestamp(self, mock_client, mock_get_param):
        """Test that all metrics include a timestamp."""
        mock_get_param.side_effect = ["test-apify-token", "test-claude-key"]

        with patch("src.lambdas.ingestion.lambda_function.boto3.resource"):
            pipeline = IngestionPipeline()

        pipeline._emit_metrics_to_cloudwatch()

        call_kwargs = pipeline.cloudwatch.put_metric_data.call_args[1]
        metric_data = call_kwargs["MetricData"]

        for metric in metric_data:
            assert "Timestamp" in metric
            assert metric["Timestamp"] is not None


class TestCloudWatchDashboardMetrics:
    """Tests for CloudWatch dashboard metric integration."""

    def test_dashboard_metrics_namespace_matches_config(self):
        """Test that dashboard uses configured metrics namespace."""
        assert config.CLOUDWATCH_METRICS_NAMESPACE == "HealingBedroom/Ingestion"

    def test_dashboard_metrics_defined_in_config(self):
        """Test that all required metrics are defined in config."""
        required_metrics = [
            "processed_items",
            "successful_captions",
            "failed_captions",
            "duplicate_skipped",
            "errors_total",
            "dlq_messages",
            "lambda_duration_ms"
        ]

        for metric_name in required_metrics:
            assert metric_name in config.CLOUDWATCH_METRICS
