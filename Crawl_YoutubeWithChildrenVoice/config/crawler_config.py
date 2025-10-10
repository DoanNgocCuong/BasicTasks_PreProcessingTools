"""
Crawler Configuration

Configuration constants and settings for the YouTube video crawler module.

Author: Refactoring Assistant
"""

from pathlib import Path
from .base_config import BaseConfig


class CrawlerConstants(BaseConfig):
    """Configuration constants for the YouTube video crawler."""
    
    def __init__(self):
        super().__init__()
        
        # API and URL constants
        self.YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
        self.YOUTUBE_VIDEO_URL_PREFIX = "https://www.youtube.com/watch?v="
        self.MAX_RESULTS_PER_REQUEST = 50
        
        # File paths
        self.DEFAULT_CONFIG_FILE = str(self.base_dir / "crawler_config.json")
        self.DEFAULT_URLS_FILE = str(self.output_dir / "collected_video_urls.txt")
        self.DEFAULT_REPORT_FILE = str(self.output_dir / "collection_report.txt")
        self.DEFAULT_DETAILED_RESULTS_FILE = str(self.output_dir / "detailed_collection_results.json")
        self.DEFAULT_STATISTICS_FILE = str(self.output_dir / "query_efficiency_statistics.json")
        self.DEFAULT_MAIN_URLS_FILE = str(self.output_dir / "multi_query_collected_video_urls.txt")
        self.DEFAULT_MAIN_DETAILED_FILE = str(self.output_dir / "multi_query_detailed_results.json")
        self.DEFAULT_BACKUP_FILE_PREFIX = str(self.output_dir / "backup")

        # Validation constants
        self.MIN_TARGET_COUNT = 1
        self.MAX_RECOMMENDED_PER_QUERY = 100
        
        # Default values
        self.DEBUG_PREFIX = "🔍 DEBUG: "
        self.DEFAULT_QUERY = "bé giới thiệu bản thân"
        
        # Common message patterns
        self.CHUNK_ANALYSIS_TIME_ESTIMATE = 20  # seconds per chunk
        self.MAX_CONSECUTIVE_NO_CHILDREN = 3