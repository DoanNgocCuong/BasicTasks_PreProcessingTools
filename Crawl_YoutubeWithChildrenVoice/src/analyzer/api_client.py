"""
Analysis API Client - Interface to audio analysis service

This module provides a client for communicating with the analysis API
to perform children's voice detection on audio files.
"""

import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from pathlib import Path

from ..config import AnalysisAPIConfig
from ..models import VideoMetadata
from ..utils import get_output_manager


@dataclass
class AnalysisResult:
    """Result of audio analysis."""
    video_id: str
    is_child_voice: bool
    confidence: float
    processing_time: float
    metadata: Dict[str, Any]


class AnalysisAPIError(Exception):
    """Base exception for analysis API errors."""
    pass


class AnalysisAPIClient:
    """
    Client for the audio analysis API service.

    Handles communication with the analysis service to detect
    children's voice in audio files.
    """

    def __init__(self, config: AnalysisAPIConfig):
        """
        Initialize analysis API client.

        Args:
            config: Analysis API configuration
        """
        self.config = config
        self.output = get_output_manager()

        # HTTP client session
        self.session: Optional[aiohttp.ClientSession] = None

        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0

        self.output.debug(f"Initialized analysis API client for {config.server_url}")

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
            self.output.debug("Analysis API client session started")

    async def close(self) -> None:
        """Close the API client session."""
        if self.session:
            await self.session.close()
            self.session = None
            self.output.debug("Analysis API client session closed")

    async def analyze_videos(self, videos: List[VideoMetadata]) -> List[AnalysisResult]:
        """
        Analyze a batch of videos through the API.

        Args:
            videos: List of videos to analyze

        Returns:
            List of analysis results
        """
        if not self.config.enabled:
            self.output.info("Analysis API disabled - skipping analysis")
            return [
                AnalysisResult(
                    video_id=video.video_id,
                    is_child_voice=True,  # Assume true when API disabled
                    confidence=1.0,
                    processing_time=0.0,
                    metadata={}
                )
                for video in videos
            ]

        if not self.session:
            await self.start()

        self.output.info(f"Sending {len(videos)} videos to analysis API")

        results = []
        for video in videos:
            try:
                result = await self._analyze_single_video(video)
                results.append(result)
            except Exception as e:
                self.output.error(f"Failed to analyze video {video.video_id}: {e}")
                results.append(AnalysisResult(
                    video_id=video.video_id,
                    is_child_voice=False,
                    confidence=0.0,
                    processing_time=0.0,
                    metadata={"error": str(e)}
                ))

        # Update statistics
        self._update_statistics(results)

        # Log summary
        self._log_analysis_summary(results)

        return results

    async def _analyze_single_video(self, video: VideoMetadata) -> AnalysisResult:
        """
        Analyze a single video through the API.

        Args:
            video: Video to analyze

        Returns:
            Analysis result
        """
        import time
        start_time = time.time()

        # Prepare request data
        request_data = self._prepare_analysis_request(video)

        # Make API request with retries
        for attempt in range(self.config.max_retries + 1):
            try:
                assert self.session is not None  # Session should be initialized by analyze_videos
                async with self.session.post(
                    f"{self.config.server_url}/analyze",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                ) as response:

                    self.total_requests += 1

                    if response.status == 200:
                        response_data = await response.json()
                        self.successful_requests += 1

                        return AnalysisResult(
                            video_id=video.video_id,
                            is_child_voice=response_data.get("is_child_voice", False),
                            confidence=response_data.get("confidence", 0.0),
                            processing_time=time.time() - start_time,
                            metadata=response_data.get("metadata", {})
                        )
                    else:
                        error_text = await response.text()
                        self.output.warning(f"Analysis API returned status {response.status}: {error_text}")

                        if attempt < self.config.max_retries:
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                            continue
                        else:
                            raise AnalysisAPIError(f"API returned status {response.status}: {error_text}")

            except aiohttp.ClientError as e:
                self.output.warning(f"Analysis API request failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise AnalysisAPIError(f"Request failed after {self.config.max_retries + 1} attempts: {e}")

        # Should not reach here
        raise AnalysisAPIError("Unexpected error in analysis")

    def _prepare_analysis_request(self, video: VideoMetadata) -> Dict[str, Any]:
        """
        Prepare request data for the analysis API.

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
            "duration": video.duration_seconds,
            "audio_path": str(getattr(video, 'audio_path', '')) if hasattr(video, 'audio_path') else None,
            # Include any additional metadata that might help analysis
            "tags": video.tags or [],
            "view_count": video.view_count,
            "published_at": video.published_at.isoformat() if video.published_at else None,
        }

    def _update_statistics(self, results: List[AnalysisResult]) -> None:
        """Update analysis statistics."""
        self.total_requests = len(results)
        self.successful_requests = sum(1 for r in results if r.is_child_voice)
        self.failed_requests = self.total_requests - self.successful_requests

    def _log_analysis_summary(self, results: List[AnalysisResult]) -> None:
        """Log comprehensive analysis summary."""
        child_voice_count = sum(1 for r in results if r.is_child_voice)
        non_child_count = len(results) - child_voice_count

        self.output.info("=== Analysis Summary ===")
        self.output.info(f"Total videos analyzed: {len(results)}")
        self.output.info(f"Children's voice detected: {child_voice_count}")
        self.output.info(f"No children's voice: {non_child_count}")

        if len(results) > 0:
            detection_rate = (child_voice_count / len(results)) * 100
            self.output.info(f"Detection rate: {detection_rate:.1f}%")

    async def health_check(self) -> bool:
        """
        Check if the analysis API is healthy.

        Returns:
            True if API is responding
        """
        if not self.config.enabled:
            return True

        if not self.session:
            await self.start()

        try:
            assert self.session is not None  # Session should be initialized by health_check
            async with self.session.get(f"{self.config.server_url}/health") as response:
                return response.status == 200
        except Exception:
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get analysis statistics.

        Returns:
            Dictionary with analysis statistics
        """
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0,
            "api_enabled": self.config.enabled,
            "server_url": self.config.server_url
        }