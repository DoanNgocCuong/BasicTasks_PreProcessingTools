# downloader package

"""
Downloader Package - Audio download and processing

This package handles downloading audio from YouTube videos,
including fallback mechanisms and quality optimization.
"""

from .audio_downloader import AudioDownloader, DownloadError, DownloadResult

# Lazy import to avoid loading heavy dependencies at package import time
def __getattr__(name):
    if name == "run_download_phase_from_urls":
        from .download_phases import run_download_phase_from_urls
        return run_download_phase_from_urls
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "AudioDownloader",
    "DownloadError",
    "DownloadResult"
]