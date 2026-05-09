"""
Apify Actor Client for Social Media Scraping

This module handles orchestration of Apify Actors to scrape content
from TikTok, Instagram, and Facebook.
"""

import requests
import logging
from typing import Dict, List, Any, Optional
from common.error_handlers import ApifyError
from common import config

logger = logging.getLogger(__name__)


class ApifyClient:
    """Client for interacting with Apify Actors."""

    BASE_URL = "https://api.apify.com/v2"

    def __init__(self, api_token: str):
        """
        Initialize Apify client.

        Args:
            api_token: Apify API token for authentication
        """
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }

    def start_actor_run(
        self,
        actor_id: str,
        input_params: Dict[str, Any]
    ) -> str:
        """
        Start an Apify actor run.

        Args:
            actor_id: Apify actor ID (e.g., sKvq8dqWIB7QvZyPf for TikTok scraper)
            input_params: Input configuration for the actor

        Returns:
            Run ID for tracking the execution

        Raises:
            ApifyError: If API call fails
        """
        url = f"{self.BASE_URL}/acts/{actor_id}/runs"

        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=input_params,
                timeout=30
            )

            if response.status_code == 403:
                raise ApifyError(f"Authentication failed: {response.text}")
            if response.status_code == 429:
                raise ApifyError(f"Rate limit exceeded: {response.text}")
            if response.status_code == 503:
                raise ApifyError(f"Apify service unavailable: {response.text}")

            response.raise_for_status()

            data = response.json()
            run_id = data.get("data", {}).get("id")

            if not run_id:
                raise ApifyError(f"No run ID in response: {data}")

            logger.info(f"Started Apify run: {run_id}")
            return run_id

        except requests.RequestException as e:
            raise ApifyError(f"Failed to start actor run: {e}")

    def get_run_status(self, run_id: str) -> Dict[str, Any]:
        """
        Get the status of an Apify actor run.

        Args:
            run_id: Apify run ID

        Returns:
            Run status data

        Raises:
            ApifyError: If API call fails
        """
        url = f"{self.BASE_URL}/actor-runs/{run_id}"

        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()

            data = response.json()
            return data.get("data", {})

        except requests.RequestException as e:
            raise ApifyError(f"Failed to get run status: {e}")

    def retrieve_results(
        self,
        run_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve results from a completed Apify actor run.

        Args:
            run_id: Apify run ID
            limit: Maximum number of results to retrieve

        Returns:
            List of scraped content items

        Raises:
            ApifyError: If API call fails
        """
        url = f"{self.BASE_URL}/actor-runs/{run_id}/dataset/items"

        try:
            params = {
                "limit": limit,
                "format": "json"
            }

            response = requests.get(
                url,
                headers=self.headers,
                params=params,
                timeout=30
            )

            if response.status_code == 404:
                logger.warning(f"No dataset found for run {run_id}")
                return []

            response.raise_for_status()

            data = response.json()
            items = data if isinstance(data, list) else []

            logger.info(f"Retrieved {len(items)} items from run {run_id}")
            return items

        except requests.RequestException as e:
            raise ApifyError(f"Failed to retrieve results: {e}")
