"""
Filterer API Client - Interface to content filtering service

This module provides a client for communicating with the filterer API
to validate and filter processed children's voice content.
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from config import FiltererAPIConfig
from models import VideoMetadata
from utils import get_output_manager


@dataclass
class FilterResult:
    """Result of content filtering."""
    video_id: str
    passed_filter: bool
    filter_score: float
    reasons: List[str]
    metadata: Dict[str, Any]
    processing_time: float


class FiltererAPIError(Exception):
    """Base exception for filterer API errors."""
    pass


class FiltererAPIClient:
    """
    Client for the content filterer API service.

    Handles communication with the filtering service to validate
    processed children's voice content.
    """

    def __init__(self, config: FiltererAPIConfig):
        """
        Initialize filterer API client.

        Args:
            config: Filterer API configuration
        """
        self.config = config
        self.output = get_output_manager()

        # HTTP client session
        self.session: Optional[aiohttp.ClientSession] = None

        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

        self.output.debug(f"Initialized filterer API client for {config.server_url}")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self) -> None:
        """Start the API client session."""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self.session = aiohttp.ClientSession(timeout=timeout)
            self.output.debug("Filterer API client session started")

    async def close(self) -> None:
        """Close the API client session."""
        if self.session:
            await self.session.close()
            self.session = None
            self.output.debug("Filterer API client session closed")

    async def filter_videos(self, videos: List[VideoMetadata]) -> List[FilterResult]:
        """
        Filter a batch of videos through the API.

        Args:
            videos: List of videos to filter

        Returns:
            List of filter results
        """
        if not self.config.enabled:
            self.output.info("Filterer API disabled - skipping filtering")
            return [
                FilterResult(
                    video_id=video.video_id,
                    passed_filter=True,
                    filter_score=1.0,
                    reasons=["API disabled"],
                    metadata={},
                    processing_time=0.0
                )
                for video in videos
            ]

        if not self.session:
            await self.start()

        self.output.info(f"Sending {len(videos)} videos to filterer API")

        results = []
        for video in videos:
            try:
                result = await self._filter_single_video(video)
                results.append(result)
            except Exception as e:
                self.output.error(f"Failed to filter video {video.video_id}: {e}")
                results.append(FilterResult(
                    video_id=video.video_id,
                    passed_filter=False,
                    filter_score=0.0,
                    reasons=[f"API error: {str(e)}"],
                    metadata={},
                    processing_time=0.0
                ))

        # Update statistics
        self._update_statistics(results)

        # Log summary
        self._log_filtering_summary(results)

        return results

    async def _filter_single_video(self, video: VideoMetadata) -> FilterResult:
        """
        Filter a single video through the API.

        Args:
            video: Video to filter

        Returns:
            Filter result
        """
        import time
        start_time = time.time()

        # Prepare request data
        request_data = self._prepare_filter_request(video)

        # Make API request with retries
        for attempt in range(self.config.max_retries + 1):
            try:
                async with self.session.post(
                    f"{self.config.server_url}/filter",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                ) as response:

                    self.total_requests += 1

                    if response.status == 200:
                        response_data = await response.json()
                        self.successful_requests += 1

                        return FilterResult(
                            video_id=video.video_id,
                            passed_filter=response_data.get("passed", False),
                            filter_score=response_data.get("score", 0.0),
                            reasons=response_data.get("reasons", []),
                            metadata=response_data.get("metadata", {}),
                            processing_time=time.time() - start_time
                        )
                    else:
                        error_text = await response.text()
                        self.output.warning(f"Filter API returned status {response.status}: {error_text}")

                        if attempt < self.config.max_retries:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            raise FiltererAPIError(f"API returned status {response.status}: {error_text}")

            except aiohttp.ClientError as e:
                self.output.warning(f"Filter API request failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise FiltererAPIError(f"Request failed after {self.config.max_retries + 1} attempts: {e}")

        # Should not reach here
        raise FiltererAPIError("Unexpected error in filtering")

    def _prepare_filter_request(self, video: VideoMetadata) -> Dict[str, Any]:
        """
        Prepare request data for the filter API.

        Args:
            video: Video metadata

        Returns:
            Request data dictionary
        """
        return {
            "video_id": video.video_id,
            "title": video.title,
            "description": video.description,
            "channel_title": video.channel_title,
            "tags": video.tags or [],
            "duration": video.duration_seconds,
            "view_count": video.view_count,
            "like_count": video.like_count,
            "comment_count": video.comment_count,
            "published_at": video.published_at.isoformat() if video.published_at else None,
            # Add analysis results if available
            "analysis_results": getattr(video, 'analysis_results', {}),
            # Add audio file path if available
            "audio_path": str(getattr(video, 'audio_path', '')) if hasattr(video, 'audio_path') else None
        }

    def _update_statistics(self, results: List[FilterResult]) -> None:
        """Update filtering statistics."""
        self.total_requests = len(results)
        self.successful_requests = sum(1 for r in results if r.passed_filter)
        self.failed_requests = self.total_requests - self.successful_requests

    def _log_filtering_summary(self, results: List[FilterResult]) -> None:
        """Log comprehensive filtering summary."""
        passed_count = sum(1 for r in results if r.passed_filter)
        failed_count = len(results) - passed_count

        self.output.info("=== Filtering Summary ===")
        self.output.info(f"Total videos processed: {len(results)}")
        self.output.info(f"Passed filtering: {passed_count}")
        self.output.info(f"Failed filtering: {failed_count}")

        if len(results) > 0:
            pass_rate = (passed_count / len(results)) * 100
            self.output.info(f"Pass rate: {pass_rate:.1f}%")

        # Log top failure reasons
        failure_reasons = {}
        for result in results:
            if not result.passed_filter:
                for reason in result.reasons:
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

        if failure_reasons:
            self.output.info("Top failure reasons:")
            sorted_reasons = sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)
            for reason, count in sorted_reasons[:5]:
                self.output.info(f"  - {reason}: {count} videos")

    async def health_check(self) -> bool:
        """
        Check if the filterer API is healthy.

        Returns:
            True if API is responding
        """
        if not self.config.enabled:
            return True

        if not self.session:
            await self.start()

        try:
            async with self.session.get(f"{self.config.server_url}/health") as response:
                return response.status == 200
        except Exception:
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get filtering statistics.

        Returns:
            Dictionary with filtering statistics
        """
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            "api_enabled": self.config.enabled,
            "server_url": self.config.server_url
        }