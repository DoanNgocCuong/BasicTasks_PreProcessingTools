"""
Audio Downloader - Download audio from YouTube videos

This module provides functionality to download audio from YouTube videos
using multiple methods with fallback support.
"""

import asyncio
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, parse_qs

from config import DownloadConfig
from models import VideoMetadata, DownloadResult
from utils import get_output_manager, get_file_manager


class DownloadError(Exception):
    """Base exception for download errors."""
    pass


class YouTubeDLError(DownloadError):
    """Exception raised when yt-dlp fails."""
    pass


class APIAssistedError(DownloadError):
    """Exception raised when API-assisted download fails."""
    pass


@dataclass
class DownloadAttempt:
    """Represents a single download attempt."""
    method: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    error_message: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None

    @property
    def completed(self) -> bool:
        """Check if attempt is completed."""
        return self.end_time is not None

    def complete(self, success: bool, error_message: Optional[str] = None, file_size: Optional[int] = None) -> None:
        """Mark attempt as completed."""
        self.end_time = time.time()
        self.success = success
        self.error_message = error_message
        self.file_size = file_size
        self.duration = self.end_time - self.start_time


class AudioDownloader:
    """
    Downloads audio from YouTube videos using multiple strategies.

    Supports yt-dlp primary method with API-assisted fallback,
    with comprehensive error handling and progress tracking.
    """

    def __init__(self, config: DownloadConfig):
        """
        Initialize audio downloader.

        Args:
            config: Download configuration
        """
        self.config = config
        self.output = get_output_manager()
        self.file_manager = get_file_manager()

        # Download statistics
        self.total_downloads = 0
        self.successful_downloads = 0
        self.failed_downloads = 0

        self.output.debug("Initialized audio downloader")

    async def download_videos_audio(self, videos: List[VideoMetadata]) -> List[DownloadResult]:
        """
        Download audio for multiple videos.

        Args:
            videos: List of videos to download

        Returns:
            List of download results
        """
        self.output.info(f"Starting audio download for {len(videos)} videos")

        results = []
        semaphore = asyncio.Semaphore(self.config.max_concurrent_downloads)

        async def download_with_semaphore(video: VideoMetadata) -> DownloadResult:
            async with semaphore:
                return await self.download_video_audio(video)

        # Download videos concurrently
        tasks = [download_with_semaphore(video) for video in videos]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions and convert to DownloadResult
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                video = videos[i]
                self.output.error(f"Download failed for {video.video_id}: {result}")
                processed_results.append(DownloadResult(
                    video_id=video.video_id,
                    success=False,
                    error_message=str(result),
                    attempts=[]
                ))
            else:
                processed_results.append(result)

        # Update statistics
        self._update_statistics(processed_results)

        # Log summary
        self._log_download_summary(processed_results)

        return processed_results

    async def download_video_audio(self, video: VideoMetadata) -> DownloadResult:
        """
        Download audio for a single video.

        Args:
            video: Video metadata

        Returns:
            Download result
        """
        self.output.debug(f"Downloading audio for video: {video.video_id}")

        attempts = []
        result = DownloadResult(video_id=video.video_id, attempts=attempts)

        # Try primary method first
        if self.config.yt_dlp_primary:
            attempt = await self._try_yt_dlp_download(video)
            attempts.append(attempt)
            if attempt.success:
                result.success = True
                result.output_path = attempt.output_path
                result.file_size = attempt.file_size
                result.duration = attempt.duration
                return result

        # Try API-assisted method as fallback
        if self.config.method == "api_assisted":
            attempt = await self._try_api_assisted_download(video)
            attempts.append(attempt)
            if attempt.success:
                result.success = True
                result.output_path = attempt.output_path
                result.file_size = attempt.file_size
                result.duration = attempt.duration
                return result

        # All methods failed
        result.success = False
        result.error_message = "All download methods failed"
        return result

    async def _try_yt_dlp_download(self, video: VideoMetadata) -> DownloadAttempt:
        """
        Try downloading using yt-dlp.

        Args:
            video: Video metadata

        Returns:
            Download attempt result
        """
        attempt = DownloadAttempt(method="yt-dlp", start_time=time.time())

        try:
            # Prepare output path
            output_dir = self.file_manager.audio_outputs_dir
            output_path = output_dir / f"{video.video_id}.%(ext)s"

            # Build yt-dlp command
            cmd = [
                "yt-dlp",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "128K",
                "--output", str(output_path),
                "--no-playlist",
                "--quiet",
                "--no-warnings",
                f"https://www.youtube.com/watch?v={video.video_id}"
            ]

            # Add user agent if specified
            if self.config.user_agent:
                cmd.extend(["--user-agent", self.config.user_agent])

            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                # Check if file was created
                actual_path = output_dir / f"{video.video_id}.mp3"
                if actual_path.exists():
                    file_size = actual_path.stat().st_size
                    attempt.complete(True, file_size=file_size)
                    attempt.output_path = actual_path
                    self.output.debug(f"yt-dlp download successful: {video.video_id}")
                else:
                    attempt.complete(False, "Output file not found")
            else:
                error_msg = stderr.decode() if stderr else "Unknown yt-dlp error"
                attempt.complete(False, error_msg)

        except Exception as e:
            attempt.complete(False, str(e))

        return attempt

    async def _try_api_assisted_download(self, video: VideoMetadata) -> DownloadAttempt:
        """
        Try downloading using API-assisted method.

        Args:
            video: Video metadata

        Returns:
            Download attempt result
        """
        attempt = DownloadAttempt(method="api_assisted", start_time=time.time())

        try:
            # This would integrate with YouTube API to get direct download URLs
            # For now, fall back to yt-dlp with different parameters
            output_dir = self.file_manager.audio_outputs_dir
            output_path = output_dir / f"{video.video_id}_api.%(ext)s"

            cmd = [
                "yt-dlp",
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "128K",
                "--output", str(output_path),
                "--no-playlist",
                "--quiet",
                "--no-warnings",
                "--format", "bestaudio/best",  # More restrictive format selection
                f"https://www.youtube.com/watch?v={video.video_id}"
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                actual_path = output_dir / f"{video.video_id}_api.mp3"
                if actual_path.exists():
                    file_size = actual_path.stat().st_size
                    attempt.complete(True, file_size=file_size)
                    attempt.output_path = actual_path
                    self.output.debug(f"API-assisted download successful: {video.video_id}")
                else:
                    attempt.complete(False, "Output file not found")
            else:
                error_msg = stderr.decode() if stderr else "Unknown API-assisted error"
                attempt.complete(False, error_msg)

        except Exception as e:
            attempt.complete(False, str(e))

        return attempt

    def _update_statistics(self, results: List[DownloadResult]) -> None:
        """Update download statistics."""
        self.total_downloads = len(results)
        self.successful_downloads = sum(1 for r in results if r.success)
        self.failed_downloads = self.total_downloads - self.successful_downloads

    def _log_download_summary(self, results: List[DownloadResult]) -> None:
        """Log comprehensive download summary."""
        self.output.info("=== Download Summary ===")
        self.output.info(f"Total videos: {self.total_downloads}")
        self.output.info(f"Successful: {self.successful_downloads}")
        self.output.info(f"Failed: {self.failed_downloads}")

        if self.total_downloads > 0:
            success_rate = (self.successful_downloads / self.total_downloads) * 100
            self.output.info(f"Success rate: {success_rate:.1f}%")

        # Log failures
        failed_results = [r for r in results if not r.success]
        if failed_results:
            self.output.warning("Failed downloads:")
            for result in failed_results[:5]:  # Show first 5 failures
                self.output.warning(f"  - {result.video_id}: {result.error_message}")
            if len(failed_results) > 5:
                self.output.warning(f"  ... and {len(failed_results) - 5} more")

    def get_download_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive download statistics.

        Returns:
            Dictionary with download statistics
        """
        return {
            "total_downloads": self.total_downloads,
            "successful_downloads": self.successful_downloads,
            "failed_downloads": self.failed_downloads,
            "success_rate": (self.successful_downloads / self.total_downloads * 100) if self.total_downloads > 0 else 0
        }