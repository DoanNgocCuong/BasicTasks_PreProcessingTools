# downloader package

"""
Downloader Package - Audio download and processing

This package handles downloading audio from YouTube videos,
including fallback mechanisms and quality optimization.
"""

from .audio_downloader import AudioDownloader, DownloadError, DownloadResult

__all__ = [
    "AudioDownloader",
    "DownloadError",
    "DownloadResult"
]