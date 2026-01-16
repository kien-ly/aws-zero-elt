"""HTTP client for JSONPlaceholder API.

This module provides a wrapper around requests library for fetching
dummy data from JSONPlaceholder REST API.
"""

import logging
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# Default timeout for HTTP requests (connect, read)
DEFAULT_TIMEOUT = (5, 30)

# Retry configuration
RETRY_TOTAL = 3
RETRY_BACKOFF_FACTOR = 0.5
RETRY_STATUS_FORCELIST = [429, 500, 502, 503, 504]


class APIClientError(Exception):
    """Exception raised for API client errors."""

    pass


class APIClient:
    """HTTP client for JSONPlaceholder API.

    Provides methods to fetch users, posts, and comments from the API
    with automatic retry and error handling.

    Attributes:
        base_url: Base URL for the API.
    """

    def __init__(self, base_url: str) -> None:
        """Initialize API client.

        Args:
            base_url: Base URL for JSONPlaceholder API.
        """
        self.base_url = base_url.rstrip("/")
        self._session = self._create_session()
        logger.info("APIClient initialized with base_url=%s", self.base_url)

    def _create_session(self) -> requests.Session:
        """Create requests session with retry configuration.

        Returns:
            Configured requests Session.
        """
        session = requests.Session()

        retry_strategy = Retry(
            total=RETRY_TOTAL,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            status_forcelist=RETRY_STATUS_FORCELIST,
            allowed_methods=["GET"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        return session

    def _get(self, endpoint: str) -> list[dict[str, Any]]:
        """Execute GET request to API endpoint.

        Args:
            endpoint: API endpoint path (e.g., "/users").

        Returns:
            JSON response as list of dictionaries.

        Raises:
            APIClientError: If request fails.
        """
        url = f"{self.base_url}{endpoint}"
        logger.info("Fetching data from %s", url)

        try:
            response = self._session.get(url, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            logger.info("Fetched %d records from %s", len(data), endpoint)
            return data
        except requests.exceptions.Timeout as e:
            logger.error("Request timeout for %s: %s", url, e)
            raise APIClientError(f"Request timeout: {e}") from e
        except requests.exceptions.HTTPError as e:
            logger.error("HTTP error for %s: %s", url, e)
            raise APIClientError(f"HTTP error: {e}") from e
        except requests.exceptions.RequestException as e:
            logger.error("Request failed for %s: %s", url, e)
            raise APIClientError(f"Request failed: {e}") from e
        except ValueError as e:
            logger.error("Invalid JSON response from %s: %s", url, e)
            raise APIClientError(f"Invalid JSON response: {e}") from e

    def fetch_users(self) -> list[dict[str, Any]]:
        """Fetch all users from /users endpoint.

        Returns:
            List of user dictionaries.

        Raises:
            APIClientError: If request fails.
        """
        return self._get("/users")

    def fetch_posts(self) -> list[dict[str, Any]]:
        """Fetch all posts from /posts endpoint.

        Returns:
            List of post dictionaries.

        Raises:
            APIClientError: If request fails.
        """
        return self._get("/posts")

    def fetch_comments(self) -> list[dict[str, Any]]:
        """Fetch all comments from /comments endpoint.

        Returns:
            List of comment dictionaries.

        Raises:
            APIClientError: If request fails.
        """
        return self._get("/comments")

    def close(self) -> None:
        """Close the HTTP session."""
        self._session.close()
        logger.debug("APIClient session closed")
