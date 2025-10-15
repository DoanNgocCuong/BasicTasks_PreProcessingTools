# Crawler package - YouTube search and collection

"""
Crawler Package - YouTube video discovery and collection

This package handles all aspects of discovering and collecting YouTube videos,
including API interactions, search coordination, and metadata management.
"""

from .youtube_api import YouTubeAPIClient, YouTubeAPIError, QuotaExceededError
from .search_engine import SearchEngine

# Lazy import to avoid loading heavy dependencies at package import time
def __getattr__(name):
    if name == "run_search_phase":
        from .search_phases import run_search_phase
        return run_search_phase
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "YouTubeAPIClient",
    "YouTubeAPIError",
    "QuotaExceededError",
    "SearchEngine"
]