"""
YouTube API Client - Handle YouTube Data API interactions

This module provides a clean interface for interacting with the YouTube Data API v3,
including search, video metadata retrieval, and quota management.
"""

import time
import random
from typing import List, Dict, Optional, Any, Callable
from datetime import datetime

import googleapiclient.discovery
from googleapiclient.errors import HttpError

from ..config import YouTubeAPIConfig
from ..models import VideoMetadata, VideoSource
from ..utils import get_output_manager


class YouTubeAPIError(Exception):
    """Base exception for YouTube API errors."""
    pass


class QuotaExceededError(YouTubeAPIError):
    """Exception raised when API quota is exceeded."""
    pass


class YouTubeAPIClient:
    """
    Client for YouTube Data API v3 operations.

    Handles authentication, quota management, rate limiting, and error recovery.
    """

    def __init__(self, config: YouTubeAPIConfig):
        """
        Initialize YouTube API client.

        Args:
            config: YouTube API configuration
        """
        self.config = config
        self.output = get_output_manager()

        self.api_keys = config.api_keys.copy()
        if not self.api_keys:
            raise YouTubeAPIError("No YouTube API keys provided")

        self.current_key_index = 0
        try:
            self.youtube_service = googleapiclient.discovery.build(
                "youtube", "v3",
                developerKey=self._current_key,
                cache_discovery=False
            )
            self.output.debug(f"Initialized YouTube API service with key {self.current_key_index + 1}")
        except Exception as e:
            raise YouTubeAPIError(f"Failed to initialize YouTube API service: {e}")

        # Quota and rate limiting
        self.quota_exceeded = False
        self.request_count = 0
        self.last_request_time = 0.0

        self.output.debug(f"Initialized YouTube API client with {len(self.api_keys)} keys")

    @property
    def _current_key(self) -> str:
        """Get current API key."""
        return self.api_keys[self.current_key_index]

    def _switch_to_next_key(self) -> bool:
        """
        Switch to the next available API key.

        Returns:
            True if successfully switched, False if no more keys
        """
        if self.current_key_index + 1 >= len(self.api_keys):
            return False

        old_key = self._current_key
        self.current_key_index += 1

        self.output.info(f"Switching to API key {self.current_key_index + 1}")
        self.output.debug(f"Previous key: ...{old_key[-4:]}")
        self.output.debug(f"Current key: ...{self._current_key[-4:]}")

        try:
            self.youtube_service = googleapiclient.discovery.build(
                "youtube", "v3",
                developerKey=self._current_key,
                cache_discovery=False
            )
            self.quota_exceeded = False
            return True
        except Exception as e:
            self.output.error(f"Failed to initialize with new API key: {e}")
            return False

    def _wait_for_quota_reset(self) -> None:
        """Wait for API quota to reset by polling all keys."""
        self.output.warning("All API keys quota exceeded - waiting for reset")

        poll_interval = self.config.poll_interval_seconds
        start_time = time.time()

        while True:
            self.output.info(f"Polling API keys every {poll_interval}s...")

            # Check all keys
            for i, key in enumerate(self.api_keys):
                if self._test_key_quota(key):
                    self.output.success(f"API key {i + 1} is available")
                    self.current_key_index = i
                    try:
                        self.youtube_service = googleapiclient.discovery.build(
                            "youtube", "v3",
                            developerKey=self._current_key,
                            cache_discovery=False
                        )
                        self.output.debug(f"Reinitialized YouTube API service with key {self.current_key_index + 1}")
                    except Exception as e:
                        self.output.error(f"Failed to reinitialize YouTube API service: {e}")
                        continue
                    self.quota_exceeded = False
                    return

            # Wait before next poll
            elapsed = int(time.time() - start_time)
            self.output.info(f"Elapsed: {elapsed // 60}m {elapsed % 60}s - still waiting...")
            time.sleep(poll_interval)

    def _test_key_quota(self, api_key: str) -> bool:
        """
        Test if an API key has available quota.

        Args:
            api_key: API key to test

        Returns:
            True if key has quota available
        """
        try:
            # Use a low-cost request to test quota
            test_service = googleapiclient.discovery.build(
                "youtube", "v3",
                developerKey=api_key,
                cache_discovery=False
            )

            # Simple video details request (very low quota cost)
            request = test_service.videos().list(
                part="id",
                id="dQw4w9WgXcQ"  # Rickroll video - should always exist
            )

            response = request.execute()
            return True

        except HttpError as e:
            if e.resp.status == 403:
                error_details = e.content.decode() if hasattr(e, 'content') else str(e)
                if "quotaExceeded" in error_details or "dailyLimitExceeded" in error_details:
                    return False
            return False
        except Exception:
            return False

    def _handle_api_error(self, error: HttpError, operation: str) -> None:
        """
        Handle YouTube API errors with appropriate recovery actions.

        Args:
            error: The HttpError that occurred
            operation: Description of the operation that failed

        Raises:
            QuotaExceededError: If quota is exceeded and no recovery possible
            YouTubeAPIError: For other API errors
        """
        status_code = getattr(error, 'resp', {}).get('status', 0)

        if status_code == 403:
            error_content = error.content.decode() if hasattr(error, 'content') else str(error)
            if "quotaExceeded" in error_content or "dailyLimitExceeded" in error_content:
                self.quota_exceeded = True
                self.output.warning(f"Quota exceeded during {operation}")

                if not self._switch_to_next_key():
                    self.output.error(f"All API keys exhausted during {operation}")
                    raise QuotaExceededError("All YouTube API keys quota exceeded")

                self.output.info(f"Retrying {operation} with new API key")
                return

        elif status_code == 429:
            # Rate limiting
            retry_after = getattr(error, 'resp', {}).get('retry_after', 60)
            self.output.warning(f"Rate limited during {operation} - waiting {retry_after}s")
            time.sleep(retry_after)
            return

        # Other errors
        raise YouTubeAPIError(f"YouTube API error during {operation}: {error}")

    def _make_api_request(self, operation: Callable[[], Any], max_retries: int = 3) -> Any:
        """
        Make an API request with error handling and retries.

        Args:
            operation: Description of the operation
            max_retries: Maximum number of retries

        Returns:
            API response

        Raises:
            YouTubeAPIError: If request ultimately fails
        """
        for attempt in range(max_retries + 1):
            try:
                # Rate limiting
                now = time.time()
                time_since_last = now - self.last_request_time
                if time_since_last < self.config.min_request_interval:
                    sleep_time = self.config.min_request_interval - time_since_last
                    time.sleep(sleep_time)

                # Make request
                self.last_request_time = time.time()
                self.request_count += 1

                return operation()

            except HttpError as e:
                if attempt < max_retries:
                    self._handle_api_error(e, operation.__name__ if callable(operation) else str(operation))
                    continue
                else:
                    raise YouTubeAPIError(f"API request failed after {max_retries + 1} attempts: {e}")

            except Exception as e:
                if attempt < max_retries:
                    delay = self.config.retry_delays[min(attempt, len(self.config.retry_delays) - 1)]
                    self.output.warning(f"Request failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    self.output.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    raise YouTubeAPIError(f"Request failed after {max_retries + 1} attempts: {e}")

    def search_videos(self, query: str, max_results: int = 50) -> List[VideoMetadata]:
        """
        Search for videos using YouTube Data API.

        Args:
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of VideoMetadata objects
        """
        self.output.debug(f"Searching for videos: '{query}' (max {max_results})")

        def _search_request():
            request = self.youtube_service.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=min(max_results, 50),  # API limit is 50
                order="relevance",
                safeSearch="strict"
            )
            return request.execute()

        try:
            response = self._make_api_request(_search_request)
            return self._parse_search_response(response)
        except QuotaExceededError:
            raise
        except Exception as e:
            self.output.error(f"Search failed for query '{query}': {e}")
            return []

    def search_videos_in_channel(self, channel_id: str, query: str, max_results: int = 50) -> List[VideoMetadata]:
        """
        Search for videos within a specific channel using YouTube Data API.

        Args:
            channel_id: YouTube channel ID
            query: Search query
            max_results: Maximum number of results to return

        Returns:
            List of VideoMetadata objects from the channel
        """
        self.output.debug(f"Searching channel {channel_id} for videos: '{query}' (max {max_results})")

        def _channel_search_request():
            request = self.youtube_service.search().list(
                part="snippet",
                q=query,
                type="video",
                channelId=channel_id,
                maxResults=min(max_results, 50),  # API limit is 50
                order="relevance",
                safeSearch="strict"
            )
            return request.execute()

        try:
            response = self._make_api_request(_channel_search_request)
            return self._parse_search_response(response)
        except QuotaExceededError:
            raise
        except Exception as e:
            self.output.error(f"Channel search failed for channel {channel_id} with query '{query}': {e}")
            return []
    def get_video_details_batch(self, video_ids: List[str]) -> Dict[str, VideoMetadata]:
        if not video_ids:
            return {}

        self.output.debug(f"Getting details for {len(video_ids)} videos")

        # Process in batches of 50 (API limit)
        all_metadata = {}
        batch_size = 50

        for i in range(0, len(video_ids), batch_size):
            batch_ids = video_ids[i:i + batch_size]

            def _details_request():
                request = self.youtube_service.videos().list(
                    part="snippet,contentDetails,statistics",
                    id=",".join(batch_ids)
                )
                return request.execute()

            try:
                response = self._make_api_request(_details_request)
                batch_metadata = self._parse_video_details_response(response)
                all_metadata.update(batch_metadata)
            except QuotaExceededError:
                raise
            except Exception as e:
                self.output.error(f"Failed to get details for batch {i//batch_size + 1}: {e}")
                continue

        return all_metadata

    def _parse_search_response(self, response: Dict[str, Any]) -> List[VideoMetadata]:
        """Parse YouTube search API response."""
        videos = []

        for item in response.get('items', []):
            try:
                metadata = VideoMetadata.from_youtube_api_response(item)
                videos.append(metadata)
            except Exception as e:
                self.output.warning(f"Failed to parse search result: {e}")
                continue

        self.output.debug(f"Parsed {len(videos)} videos from search response")
        return videos

    def _parse_video_details_response(self, response: Dict[str, Any]) -> Dict[str, VideoMetadata]:
        """Parse YouTube video details API response."""
        metadata_dict = {}

        for item in response.get('items', []):
            try:
                metadata = VideoMetadata.from_youtube_api_response(item)
                metadata_dict[metadata.video_id] = metadata
            except Exception as e:
                self.output.warning(f"Failed to parse video details: {e}")
                continue

        self.output.debug(f"Parsed {len(metadata_dict)} video details")
        return metadata_dict

    def get_quota_status(self) -> Dict[str, Any]:
        """
        Get current quota status and usage statistics.

        Returns:
            Dictionary with quota information
        """
        return {
            "current_key_index": self.current_key_index,
            "total_keys": len(self.api_keys),
            "quota_exceeded": self.quota_exceeded,
            "request_count": self.request_count,
            "last_request_time": self.last_request_time,
            "current_key_suffix": self._current_key[-4:] if self.api_keys else None
        }