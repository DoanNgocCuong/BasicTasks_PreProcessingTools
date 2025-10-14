# Crawler package - YouTube search and collection

"""
Crawler Package - YouTube video discovery and collection

This package handles all aspects of discovering and collecting YouTube videos,
including API interactions, search coordination, and metadata management.
"""

from .youtube_api import YouTubeAPIClient, YouTubeAPIError, QuotaExceededError
from .search_engine import SearchEngine

__all__ = [
    "YouTubeAPIClient",
    "YouTubeAPIError",
    "QuotaExceededError",
    "SearchEngine"
]