"""
Apify Actor Client for Social Media Scraping

Uses the official apify-client SDK.
"""

import logging
from typing import Dict, List, Any, Optional

from apify_client import ApifyClient

from common.error_handlers import ApifyError

logger = logging.getLogger(__name__)


class ApifyClientWrapper:
    """Client for interacting with Apify Actors using the official SDK."""

    def __init__(self, api_token: str):
        """
        Initialize Apify client.
        """
        self.client: ApifyClient = ApifyClient(token=api_token)
        logger.info("ApifyClientWrapper initialized successfully")

    def start_actor_run(self, actor_id: str, input_params: Dict[str, Any]) -> str:
        """
        Start an Apify actor run asynchronously.
        """
        try:
            run = self.client.actor(actor_id).start(run_input=input_params)

            run_id = run.get("id") if isinstance(run, dict) else getattr(run, "id", None)
            if not run_id:
                raise ApifyError("No run ID returned from Apify")

            logger.info(f"Started Apify run: {run_id} | Actor: {actor_id}")
            return str(run_id)

        except Exception as e:
            raise ApifyError(f"Failed to start actor run for {actor_id}: {str(e)}") from e

    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """Get current status of a run."""
        try:
            run = self.client.run(run_id).get()
            return dict(run) if run else {}
        except Exception as e:
            raise ApifyError(f"Failed to get status for run {run_id}: {str(e)}") from e

    def wait_for_run_to_finish(self, run_id: str, timeout_secs: Optional[int] = 600) -> Dict[str, Any]:
        """
        Wait for the run to finish and return final run data.
        """
        try:
            run_client = self.client.run(run_id)
            final_run = run_client.wait_for_finish(wait_secs=timeout_secs)

            status = final_run.get("status") if isinstance(final_run, dict) else getattr(final_run, "status", None)
            logger.info(f"Run {run_id} completed with status: {status}")
            return dict(final_run) if isinstance(final_run, dict) else {}

        except Exception as e:
            raise ApifyError(f"Failed while waiting for run {run_id}: {str(e)}") from e

    def retrieve_results(self, run_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Retrieve results from the run's default dataset.
        """
        try:
            # Get the run to find defaultDatasetId
            run_data = self.get_run_status(run_id)  # reuse existing method
            dataset_id = run_data.get("defaultDatasetId")

            if not dataset_id:
                logger.warning(f"No defaultDatasetId found for run {run_id}")
                return []

            # Fetch items from the dataset
            dataset_client = self.client.dataset(dataset_id)
            items_result = dataset_client.list_items(limit=limit)
            items = items_result.items if hasattr(items_result, "items") else []

            logger.info(f"Retrieved {len(items)} items from run {run_id}")
            return items if not hasattr(items_result, "error") else []

        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str or "404" in error_str:
                logger.warning(f"Dataset not found for run {run_id} (run may still be running)")
                return []

            raise ApifyError(f"Failed to retrieve results for run {run_id}: {str(e)}") from e