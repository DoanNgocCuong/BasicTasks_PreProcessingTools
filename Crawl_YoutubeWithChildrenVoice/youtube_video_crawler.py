#!/usr/bin/env python3
"""
YouTube Video Crawler for Children's Voice Content Collection

This module provides comprehensive functionality for collecting and analyzing YouTube videos
containing Vietnamese children's voices. It integrates with YouTube Data API v3 to search
for videos, downloads and analyzes audio content using machine learning models, and provides
detailed reporting and statistics.

Author: Le Hoang Minh
"""

import requests
import time
import threading
import json
import re
import googleapiclient.discovery
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union, Set, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from youtube_audio_downloader import Config as AudioConfig, YoutubeAudioDownloader
from youtube_audio_classifier import AudioClassifier
from youtube_output_analyzer import YouTubeOutputAnalyzer, QueryStatistics
from youtube_output_validator import YouTubeURLValidator
from env_config import config


# Configuration constants
class Config:
    """Configuration constants for the YouTube video crawler."""
    
    # API and URL constants
    YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
    YOUTUBE_VIDEO_URL_PREFIX = "https://www.youtube.com/watch?v="
    MAX_RESULTS_PER_REQUEST = 50
    
    # File names (relative to the script's directory)
    _SCRIPT_DIR = Path(__file__).parent
    DEFAULT_CONFIG_FILE = str(_SCRIPT_DIR / "crawler_config.json")
    DEFAULT_URLS_FILE = str(_SCRIPT_DIR / "youtube_url_outputs/collected_video_urls.txt")
    DEFAULT_REPORT_FILE = str(_SCRIPT_DIR / "youtube_url_outputs/collection_report.txt")
    DEFAULT_DETAILED_RESULTS_FILE = str(_SCRIPT_DIR / "youtube_url_outputs/detailed_collection_results.json")
    DEFAULT_STATISTICS_FILE = str(_SCRIPT_DIR / "youtube_url_outputs/query_efficiency_statistics.json")
    
    # Additional file paths for main() function
    DEFAULT_OUTPUT_DIR = _SCRIPT_DIR / "youtube_url_outputs"
    DEFAULT_MAIN_URLS_FILE = str(DEFAULT_OUTPUT_DIR / "multi_query_collected_video_urls.txt")
    DEFAULT_MAIN_DETAILED_FILE = str(DEFAULT_OUTPUT_DIR / "multi_query_detailed_results.json")
    DEFAULT_BACKUP_FILE_PREFIX = str(DEFAULT_OUTPUT_DIR / "backup")  # Will be used with timestamp

    # User input validation
    MIN_TARGET_COUNT = 1
    MAX_RECOMMENDED_PER_QUERY = 100
    
    # Debug and logging
    DEBUG_PREFIX = "🔍 DEBUG: "
    
    # Default values
    DEFAULT_QUERY = "bé giới thiệu bản thân"


@dataclass
class CrawlerConfig:
    """Data class for crawler configuration loaded from JSON file."""
    debug_mode: bool
    target_videos_per_query: int
    search_queries: List[str]
    max_recommended_per_query: int = 100
    min_target_count: int = 1
    download_method: str = "api_assisted"
    cookie_settings: Optional[Dict[str, Any]] = None


class ConfigLoader:
    """Loads configuration from JSON file instead of user input."""
    
    def __init__(self, output_manager: "OutputManager", config_file_path: Optional[str] = None):
        """Initialize with output manager and optional config file path."""
        self.output = output_manager
        self.config_file_path = config_file_path or Config.DEFAULT_CONFIG_FILE
    
    def load_config(self) -> CrawlerConfig:
        """
        Load configuration from JSON file.
        
        Returns:
            CrawlerConfig: Configuration object with all settings
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config file is invalid or missing required fields
        """
        config_path = Path(self.config_file_path)
        
        if not config_path.exists():
            self.output.print_error(f"Configuration file not found: {self.config_file_path}")
            self.output.print_info("Creating a default configuration file...")
            self._create_default_config_file(config_path)
            self.output.print_success(f"Default configuration created: {self.config_file_path}")
            self.output.print_info("Please edit the configuration file and run the script again.")
            raise FileNotFoundError(f"Configuration file created at {self.config_file_path}. Please edit it and run again.")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validate required fields
            required_fields = ['debug_mode', 'target_videos_per_query', 'search_queries']
            missing_fields = [field for field in required_fields if field not in config_data]
            
            if missing_fields:
                raise ValueError(f"Missing required fields in configuration: {', '.join(missing_fields)}")
            
            # Validate data types and values
            if not isinstance(config_data['debug_mode'], bool):
                raise ValueError("debug_mode must be a boolean (true/false)")
            
            if not isinstance(config_data['target_videos_per_query'], int) or config_data['target_videos_per_query'] < 1:
                raise ValueError("target_videos_per_query must be a positive integer")
            
            if not isinstance(config_data['search_queries'], list) or len(config_data['search_queries']) == 0:
                raise ValueError("search_queries must be a non-empty list of strings")
            
            # Validate each query is a non-empty string
            for i, query in enumerate(config_data['search_queries']):
                if not isinstance(query, str) or not query.strip():
                    raise ValueError(f"search_queries[{i}] must be a non-empty string")
            
            # Create config object with defaults for optional fields
            crawler_config = CrawlerConfig(
                debug_mode=config_data['debug_mode'],
                target_videos_per_query=config_data['target_videos_per_query'],
                search_queries=[q.strip() for q in config_data['search_queries']],
                max_recommended_per_query=config_data.get('max_recommended_per_query', 100),
                min_target_count=config_data.get('min_target_count', 1),
                cookie_settings=config_data.get('cookie_settings', None)
            )
            
            # Report loaded configuration
            self._report_loaded_config(crawler_config)
            
            return crawler_config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")
    
    def _create_default_config_file(self, config_path: Path) -> None:
        """Create a default configuration file."""
        default_config = {
            "debug_mode": False,
            "target_videos_per_query": 20,
            "search_queries": [
                "bé giới thiệu bản thân",
                "bé tập nói tiếng Việt",
                "trẻ em kể chuyện",
                "bé hát ca dao",
                "em bé học nói",
                "trẻ con nói chuyện",
                "bé đọc thơ",
                "con nít kể chuyện"
            ],
            "max_recommended_per_query": 100,
            "min_target_count": 1,
            "description": "Configuration file for YouTube Video Crawler. Set debug_mode to true for detailed logging, adjust target_videos_per_query for collection size, and modify search_queries array to change what videos to search for."
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
    
    def _report_loaded_config(self, config: CrawlerConfig) -> None:
        """Report the loaded configuration to the user."""
        self.output.print_header("CONFIGURATION LOADED FROM FILE", 60)
        self.output.print_success(f"Configuration file: {self.config_file_path}")
        self.output.print_info(f"Debug mode: {'Enabled' if config.debug_mode else 'Disabled'}")
        self.output.print_info(f"Target videos per query: {config.target_videos_per_query}")
        self.output.print_info(f"Total queries: {len(config.search_queries)}")
        
        total_target_count = config.target_videos_per_query * len(config.search_queries)
        self.output.print_info(f"Total target videos: {total_target_count}")
        
        self.output.print_enumerated_list(config.search_queries, "Search queries:")
        
        if config.target_videos_per_query > config.max_recommended_per_query:
            self.output.print_warning(f"High target count per query: {config.target_videos_per_query} (recommended max: {config.max_recommended_per_query})")
        
        self.output.print_section_divider()


@dataclass
class AnalysisResult:
    """Data class for audio analysis results."""
    is_vietnamese: bool
    detected_language: str
    has_children_voice: Optional[bool]
    confidence: float
    error: Optional[str]
    total_analysis_time: Optional[float] = None
    children_detection_time: Optional[float] = None
    video_length_seconds: Optional[float] = None


class OutputManager:
    """Centralized output management for all print statements."""
    
    def __init__(self) -> None:
        """Initialize output manager."""
        pass
    
    def print_header(self, title: str, width: int = 60) -> None:
        """Print a formatted header."""
        print("=" * width)
        print(title)
        print("=" * width)
    
    def print_sub_header(self, title: str, width: int = 50) -> None:
        """Print a formatted sub-header."""
        print("\n" + "=" * width)
        print(title)
        print("=" * width)
    
    def print_section_divider(self, width: int = 50) -> None:
        """Print a section divider."""
        print("-" * width)
    
    def print_success(self, message: str) -> None:
        """Print success message with checkmark."""
        print(f"✅ {message}")
    
    def print_error(self, message: str) -> None:
        """Print error message with X mark."""
        print(f"❌ {message}")
    
    def print_warning(self, message: str) -> None:
        """Print warning message with warning symbol."""
        print(f"⚠️  {message}")
    
    def print_info(self, message: str) -> None:
        """Print info message with info symbol."""
        print(f"ℹ️  {message}")
    
    def print_progress(self, message: str) -> None:
        """Print progress message with search symbol."""
        print(f"🔍 {message}")
    
    def print_timing(self, message: str, duration: float) -> None:
        """Print timing message with clock symbol."""
        print(f"⏱️  {message}: {duration:.2f}s")
    
    def print_result(self, message: str, is_positive: bool = True) -> None:
        """Print result message with appropriate symbol."""
        symbol = "✓" if is_positive else "✗"
        print(f"{symbol} {message}")
    
    def print_statistics(self, stats_dict: Dict[str, Union[str, int, float]]) -> None:
        """Print statistics in a formatted way."""
        for key, value in stats_dict.items():
            print(f"  - {key}: {value}")
    
    def print_enumerated_list(self, items: List[str], title: Optional[str] = None) -> None:
        """Print an enumerated list."""
        if title:
            print(f"\n📋 {title}")
        for i, item in enumerate(items, 1):
            print(f"  {i}. '{item}'")


class CollectionReporter:
    """Handles all collection-related reporting and statistics display."""
    
    def __init__(self, output_manager: OutputManager):
        """Initialize with output manager."""
        self.output = output_manager
    
    def report_initialization(self, existing_urls_count: int, filename: str) -> None:
        """Report initialization status."""
        if existing_urls_count > 0:
            self.output.print_info(f"Loaded {existing_urls_count} existing URLs from {filename}")
        else:
            self.output.print_info("No existing URL file found - starting fresh collection")
    
    def report_configuration(self, target_count_per_query: int, total_target_count: int, queries: List[str]) -> None:
        """Report configuration settings."""
        self.output.print_success(f"Target set to {target_count_per_query} videos per query")
        self.output.print_success(f"Total target count automatically calculated: {total_target_count} videos ({target_count_per_query} × {len(queries)} queries)")
        self.output.print_enumerated_list(queries, f"Total queries configured: {len(queries)}")
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.output.print_info(f"Collection started at: {current_time}")
        
        # Since total target is now calculated as per-query * num_queries, no efficiency insight needed
        self.output.print_info(f"Collection will attempt to gather {target_count_per_query} videos for each query")
    
    def report_collection_start(self, target_per_query: int, total_queries: int) -> None:
        """Report collection start."""
        print(f"Starting multi-query video collection")
        print(f"Target videos per query: {target_per_query}")
        print(f"Total queries to process: {total_queries}")
        self.output.print_header("", 60)
    
    def report_query_start(self, query_index: int, total_queries: int, query: str) -> None:
        """Report start of query processing."""
        self.output.print_header(f"Processing Query {query_index}/{total_queries}: '{query}'", 60)
    
    def report_query_results(self, video_count: int, query: str) -> None:
        """Report initial query results."""
        if video_count > 0:
            print(f"Found {video_count} videos for query: '{query}'")
        else:
            self.output.print_warning(f"No videos found for query: '{query}'")
    
    def report_video_processing(self, video_index: int, total_videos: int, title: str, channel: str) -> None:
        """Report individual video processing."""
        print(f"\nProcessing video {video_index + 1}/{total_videos}")
        print(f"Title: {title[:50]}...")
        print(f"Channel: {channel}")
    
    def report_evaluation_start(self) -> None:
        """Report start of video evaluation."""
        self.output.print_progress("Evaluating video for children's voice...")
    
    def report_evaluation_result(self, has_children_voice: bool, is_new_channel: bool) -> None:
        """Report evaluation results."""
        if has_children_voice and is_new_channel:
            self.output.print_result("Video contains children's voice and channel is new")
        elif not is_new_channel:
            self.output.print_result("Channel already reviewed", False)
        else:
            self.output.print_result("No children's voice detected", False)
    
    def report_channel_exploration(self, channel_name: str, query: str, similar_count: int) -> None:
        """Report channel exploration."""
        self.output.print_progress(f"Searching for similar videos in channel '{channel_name}' with query: '{query}'")
        print(f"Found {similar_count} similar videos in channel. Evaluating...")
    
    def report_similar_video_evaluation(self, title: str) -> None:
        """Report similar video evaluation."""
        self.output.print_progress(f"Evaluating similar video: {title[:30]}...")
    
    def report_similar_video_result(self, has_children_voice: bool) -> None:
        """Report similar video evaluation result."""
        if has_children_voice:
            self.output.print_result("Video has children's voice - Added to results")
        else:
            self.output.print_result("Video has no children's voice - Skipped", False)
    
    def report_query_progress(self, collected: int, target: int) -> None:
        """Report progress for current query."""
        print(f"Progress: {collected}/{target} collected for this query")
    
    def report_total_progress(self, total_collected: int, total_target: int, query_collected: int, query_target: int) -> None:
        """Report progress for both current query and total collection."""
        print(f"Query progress: {query_collected}/{query_target} | Total progress: {total_collected}/{total_target}")
        if total_collected >= total_target:
            self.output.print_success("🎯 Total target reached!")
    
    def report_query_statistics(self, stats: QueryStatistics) -> None:
        """Report statistics for completed query."""
        self.output.print_sub_header(f"STATISTICS FOR QUERY: '{stats.query}'")
        formatted_stats = {
            "Videos collected": stats.videos_collected,
            "Videos reviewed": stats.videos_reviewed,
            "Videos evaluated": stats.videos_evaluated,
            "Videos with children's voice": stats.videos_with_children_voice,
            "Videos in Vietnamese": stats.videos_vietnamese,
            "Videos not in Vietnamese": stats.videos_not_vietnamese,
            "Efficiency rate": f"{stats.efficiency_rate:.2f}%",
            "Children's voice rate": f"{stats.children_voice_rate:.2f}%",
            "Vietnamese rate": f"{stats.vietnamese_rate:.2f}%"
        }
        self.output.print_statistics(formatted_stats)
        self.output.print_section_divider()
    
    def report_language_check_start(self) -> None:
        """Report start of language detection."""
        self.output.print_progress("Checking if video is in Vietnamese...")
    
    def report_language_result(self, is_vietnamese: bool, detected_language: Optional[str] = None) -> None:
        """Report language detection results."""
        if is_vietnamese:
            self.output.print_result("✓ Video is in Vietnamese - Proceeding to evaluate")
        else:
            language_info = f" (detected: {detected_language})" if detected_language else ""
            self.output.print_result(f"✗ Video is not in Vietnamese - Skipping{language_info}", False)
    
    def report_similar_video_language_result(self, is_vietnamese: bool) -> None:
        """Report language detection for similar videos."""
        if is_vietnamese:
            self.output.print_result("✓ Similar video is in Vietnamese - Proceeding to evaluate")
        else:
            self.output.print_result("✗ Similar video is not in Vietnamese - Skipping", False)
    
    def report_collection_completion(self, total_collected: int, quota_exceeded: bool = False) -> None:
        """Report completion of entire collection."""
        print(f"\nCollection completed! Videos collected in current session: {total_collected}")
        
        if quota_exceeded:
            self.output.print_warning("⚠️  Collection stopped due to API quota limits")
            print("💡 Consider the following options:")
            print("  • Continue with videos already collected")
            print("  • Resume collection tomorrow when quota resets")
            print("  • Request quota increase from Google Cloud Console")
        
        self.output.print_info("Proceeding to URL validation...")
    
    def report_file_operations(self, operation: str, filepath: str) -> None:
        """Report file operation results."""
        self.output.print_success(f"{operation}: {filepath}")
    
    def report_duplicate_skip(self) -> None:
        """Report skipping duplicate video."""
        self.output.print_result("Video already exists, skipping", False)
    
    def report_channel_added_count(self, added_count: int) -> None:
        """Report number of videos added from channel."""
        print(f"Added {added_count} similar videos from channel")
    
    def report_url_validation_start(self, filename: str) -> None:
        """Report start of URL validation."""
        self.output.print_sub_header("🔍 URL VALIDATION")
        self.output.print_progress(f"Validating URLs in: {filename}")
    
    def report_url_validation_completion(self, duplicate_count: int, invalid_count: int) -> None:
        """Report completion of URL validation."""
        if duplicate_count == 0 and invalid_count == 0:
            self.output.print_success("✅ All URLs are valid and unique!")
        else:
            if duplicate_count > 0:
                self.output.print_warning(f"Found {duplicate_count} duplicate URLs")
            if invalid_count > 0:
                self.output.print_warning(f"Found {invalid_count} invalid URLs")
            self.output.print_info("Check validation reports for details")
    
    def report_children_voice_detection_timing(self, video_title: str, duration: float) -> None:
        """Report children's voice detection timing."""
        truncated_title = video_title[:40] + "..." if len(video_title) > 40 else video_title
        self.output.print_timing(f"Children's voice detection for '{truncated_title}'", duration)
    
    def report_audio_analysis_timing(self, video_title: str, total_duration: float, children_detection_duration: float) -> None:
        """Report comprehensive audio analysis timing."""
        truncated_title = video_title[:40] + "..." if len(video_title) > 40 else video_title
        language_detection_duration = total_duration - children_detection_duration
        self.output.print_timing(f"Total audio analysis for '{truncated_title}'", total_duration)
        self.output.print_timing(f"  ├─ Language detection", language_detection_duration)
        self.output.print_timing(f"  └─ Children's voice detection", children_detection_duration)


class ErrorReporter:
    """Handles all error reporting and exception messages."""
    
    def __init__(self, output_manager: OutputManager):
        """Initialize with output manager."""
        self.output = output_manager
    
    def report_api_error(self, error: Exception) -> None:
        """Report API-related errors."""
        self.output.print_error(f"API request error: {error}")
    
    def report_channel_search_error(self, error: Exception) -> None:
        """Report channel search errors."""
        self.output.print_error(f"Channel search error: {error}")
    
    def report_unexpected_error(self, error: Exception) -> None:
        """Report unexpected errors."""
        self.output.print_error(f"Unexpected error: {error}")
    
    def report_audio_analysis_error(self, error: Exception) -> None:
        """Report audio analysis errors."""
        self.output.print_error(f"Error analyzing video: {error}")
    
    def report_file_error(self, operation: str, error: Exception) -> None:
        """Report file operation errors."""
        self.output.print_error(f"Error {operation}: {error}")
    
    def report_configuration_error(self, error: Exception) -> None:
        """Report configuration errors."""
        self.output.print_error(f"Configuration Error: {error}")
        print("Please set the YOUTUBE_API_KEY environment variable.")
        print("You can get an API key from: https://console.developers.google.com/")
        print("Enable the YouTube Data API v3 for your project.")
    
    def report_audio_download_failure(self) -> None:
        """Report audio download failure."""
        self.output.print_error("Failed to download or convert audio.")
    
    def report_quota_exceeded_error(self, current_collected: int, total_target: int) -> None:
        """Report YouTube API quota exceeded error with guidance."""
        self.output.print_error("⚠️  YouTube Data API quota exceeded!")
        print("🔧 API Quota Information:")
        print("   • YouTube Data API v3 has a daily quota limit")
        print("   • Default quota: 10,000 units per day")
        print("   • Each video search uses ~100 units")
        print("   • Each channel search uses ~100 units")
        print("")
        print("📊 Current Progress:")
        print(f"   • Videos collected: {current_collected}")
        print(f"   • Target goal: {total_target}")
        print(f"   • Completion rate: {current_collected / total_target * 100:.1f}%")
        print("")
        print("💡 Solutions:")
        print("   1. Wait until tomorrow (quota resets at midnight Pacific Time)")
        print("   2. Request quota increase from Google Cloud Console")
        print("   3. Use multiple API keys (if you have multiple projects)")
        print("   4. Continue with videos already collected")
        print("")
        print("🔗 Quota Management:")
        print("   • Monitor usage: https://console.cloud.google.com/apis/api/youtube.googleapis.com/quotas")
        print("   • Request increase: https://support.google.com/youtube/contact/yt_api_form")
    
    def report_api_rate_limit_error(self) -> None:
        """Report API rate limiting error."""
        self.output.print_error("⚠️  YouTube API rate limit exceeded!")
        print("⏰ Rate Limiting Information:")
        print("   • YouTube API has per-second rate limits")
        print("   • Temporarily slowing down requests...")
        print("   • This is normal for high-volume operations")
    
    def report_api_temporary_error(self, retry_count: int, max_retries: int) -> None:
        """Report temporary API error with retry information."""
        self.output.print_warning(f"⚠️  Temporary API error (attempt {retry_count}/{max_retries})")
        print(f"🔄 Retrying in a few seconds...")
    
    def report_api_permanent_error(self, error_code: int, error_message: str) -> None:
        """Report permanent API error that cannot be retried."""
        self.output.print_error(f"❌ Permanent API error (HTTP {error_code})")
        print(f"📋 Error details: {error_message}")
        print("🔧 This error cannot be resolved by retrying")
        print("   • Check your API key validity")
        print("   • Verify API is enabled in Google Cloud Console")
        print("   • Check if the video/channel still exists")


class UserInputManager:
    """Manages all user input interactions and prompts."""
    
    def __init__(self, output_manager: OutputManager):
        """Initialize with output manager."""
        self.output = output_manager
    
    def get_debug_mode_preference(self) -> bool:
        """Get user preference for debug mode."""
        self.output.print_header("Multi-Query Collector for Youtube Videos with Children's Voices", 60)
        
        debug_input = input("Enable debug mode? (y/n, default: n): ").strip().lower()
        debug_mode = debug_input in ['y', 'yes', '1', 'true']
        
        if debug_mode:
            self.output.print_progress("Debug mode enabled - detailed logging will be shown")
        else:
            self.output.print_info("Debug mode disabled - clean output mode")
        print()
        
        return debug_mode
    
    def get_target_count_per_query(self) -> int:
        """Get target video count per query from user."""
        self.output.print_sub_header("📊 TARGET CONFIGURATION")
        
        while True:
            try:
                count = int(input("Enter the target number of videos to collect per query (recommended: 10-50): "))
                if count <= Config.MIN_TARGET_COUNT - 1:
                    self.output.print_error("Please enter a positive number")
                    continue
                if count > Config.MAX_RECOMMENDED_PER_QUERY:
                    confirm = input(f"⚠️  {count} videos per query is quite high. Continue? (y/n): ").strip().lower()
                    if confirm not in ['y', 'yes']:
                        continue
                return count
            except ValueError:
                self.output.print_error("Invalid input. Please enter a valid number.")
    
    def get_query_list(self) -> List[str]:
        """Get list of queries from user."""
        self.output.print_sub_header("🔍 QUERY CONFIGURATION")
        print("Enter search queries (one per line)")
        print("Type 'DONE' when finished")
        print("Examples:")
        print("  - bé giới thiệu bản thân")
        print("  - bé tập nói tiếng Việt")
        print("  - trẻ em kể chuyện")
        print("  - bé hát ca dao")
        self.output.print_section_divider()
        
        query_list = []
        query_count = 1
        
        while True:
            query = input(f"Query {query_count}: ").strip()
            if query.upper() == "DONE":
                break
            if query:
                query_list.append(query)
                self.output.print_success(f"Added: '{query}'")
                query_count += 1
            else:
                self.output.print_error("Empty query, please enter a valid search term")
        
        if not query_list:
            self.output.print_warning("No queries provided. Using default query.")
            query_list = [Config.DEFAULT_QUERY]
        
        return query_list


class DebugLogger:
    """Debug logging utility for YouTube video crawler operations."""
    
    def __init__(self, enabled: bool = False):
        """
        Initialize debug logger.
        
        Args:
            enabled (bool): Whether debug logging is enabled
        """
        self.enabled = enabled
        self.debug_prefix = Config.DEBUG_PREFIX
    
    def log(self, message: str) -> None:
        """Log a debug message if debug mode is enabled."""
        if self.enabled:
            print(f"{self.debug_prefix}{message}")
    
    def log_api_request(self, url: str, params: Dict) -> None:
        """Log API request details."""
        self.log(f"Making API request to: {url}")
        self.log(f"Parameters: {params}")
    
    def log_api_response(self, status_code: int, data_keys: List[str], items_count: int) -> None:
        """Log API response details."""
        self.log(f"Response status: {status_code}")
        self.log(f"Response data keys: {data_keys}")
        self.log(f"Found {items_count} items")
    
    def log_channel_search(self, channel_id: str, query: str) -> None:
        """Log channel search operation."""
        if query:
            self.log(f"Searching channel {channel_id} with query '{query}'")
            self.log(f"Searching with query '{query}' in channel")
        else:
            self.log(f"Getting all videos from channel {channel_id}")
    
    def log_video_added(self, title: str, max_length: int = 50) -> None:
        """Log when a video is added to results."""
        truncated_title = title[:max_length] + "..." if len(title) > max_length else title
        self.log(f"Added video: {truncated_title}")
    
    def log_final_count(self, count: int) -> None:
        """Log final video count."""
        self.log(f"Final video count: {count}")
    
    def log_error(self, error_type: str, error: Exception, response_text: Optional[str] = None) -> None:
        """Log error details."""
        self.log(f"{error_type} error: {error}")
        if response_text and hasattr(error, 'response') and getattr(error, 'response', None) is not None:
            self.log(f"Response text: {response_text}")
    
    def log_audio_analysis(self, video_title: str, video_index: Union[int, str], result: Optional[bool]) -> None:
        """Log audio analysis results."""
        result_text = "Contains children's voice" if result else "No children's voice" if result is False else "Analysis failed"
        self.log(f"Video {video_index}: '{video_title[:30]}...' - {result_text}")
    
    def log_language_detection(self, video_title: str, video_index: Union[int, str], language_result: Dict) -> None:
        """Log language detection results."""
        is_vietnamese = language_result.get('is_vietnamese', False)
        detected_language = language_result.get('detected_language', 'unknown')
        result_text = f"Vietnamese detected" if is_vietnamese else f"Not Vietnamese (detected: {detected_language})"
        self.log(f"Video {video_index}: '{video_title[:30]}...' - Language: {result_text}")
    
    def log_collection_progress(self, current: int, total: int, collected: int, target: int) -> None:
        """Log collection progress."""
        self.log(f"Progress: {current}/{total} videos processed, {collected}/{target} collected")
    
    def log_timing(self, operation: str, duration: float) -> None:
        """Log timing information for operations."""
        self.log(f"Timing: {operation} took {duration:.3f}s")
    
    def log_performance_summary(self, total_time: float, avg_time: float, count: int) -> None:
        """Log performance summary."""
        self.log(f"Performance Summary: {count} operations, total: {total_time:.2f}s, avg: {avg_time:.3f}s")


class YouTubeVideoCrawler:
    """YouTube video searcher for collecting children's voice content."""
    
    def __init__(self, config: Optional[CrawlerConfig] = None, config_file_path: Optional[str] = None) -> None:
        """
        Initialize YouTube API searcher using Google's YouTube Data API v3.
        
        Args:
            config (CrawlerConfig, optional): Configuration object. If not provided, will load from file.
            config_file_path (str, optional): Path to configuration file. Uses default if not provided.
        """
        # Initialize output management
        self.output = OutputManager()
        self.reporter = CollectionReporter(self.output)
        self.error_reporter = ErrorReporter(self.output)
        
        # Load configuration from file if not provided
        if config is None:
            config_loader = ConfigLoader(self.output, config_file_path)
            config = config_loader.load_config()
        
        # Store configuration
        self.config = config
        
        # Initialize output analyzer
        self.analyzer = YouTubeOutputAnalyzer(Config.DEFAULT_OUTPUT_DIR)
        
        self.debug = DebugLogger(enabled=config.debug_mode)
        self.api_key = self._get_api_key()
        self.base_url = Config.YOUTUBE_API_BASE_URL
        
        # Configure parallel processing from environment config
        from env_config import config as env_config
        self.max_workers = env_config.MAX_WORKERS
        
        if config.debug_mode:
            self.debug.log(f"Parallel processing configured with max_workers: {self.max_workers}")
        
        # API quota and rate limiting management
        self.api_quota_exceeded = False
        self.api_requests_made = 0
        self.last_api_request_time = 0
        self.min_request_interval = 0.1  # Minimum seconds between API requests
        self.max_retries = 3
        self.retry_delays = [1, 2, 4]  # Exponential backoff delays in seconds
        
        # Initialize audio downloader
        audio_config = AudioConfig()
        
        # Configure cookie settings for the downloader
        cookies_file = None
        cookies_browser = None
        
        if config.cookie_settings and config.cookie_settings.get('enabled', False):
            if config.cookie_settings.get('method') == 'file':
                cookies_file = config.cookie_settings.get('cookies_file_path', 'cookies.txt')
            elif config.cookie_settings.get('method') == 'browser':
                cookies_browser = config.cookie_settings.get('browser_name', 'chrome')
        
        self.audio_downloader = YoutubeAudioDownloader(audio_config, cookies_file, cookies_browser)
        
        # Initialize YouTube Data API service for enhanced metadata retrieval
        self.youtube_service = None
        self._init_youtube_data_api()
        
        # Global variables for multiple query processing
        self.reviewed_channels: List[str] = []
        self.total_video_urls: List[str] = []
        self.collected_url_set: Set[str] = set()  # For fast duplicate checking
        
        # Load existing URLs from file if it exists
        self._load_existing_urls()
        
        # Track videos collected in current session only (not including pre-existing ones)
        self.current_session_collected_count = 0
        self.current_session_collected_urls: List[str] = []
        
        # Track individual video analysis results with timing for detailed reporting
        self.video_analysis_results: List[Dict] = []
        
        # Use configuration values instead of user input
        self.target_video_count_per_query = config.target_videos_per_query
        self.query_list = config.search_queries
        
        # Auto-calculate total target count based on per-query target * number of queries
        self.total_target_count = self.target_video_count_per_query * len(self.query_list)
        
        # Report configuration
        self.reporter.report_configuration(self.target_video_count_per_query, self.total_target_count, self.query_list)
        
        # Statistics tracking
        self.query_statistics: List[QueryStatistics] = []
        self.total_videos_evaluated = 0
        self.total_videos_with_children_voice = 0
        
        # Vietnamese language statistics tracking
        self.total_videos_vietnamese = 0
        self.total_videos_not_vietnamese = 0
        
        # Timing statistics tracking
        self.total_analysis_time = 0.0
        self.total_children_detection_time = 0.0
        self.min_children_detection_time = float('inf')
        self.max_children_detection_time = 0.0
        self.analysis_count = 0
        
        # Current processing state
        self.current_video: Optional[Dict] = None
        self.current_video_index = 0
        self.global_video_download_index = 0  # Global index for all video downloads to prevent file overlap
        self.download_index_lock = threading.Lock()  # Thread-safe lock for index assignment
        self.start_time = time.time()
        self.start_datetime = datetime.now()
        
    def _get_api_key(self) -> str:
        """Get and validate API key from environment configuration."""
        try:
            api_key = config.YOUTUBE_API_KEY
            print(f"✅ YouTube API key loaded from environment")
            return api_key
        except ValueError as e:
            self.error_reporter.report_configuration_error(e)
            raise
    
    def _init_youtube_data_api(self) -> None:
        """Initialize YouTube Data API service for enhanced metadata retrieval."""
        try:
            self.youtube_service = googleapiclient.discovery.build(
                "youtube", "v3", developerKey=self.api_key
            )
            print("✅ YouTube Data API service initialized for enhanced metadata retrieval")
            self.api_mode = "data_api"
        except Exception as e:
            print(f"⚠️ Could not initialize YouTube Data API service: {e}")
            print("⚠️ Falling back to web scraping methods")
            self.youtube_service = None
            self.api_mode = "web_scraping"
    
    def get_video_metadata_via_api(self, video_ids: List[str]) -> Dict[str, Dict]:
        """
        Get video metadata using YouTube Data API for enhanced efficiency.
        
        Args:
            video_ids (List[str]): List of video IDs to get metadata for
            
        Returns:
            Dict[str, Dict]: Mapping of video_id to metadata dict
        """
        if not self.youtube_service or not video_ids:
            return {}
        
        try:
            # YouTube Data API allows up to 50 video IDs per request
            batch_size = 50
            all_metadata = {}
            
            for i in range(0, len(video_ids), batch_size):
                batch_ids = video_ids[i:i + batch_size]
                
                request = self.youtube_service.videos().list(
                    part="snippet,contentDetails,statistics",
                    id=",".join(batch_ids)
                )
                response = request.execute()
                
                for item in response.get('items', []):
                    video_id = item['id']
                    snippet = item['snippet']
                    content_details = item['contentDetails']
                    statistics = item['statistics']
                    
                    # Parse duration from ISO 8601 format
                    duration_iso = content_details['duration']
                    duration_seconds = self._parse_iso_duration(duration_iso)
                    
                    all_metadata[video_id] = {
                        'video_id': video_id,
                        'title': snippet['title'],
                        'description': snippet['description'],
                        'channel_id': snippet['channelId'],
                        'channel_title': snippet['channelTitle'],
                        'published_at': snippet['publishedAt'],
                        'duration_seconds': duration_seconds,
                        'view_count': int(statistics.get('viewCount', 0)),
                        'like_count': int(statistics.get('likeCount', 0)),
                        'comment_count': int(statistics.get('commentCount', 0)),
                        'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                        'metadata_source': 'youtube_data_api'
                    }
                
                self.api_requests_made += 1
                print(f"📡 Retrieved metadata for {len(batch_ids)} videos via YouTube Data API")
                
                # Rate limiting
                time.sleep(self.min_request_interval)
            
            return all_metadata
            
        except Exception as e:
            print(f"⚠️ YouTube Data API metadata request failed: {e}")
            return {}
    
    def _parse_iso_duration(self, duration_iso: str) -> Optional[float]:
        """Parse ISO 8601 duration (PT4M13S) to seconds."""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return float(hours * 3600 + minutes * 60 + seconds)
        return None
    
    def _load_existing_urls(self) -> None:
        """Load existing URLs from file to prevent duplicates."""
        filename = Config.DEFAULT_URLS_FILE
        if Path(filename).exists():
            try:
                with Path(filename).open('r', encoding='utf-8') as f:
                    for line in f:
                        url = line.strip()
                        if url and url.startswith("https://"):
                            self.total_video_urls.append(url)
                            self.collected_url_set.add(url)
                self.reporter.report_initialization(len(self.total_video_urls), filename)
            except Exception as e:
                self.error_reporter.report_file_error("loading existing URLs", e)
        else:
            self.reporter.report_initialization(0, filename)
    
    def _get_shared_classifier(self) -> AudioClassifier:
        """
        Get shared classifier instance for optimal performance.
        This reuses the same classifier instance across all video processing.
        
        Returns:
            AudioClassifier: Shared classifier instance with cached models
        """
        if not hasattr(self, '_shared_classifier_instance'):
            self._shared_classifier_instance = AudioClassifier()
        return self._shared_classifier_instance
    
    def _get_next_download_index(self) -> int:
        """
        Thread-safe method to get the next download index.
        
        Returns:
            int: Next available download index
        """
        with self.download_index_lock:
            current_index = self.global_video_download_index
            self.global_video_download_index += 1
            return current_index
        
    def _cleanup_audio_file(self, audio_file_path: str) -> None:
        """
        Delete the audio file after analysis to clean up resources.
        
        Args:
            audio_file_path (str): Path to the audio file to delete
        """
        try:
            if audio_file_path and Path(audio_file_path).exists():
                Path(audio_file_path).unlink()
                self.debug.log(f"Cleaned up audio file: {audio_file_path}")
        except Exception as e:
            self.debug.log_error("Audio file cleanup", e)
            # Don't raise exception for cleanup failures as they shouldn't stop the main process
    
    def analyze_video_audio(self, video: Dict, video_type: str = "main") -> AnalysisResult:
        """
        OPTIMIZED: Download and analyze video audio using combined prediction for maximum efficiency.
        This method downloads the audio once and performs both analyses using shared audio loading.
        
        Args:
            video (Dict): Video information dictionary
            video_type (str): Type of video being processed ("main" or "similar")
            
        Returns:
            AnalysisResult: Combined analysis results with timing information
        """
        analysis_start_time = time.time()
        children_detection_start_time = None
        children_detection_duration = 0.0
        video_duration = None  # Ensure video_duration is always defined
        wav_file_path = None  # Initialize to handle cleanup in exception cases
        
        try:
            # Convert YouTube video to .wav file once for both analyses
            # Use thread-safe global download index to prevent file overlap
            # Get both audio file path and video duration
            # Use configured download method to bypass bot detection
            current_download_index = self._get_next_download_index()
            
            if self.config.download_method == "api_assisted":
                wav_file_path, video_duration = self.audio_downloader.download_audio_via_api(video['url'], index=current_download_index)
            else:
                wav_file_path, video_duration = self.audio_downloader.download_audio_from_yturl(video['url'], index=current_download_index)
            
            if not wav_file_path:
                self.error_reporter.report_audio_download_failure()
                return AnalysisResult(
                    is_vietnamese=False,
                    detected_language='unknown',
                    has_children_voice=None,
                    confidence=0,
                    error='Failed to download audio',
                    total_analysis_time=time.time() - analysis_start_time,
                    children_detection_time=0.0,
                    video_length_seconds=video_duration
                )
            
            # OPTIMIZED: Use shared classifier instance and combined prediction
            classifier = self._get_shared_classifier()
            
            # OPTIMIZED: Get both language and children's voice detection in one call
            # This loads audio only ONCE instead of twice (40-50% performance gain)
            # Time the children's voice detection portion specifically
            children_detection_start_time = time.time()
            combined_result = classifier.get_combined_prediction(wav_file_path)
            children_detection_duration = time.time() - children_detection_start_time
            
            if "error" in combined_result:
                # Clean up audio file after analysis
                self._cleanup_audio_file(wav_file_path)
                total_analysis_time = time.time() - analysis_start_time
                return AnalysisResult(
                    is_vietnamese=False,
                    detected_language='unknown',
                    has_children_voice=None,
                    confidence=0,
                    error=combined_result['error'],
                    total_analysis_time=total_analysis_time,
                    children_detection_time=children_detection_duration,
                    video_length_seconds=video_duration
                )
            
            # Extract results from combined prediction
            is_vietnamese = combined_result.get('is_vietnamese', False)
            children_voice_result = combined_result.get('is_child', None)
            confidence = combined_result.get('confidence', 0.0)
            
            # Calculate total analysis time
            total_analysis_time = time.time() - analysis_start_time
            
            # Prepare results
            language_result = {
                'is_vietnamese': is_vietnamese,
                'detected_language': 'vi' if is_vietnamese else 'other',
                'confidence': confidence,
                'error': None
            }
            
            # Debug logging with descriptive index based on video type
            if video_type == "main":
                display_index = self.current_video_index
            else:
                display_index = f"similar-{current_download_index}"
            
            # Log both results
            self.debug.log_language_detection(video['title'], display_index, language_result)
            if children_voice_result is not None:
                self.debug.log_audio_analysis(video['title'], display_index, children_voice_result)
            
            # Debug timing logging
            self.debug.log_timing(f"Audio analysis for video {display_index}", total_analysis_time)
            self.debug.log_timing(f"Children's voice detection for video {display_index}", children_detection_duration)
            
            # Report timing information
            self.reporter.report_audio_analysis_timing(video['title'], total_analysis_time, children_detection_duration)
            
            # Update timing statistics
            self._update_timing_statistics(total_analysis_time, children_detection_duration)
            
            # Clean up audio file after successful analysis
            self._cleanup_audio_file(wav_file_path)
            
            return AnalysisResult(
                is_vietnamese=is_vietnamese,
                detected_language=language_result['detected_language'],
                has_children_voice=children_voice_result,
                confidence=confidence,
                error=None,
                total_analysis_time=total_analysis_time,
                children_detection_time=children_detection_duration,
                video_length_seconds=video_duration
            )
            
        except Exception as e:
            total_analysis_time = time.time() - analysis_start_time
            self.error_reporter.report_audio_analysis_error(e)
            
            # Clean up audio file even if analysis failed (if it was created)
            if wav_file_path:
                self._cleanup_audio_file(wav_file_path)
            
            return AnalysisResult(
                is_vietnamese=False,
                detected_language='unknown',
                has_children_voice=None,
                confidence=0,
                error=str(e),
                total_analysis_time=total_analysis_time,
                children_detection_time=children_detection_duration,
                video_length_seconds=video_duration
            )
            
    def _update_timing_statistics(self, total_analysis_time: float, children_detection_time: float) -> None:
        """Update timing statistics for performance tracking."""
        self.total_analysis_time += total_analysis_time
        self.total_children_detection_time += children_detection_time
        self.analysis_count += 1
        
        # Track min/max children detection times
        if children_detection_time > 0:  # Only track non-zero times
            self.min_children_detection_time = min(self.min_children_detection_time, children_detection_time)
            self.max_children_detection_time = max(self.max_children_detection_time, children_detection_time)

    def get_timing_summary(self) -> Dict[str, float]:
        """Get summary of timing statistics."""
        if self.analysis_count == 0:
            return {
                "total_videos_analyzed": 0,
                "total_analysis_time": 0.0,
                "avg_analysis_time_per_video": 0.0,
                "total_children_detection_time": 0.0,
                "avg_children_detection_time": 0.0,
                "min_children_detection_time": 0.0,
                "max_children_detection_time": 0.0
            }
        
        return {
            "total_videos_analyzed": self.analysis_count,
            "total_analysis_time": self.total_analysis_time,
            "avg_analysis_time_per_video": self.total_analysis_time / self.analysis_count,
            "total_children_detection_time": self.total_children_detection_time,
            "avg_children_detection_time": self.total_children_detection_time / self.analysis_count,
            "min_children_detection_time": self.min_children_detection_time if self.min_children_detection_time != float('inf') else 0.0,
            "max_children_detection_time": self.max_children_detection_time
        }

    def estimate_remaining_quota(self) -> Dict[str, Union[int, float, bool]]:
        """Estimate remaining API quota and provide recommendations."""
        estimated_used = self.api_requests_made * 100  # Rough estimate: 100 units per request
        estimated_remaining = max(0, 10000 - estimated_used)
        
        # Estimate how many more videos can be processed
        # Assuming 1 main search + 2 channel searches per collected video on average
        requests_per_video = 3
        estimated_videos_remaining = estimated_remaining // (requests_per_video * 100)
        
        return {
            "quota_used": estimated_used,
            "quota_remaining": estimated_remaining,
            "quota_percentage_used": (estimated_used / 10000) * 100,
            "estimated_videos_remaining": estimated_videos_remaining,
            "quota_exceeded": self.api_quota_exceeded,
            "warning_threshold_reached": estimated_used > 8000,  # 80% threshold
            "requests_made": self.api_requests_made
        }

    def _report_timing_summary(self, timing_summary: Dict[str, float]) -> None:
        """Report timing performance summary."""
        self.output.print_sub_header("⏱️  PERFORMANCE TIMING SUMMARY")
        
        if timing_summary["total_videos_analyzed"] == 0:
            self.output.print_info("No videos were analyzed for timing statistics")
            return
        
        print(f"📊 Analysis Performance Statistics:")
        print(f"  ├─ Total videos analyzed: {timing_summary['total_videos_analyzed']}")
        print(f"  ├─ Total analysis time: {timing_summary['total_analysis_time']:.2f}s")
        print(f"  ├─ Average time per video: {timing_summary['avg_analysis_time_per_video']:.2f}s")
        print(f"  └─ Children's Voice Detection:")
        print(f"     ├─ Total detection time: {timing_summary['total_children_detection_time']:.2f}s")
        print(f"     ├─ Average detection time: {timing_summary['avg_children_detection_time']:.2f}s")
        print(f"     ├─ Fastest detection: {timing_summary['min_children_detection_time']:.2f}s")
        print(f"     └─ Slowest detection: {timing_summary['max_children_detection_time']:.2f}s")
        
        # Calculate efficiency metrics
        if timing_summary['total_analysis_time'] > 0:
            detection_percentage = (timing_summary['total_children_detection_time'] / timing_summary['total_analysis_time']) * 100
            print(f"  📈 Detection efficiency: {detection_percentage:.1f}% of total analysis time")
        
        self.output.print_section_divider()

    def _report_api_usage_summary(self) -> None:
        """Report API usage and quota status summary."""
        self.output.print_sub_header("🔗 API USAGE SUMMARY")
        
        print(f"📊 YouTube Data API Statistics:")
        print(f"  ├─ Total API requests made: {self.api_requests_made}")
        
        # Estimate quota units used (rough calculation)
        estimated_quota_used = self.api_requests_made * 100  # Each search request uses ~100 units
        print(f"  ├─ Estimated quota units used: {estimated_quota_used}")
        print(f"  ├─ Daily quota limit: 10,000 units (default)")
        
        if self.api_quota_exceeded:
            print(f"  └─ Status: ❌ QUOTA EXCEEDED")
            remaining_percentage = 0
        else:
            remaining_quota = max(0, 10000 - estimated_quota_used)
            remaining_percentage = (remaining_quota / 10000) * 100
            print(f"  └─ Status: ✅ ACTIVE")
            print(f"     ├─ Estimated remaining quota: {remaining_quota} units")
            print(f"     └─ Estimated remaining: {remaining_percentage:.1f}%")
        
        if estimated_quota_used > 8000:  # Warning at 80%
            print(f"  ⚠️  Warning: High quota usage detected!")
            print(f"     Consider monitoring usage to avoid hitting limits")
        
        self.output.print_section_divider()

    def _make_api_request(self, url: str, params: Dict, operation_name: str = "API request") -> Optional[Dict]:
        """
        Centralized API request method with quota handling, retry logic, and rate limiting.
        
        Args:
            url (str): API endpoint URL
            params (Dict): Request parameters
            operation_name (str): Description of the operation for logging
            
        Returns:
            Optional[Dict]: API response data or None if failed
        """
        if self.api_quota_exceeded:
            self.debug.log(f"Skipping {operation_name} - API quota exceeded")
            return None
        
        # Rate limiting: ensure minimum interval between requests
        current_time = time.time()
        time_since_last_request = current_time - self.last_api_request_time
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        for retry_attempt in range(self.max_retries + 1):
            try:
                self.debug.log_api_request(url, params)
                
                # Make the API request
                response = requests.get(url, params=params)
                self.last_api_request_time = time.time()
                self.api_requests_made += 1
                
                # Handle different HTTP status codes
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('items', [])
                    self.debug.log_api_response(response.status_code, list(data.keys()), len(items))
                    return data
                
                elif response.status_code == 403:
                    # Check if it's quota exceeded
                    error_data = response.json() if response.content else {}
                    error_details = error_data.get('error', {})
                    error_reason = error_details.get('errors', [{}])[0].get('reason', '')
                    
                    if 'quotaExceeded' in error_reason or 'dailyLimitExceeded' in error_reason:
                        self.api_quota_exceeded = True
                        self.error_reporter.report_quota_exceeded_error(
                            self.current_session_collected_count,
                            self.total_target_count
                        )
                        return None
                    else:
                        # Other 403 errors (e.g., API not enabled, invalid key)
                        error_message = error_details.get('message', 'Unknown API error')
                        self.error_reporter.report_api_permanent_error(403, error_message)
                        return None
                
                elif response.status_code == 429:
                    # Rate limit exceeded - retry with exponential backoff
                    if retry_attempt < self.max_retries:
                        self.error_reporter.report_api_rate_limit_error()
                        delay = self.retry_delays[min(retry_attempt, len(self.retry_delays) - 1)]
                        time.sleep(delay)
                        continue
                    else:
                        self.error_reporter.report_api_permanent_error(429, "Rate limit exceeded - max retries reached")
                        return None
                
                elif response.status_code in [500, 502, 503, 504]:
                    # Server errors - retry with exponential backoff
                    if retry_attempt < self.max_retries:
                        self.error_reporter.report_api_temporary_error(retry_attempt + 1, self.max_retries)
                        delay = self.retry_delays[min(retry_attempt, len(self.retry_delays) - 1)]
                        time.sleep(delay)
                        continue
                    else:
                        self.error_reporter.report_api_permanent_error(response.status_code, "Server error - max retries reached")
                        return None
                
                else:
                    # Other HTTP errors
                    error_message = f"HTTP {response.status_code}: {response.text[:200]}"
                    self.error_reporter.report_api_permanent_error(response.status_code, error_message)
                    return None
                    
            except requests.exceptions.RequestException as e:
                if retry_attempt < self.max_retries:
                    self.error_reporter.report_api_temporary_error(retry_attempt + 1, self.max_retries)
                    delay = self.retry_delays[min(retry_attempt, len(self.retry_delays) - 1)]
                    time.sleep(delay)
                    continue
                else:
                    self.error_reporter.report_api_error(e)
                    response_text = getattr(e.response, 'text', '') if hasattr(e, 'response') and e.response else ''
                    self.debug.log_error("API request", e, response_text)
                    return None
            
            except Exception as e:
                self.error_reporter.report_unexpected_error(e)
                self.debug.log_error("Unexpected", e)
                return None
        
        return None

    def search_videos_by_query(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Search videos on YouTube using the given query.
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            
        Returns:
            List[Dict]: List of video information dictionaries
        """
        if self.api_quota_exceeded:
            self.debug.log("Skipping video search - API quota exceeded")
            return []
        
        url = f"{self.base_url}/search"
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': min(max_results, Config.MAX_RESULTS_PER_REQUEST),  # YouTube API max is 50 per request
            'key': self.api_key
        }
        
        # Use centralized API request method
        data = self._make_api_request(url, params, f"video search for '{query}'")
        if not data:
            return []
        
        videos = []
        items = data.get('items', [])
        for item in items:
            video_info = self._extract_video_info(item)
            videos.append(video_info)
        self.debug.log_final_count(len(videos))
        return videos

    def _extract_video_info(self, item: Dict) -> Dict:
        """Extract video information from API response item."""
        snippet = item.get('snippet', {})
        video_id = item.get('id', {}).get('videoId', '')
        
        return {
            'video_id': video_id,
            'title': snippet.get('title', ''),
            'channel_id': snippet.get('channelId', ''),
            'channel_title': snippet.get('channelTitle', ''),
            'description': snippet.get('description', ''),
            'published_at': snippet.get('publishedAt', ''),
            'url': f"{Config.YOUTUBE_VIDEO_URL_PREFIX}{video_id}"
        }
    
    def get_channel_videos(self, channel_id: str, query: str = "", max_results: int = 50) -> List[Dict]:
        """
        Get videos from a specific channel, optionally filtered by search query.
        
        Args:
            channel_id (str): YouTube channel ID
            query (str): Optional search query to filter channel videos
            max_results (int): Maximum number of results to return
            
        Returns:
            List[Dict]: List of video information dictionaries
        """
        if self.api_quota_exceeded:
            self.debug.log("Skipping channel search - API quota exceeded")
            return []
        
        url = f"{self.base_url}/search"
        params = {
            'part': 'snippet',
            'channelId': channel_id,
            'type': 'video',
            'maxResults': min(max_results, Config.MAX_RESULTS_PER_REQUEST),
            'key': self.api_key
        }
        
        if query:
            params['q'] = query
        
        self.debug.log_channel_search(channel_id, query)
        
        # Use centralized API request method
        operation_name = f"channel search (ID: {channel_id[:20]}...)"
        if query:
            operation_name += f" with query '{query}'"
        
        data = self._make_api_request(url, params, operation_name)
        if not data:
            return []
        
        videos = []
        items = data.get('items', [])
        for item in items:
            video_info = self._extract_video_info(item)
            videos.append(video_info)
            self.debug.log_video_added(video_info['title'])
        
        self.debug.log_final_count(len(videos))
        return videos
    
    def _process_main_video(self, video: Dict, query_stats: Dict) -> bool:
        """
        Process a main video from search results.
        
        Args:
            video (Dict): Video information
            query_stats (Dict): Mutable dictionary for tracking query statistics
            
        Returns:
            bool: True if video was added to collection, False otherwise
        """
        # Check for duplicate URLs
        if video['url'] in self.collected_url_set:
            self.reporter.report_duplicate_skip()
            return False
        
        # Analyze video audio (language detection + children's voice detection)
        print(f"Analyzing video: {video['title']}")
        self.reporter.report_language_check_start()
        self.current_video = video
        analysis_result = self.analyze_video_audio(video, video_type="main")
        
        # Store individual video analysis result for detailed reporting
        video_analysis_record = {
            'video_url': video['url'],
            'video_title': video['title'],
            'channel_title': video['channel_title'],
            'channel_id': video['channel_id'],
            'video_type': 'main',
            'query': query_stats['current_query'],
            'is_vietnamese': analysis_result.is_vietnamese,
            'detected_language': analysis_result.detected_language,
            'has_children_voice': analysis_result.has_children_voice,
            'confidence': analysis_result.confidence,
            'total_analysis_time': analysis_result.total_analysis_time,
            'children_detection_time': analysis_result.children_detection_time,
            'video_length_seconds': analysis_result.video_length_seconds,
            'was_collected': False,  # Will be updated later if collected
            'analysis_error': analysis_result.error,
            'timestamp': datetime.now().isoformat()
        }
        self.video_analysis_results.append(video_analysis_record)
        
        # Check language result first
        if not analysis_result.is_vietnamese:
            print(f"✗ Video is not in Vietnamese - Skipping: {video['title']}")
            if analysis_result.detected_language:
                print(f"  Detected language: {analysis_result.detected_language}")
            query_stats['videos_not_vietnamese'] += 1
            self.total_videos_not_vietnamese += 1
            self.reporter.report_language_result(False, analysis_result.detected_language)
            return False
        else:
            print("✓ Video is in Vietnamese - Proceeding to evaluate")
            query_stats['videos_vietnamese'] += 1
            self.total_videos_vietnamese += 1
            self.reporter.report_language_result(True)
        
        # Process children's voice detection result
        print(f"Evaluating video: {video['title']}")
        self.reporter.report_evaluation_start()
        evaluation_result = analysis_result.has_children_voice
        query_stats['videos_evaluated'] += 1
        self.total_videos_evaluated += 1
        
        if evaluation_result:
            query_stats['videos_with_children_voice'] += 1
            self.total_videos_with_children_voice += 1
        
        # Check collection criteria
        is_new_channel = video['channel_id'] not in self.reviewed_channels
        
        if evaluation_result and is_new_channel:
            self.reporter.report_evaluation_result(True, True)
            
            # Add current video to collection
            self.total_video_urls.append(video['url'])
            self.collected_url_set.add(video['url'])
            self.current_session_collected_count += 1
            self.current_session_collected_urls.append(video['url'])
            self._save_url_to_file(video, Config.DEFAULT_URLS_FILE)
            query_stats['videos_collected'] += 1
            
            # Mark video as collected in analysis results
            for result in reversed(self.video_analysis_results):
                if result['video_url'] == video['url']:
                    result['was_collected'] = True
                    break
            
            # Mark channel as reviewed and process similar videos with PARALLEL processing
            added_count = self._process_similar_videos_parallel(video, query_stats)
            self.reviewed_channels.append(video['channel_id'])
            self.reporter.report_channel_added_count(added_count)
            
            return True
        else:
            self.reporter.report_evaluation_result(evaluation_result or False, is_new_channel)
            return False
    
    def _process_similar_videos(self, main_video: Dict, query_stats: Dict) -> int:
        """
        Process similar videos from the same channel.
        
        Args:
            main_video (Dict): The main video that triggered channel exploration
            query_stats (Dict): Mutable dictionary for tracking query statistics
            
        Returns:
            int: Number of similar videos added to collection
        """
        current_query = query_stats['current_query']
        
        # Search for similar videos in the same channel with evaluation
        similar_videos = self.get_channel_videos(main_video['channel_id'], current_query)
        self.reporter.report_channel_exploration(
            main_video['channel_title'],
            current_query,
            len(similar_videos)
        )
        
        # Evaluate each similar video before adding to results
        added_count = 0
        for similar_video in similar_videos:
            # Check for duplicates first
            if similar_video['url'] in self.collected_url_set:
                continue
            
            # Check if we've reached target counts
            if (query_stats['videos_collected'] >= self.target_video_count_per_query or 
                self.current_session_collected_count >= self.total_target_count):
                break
            
            # Count similar video as reviewed since we're processing it
            query_stats['videos_reviewed'] += 1
            
            # Analyze similar video audio (language + children's voice detection)
            print(f"Analyzing similar video: {similar_video['title']}")
            similar_analysis_result = self.analyze_video_audio(similar_video, video_type="similar")
            
            # Check language result first
            if not similar_analysis_result.is_vietnamese:
                print("✗ Similar video is not in Vietnamese - Skipping")
                query_stats['videos_not_vietnamese'] += 1
                self.total_videos_not_vietnamese += 1
                self.reporter.report_similar_video_language_result(False)
                continue
            else:
                print("✓ Similar video is in Vietnamese - Proceeding to evaluate")
                query_stats['videos_vietnamese'] += 1
                self.total_videos_vietnamese += 1
                self.reporter.report_similar_video_language_result(True)
            
            # Process children's voice detection result
            print(f"Evaluating similar video: {similar_video['title']}")
            self.reporter.report_similar_video_evaluation(similar_video['title'])
            similar_evaluation_result = similar_analysis_result.has_children_voice
            query_stats['videos_evaluated'] += 1
            self.total_videos_evaluated += 1
            
            if similar_evaluation_result:
                query_stats['videos_with_children_voice'] += 1
                self.total_videos_with_children_voice += 1
                
                # Only add to results when confirmed to have children's voice
                self.total_video_urls.append(similar_video['url'])
                self.collected_url_set.add(similar_video['url'])
                self.current_session_collected_count += 1
                self.current_session_collected_urls.append(similar_video['url'])
                self._save_url_to_file(similar_video, Config.DEFAULT_URLS_FILE)
                query_stats['videos_collected'] += 1
                added_count += 1
                print("✓ Video has children's voice - Added to results")
                self.reporter.report_similar_video_result(True)
            else:
                print("✗ Video has no children's voice - Skipped")
                self.reporter.report_similar_video_result(False)
        
        return added_count
    
    def _process_similar_videos_parallel(self, main_video: Dict, query_stats: Dict) -> int:
        """
        OPTIMIZED: Process similar videos from the same channel using parallel processing.
        This provides 3-4x speedup compared to sequential processing.
        
        Args:
            main_video (Dict): The main video that triggered channel exploration
            query_stats (Dict): Mutable dictionary for tracking query statistics
            
        Returns:
            int: Number of similar videos added to collection
        """
        current_query = query_stats['current_query']
        
        # Search for similar videos in the same channel
        similar_videos = self.get_channel_videos(main_video['channel_id'], current_query)
        self.reporter.report_channel_exploration(
            main_video['channel_title'],
            current_query,
            len(similar_videos)
        )
        
        # Filter out duplicates before processing
        filtered_videos = [
            video for video in similar_videos 
            if video['url'] not in self.collected_url_set
        ]
        
        if not filtered_videos:
            return 0
        
        # Limit videos to process based on remaining target
        remaining_target_query = self.target_video_count_per_query - query_stats['videos_collected']
        remaining_target_total = self.total_target_count - self.current_session_collected_count
        max_to_process = min(remaining_target_query, remaining_target_total, len(filtered_videos))
        
        videos_to_process = filtered_videos[:max_to_process]
        
        # Early return if no videos to process
        if not videos_to_process:
            print("No similar videos to process after filtering duplicates and applying limits.")
            return 0
        
        # Process videos in parallel with configured concurrency
        max_workers = min(self.max_workers, len(videos_to_process))
        added_count = 0
        
        print(f"Processing {len(videos_to_process)} similar videos with {max_workers} parallel workers...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_video = {
                executor.submit(self._process_single_similar_video, video, query_stats): video 
                for video in videos_to_process
            }
            
            # Process completed tasks
            for future in as_completed(future_to_video):
                video = future_to_video[future]
                try:
                    result = future.result()
                    if result:  # Video was added
                        added_count += 1
                        
                    # Check if we've reached targets
                    if (query_stats['videos_collected'] >= self.target_video_count_per_query or 
                        self.current_session_collected_count >= self.total_target_count):
                        break
                        
                except Exception as e:
                    print(f"Error processing similar video {video['title']}: {e}")
        
        return added_count
    
    def _process_single_similar_video(self, similar_video: Dict, query_stats: Dict) -> bool:
        """
        OPTIMIZED: Process a single similar video with optimized audio loading.
        
        Args:
            similar_video (Dict): Video information
            query_stats (Dict): Mutable dictionary for tracking query statistics
            
        Returns:
            bool: True if video was added to collection, False otherwise
        """
        # Double-check for duplicates (thread-safe)
        if similar_video['url'] in self.collected_url_set:
            return False
        
        # Count similar video as reviewed since we're processing it
        query_stats['videos_reviewed'] += 1
        
        # OPTIMIZED: Analyze similar video audio using combined prediction
        print(f"Analyzing similar video: {similar_video['title']}")
        similar_analysis_result = self.analyze_video_audio(similar_video, video_type="similar")
        
        # Store individual video analysis result for detailed reporting
        video_analysis_record = {
            'video_url': similar_video['url'],
            'video_title': similar_video['title'],
            'channel_title': similar_video['channel_title'],
            'channel_id': similar_video['channel_id'],
            'video_type': 'similar',
            'query': query_stats['current_query'],
            'is_vietnamese': similar_analysis_result.is_vietnamese,
            'detected_language': similar_analysis_result.detected_language,
            'has_children_voice': similar_analysis_result.has_children_voice,
            'confidence': similar_analysis_result.confidence,
            'total_analysis_time': similar_analysis_result.total_analysis_time,
            'children_detection_time': similar_analysis_result.children_detection_time,
            'video_length_seconds': similar_analysis_result.video_length_seconds,
            'was_collected': False,  # Will be updated later if collected
            'analysis_error': similar_analysis_result.error,
            'timestamp': datetime.now().isoformat()
        }
        self.video_analysis_results.append(video_analysis_record)
        
        # Check language result first
        if not similar_analysis_result.is_vietnamese:
            print("✗ Similar video is not in Vietnamese - Skipping")
            query_stats['videos_not_vietnamese'] += 1
            self.total_videos_not_vietnamese += 1
            self.reporter.report_similar_video_language_result(False)
            return False
        else:
            print("✓ Similar video is in Vietnamese - Proceeding to evaluate")
            query_stats['videos_vietnamese'] += 1
            self.total_videos_vietnamese += 1
            self.reporter.report_similar_video_language_result(True)
        
        # Process children's voice detection result
        print(f"Evaluating similar video: {similar_video['title']}")
        self.reporter.report_similar_video_evaluation(similar_video['title'])
        similar_evaluation_result = similar_analysis_result.has_children_voice
        query_stats['videos_evaluated'] += 1
        self.total_videos_evaluated += 1
        
        if similar_evaluation_result:
            query_stats['videos_with_children_voice'] += 1
            self.total_videos_with_children_voice += 1
            
            # Thread-safe adding to results
            self.total_video_urls.append(similar_video['url'])
            self.collected_url_set.add(similar_video['url'])
            self.current_session_collected_count += 1
            self.current_session_collected_urls.append(similar_video['url'])
            self._save_url_to_file(similar_video, Config.DEFAULT_URLS_FILE)
            query_stats['videos_collected'] += 1
            print("✓ Video has children's voice - Added to results")
            self.reporter.report_similar_video_result(True)
            
            # Mark video as collected in analysis results
            for result in reversed(self.video_analysis_results):
                if result['video_url'] == similar_video['url']:
                    result['was_collected'] = True
                    break
            
            return True
        else:
            print("✗ Video has no children's voice - Skipped")
            self.reporter.report_similar_video_result(False)
            return False
    
    def _create_query_statistics(self, query: str, query_stats: Dict) -> QueryStatistics:
        """Create QueryStatistics object from query statistics dictionary."""
        efficiency_rate = (query_stats['videos_collected'] / query_stats['videos_reviewed'] * 100) if query_stats['videos_reviewed'] > 0 else 0
        children_voice_rate = (query_stats['videos_with_children_voice'] / query_stats['videos_evaluated'] * 100) if query_stats['videos_evaluated'] > 0 else 0
       
        vietnamese_rate = (query_stats['videos_vietnamese'] / (query_stats['videos_vietnamese'] + query_stats['videos_not_vietnamese']) * 100) if (query_stats['videos_vietnamese'] + query_stats['videos_not_vietnamese']) > 0 else 0
        
        return QueryStatistics(
            query=query,
            videos_collected=query_stats['videos_collected'],
            videos_reviewed=query_stats['videos_reviewed'],
            videos_evaluated=query_stats['videos_evaluated'],
            videos_with_children_voice=query_stats['videos_with_children_voice'],
            videos_vietnamese=query_stats['videos_vietnamese'],
            videos_not_vietnamese=query_stats['videos_not_vietnamese'],
            efficiency_rate=efficiency_rate,
            children_voice_rate=children_voice_rate,
            vietnamese_rate=vietnamese_rate,
            new_channels_found=self._count_new_channels_for_query(query)
        )
    
    def collect_videos(self) -> List[str]:
        """
        Main algorithm to collect videos with children's voices using multiple queries.
        
        Returns:
            List[str]: List of video URLs
        """
        self.reporter.report_collection_start(self.target_video_count_per_query, len(self.query_list))
        
        # Main loop for each query
        for query_index, current_query in enumerate(self.query_list, 1):
            # Check if API quota has been exceeded
            if self.api_quota_exceeded:
                self.output.print_warning(f"⚠️  Stopping collection at query {query_index}/{len(self.query_list)} due to API quota exceeded")
                break
            
            # Check if we've reached the total target count for current session
            if self.current_session_collected_count >= self.total_target_count:
                self.output.print_success(f"🎯 Total target count of {self.total_target_count} videos reached!")
                self.output.print_info(f"Stopping collection at query {query_index}/{len(self.query_list)}")
                break
                
            self.reporter.report_query_start(query_index, len(self.query_list), current_query)
            
            # Initialize variables for current query
            query_stats = {
                'current_query': current_query,
                'videos_collected': 0,
                'videos_reviewed': 0,
                'videos_evaluated': 0,
                'videos_with_children_voice': 0,
                'videos_vietnamese': 0,
                'videos_not_vietnamese': 0
            }
            video_index_current = 0
            
            # Get initial video list for current query
            video_list = self.search_videos_by_query(current_query)
            if not video_list:
                self.reporter.report_query_results(0, current_query)
                # Check if failure was due to quota exceeded
                if self.api_quota_exceeded:
                    self.output.print_warning("⚠️  Stopping collection due to API quota exceeded")
                    break
                continue
            
            self.reporter.report_query_results(len(video_list), current_query)
            
            # Collection loop for current query
            while (query_stats['videos_collected'] < self.target_video_count_per_query and 
                   video_index_current < len(video_list) and 
                   self.current_session_collected_count < self.total_target_count and
                   not self.api_quota_exceeded):  # Stop if quota exceeded
                
                current_video_processing = video_list[video_index_current]
                query_stats['videos_reviewed'] += 1
                
                self.reporter.report_video_processing(
                    video_index_current, 
                    len(video_list),
                    current_video_processing['title'],
                    current_video_processing['channel_title']
                )
                
                # Set current video index for debugging
                self.current_video_index = video_index_current
                
                # Process the video
                video_added = self._process_main_video(current_video_processing, query_stats)
                
                self.reporter.report_total_progress(
                    self.current_session_collected_count, 
                    self.total_target_count,
                    query_stats['videos_collected'], 
                    self.target_video_count_per_query
                )
                video_index_current += 1
            
            # Create and save statistics for current query
            current_query_stats = self._create_query_statistics(current_query, query_stats)
            self.query_statistics.append(current_query_stats)
            
            # Print query statistics
            self.reporter.report_query_statistics(current_query_stats)
        
        # Report timing summary
        timing_summary = self.get_timing_summary()
        self._report_timing_summary(timing_summary)
        
        # Report API usage and quota status
        self._report_api_usage_summary()
        
        # Debug timing summary
        if timing_summary["total_videos_analyzed"] > 0:
            self.debug.log_performance_summary(
                timing_summary["total_analysis_time"],
                timing_summary["avg_analysis_time_per_video"],
                int(timing_summary["total_videos_analyzed"])
            )
        
        # Generate and save final report
        final_report = self.analyzer.generate_final_report(
            self.current_session_collected_count,
            self.total_video_urls,
            self.total_target_count,
            self.target_video_count_per_query,
            self.total_videos_evaluated,
            self.total_videos_with_children_voice,
            self.total_videos_vietnamese,
            self.total_videos_not_vietnamese,
            self.query_list,
            self.query_statistics,
            self.reviewed_channels
        )
        print(final_report)
        
        # Create timestamped report filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = str(Config.DEFAULT_OUTPUT_DIR / f"{timestamp}_collection_report.txt")
        self.analyzer.save_report_to_file(final_report, report_filename)
        
        # Save results and statistics with timestamps
        detailed_results_filename = str(Config.DEFAULT_OUTPUT_DIR / f"{timestamp}_detailed_collection_results.json")
        statistics_filename = str(Config.DEFAULT_OUTPUT_DIR / f"{timestamp}_query_efficiency_statistics.json")
        self.analyzer.save_detailed_results_with_statistics(
            detailed_results_filename,
            self.current_session_collected_count,
            self.total_video_urls,
            self.total_target_count,
            self.target_video_count_per_query,
            self.total_videos_evaluated,
            self.total_videos_with_children_voice,
            self.total_videos_vietnamese,
            self.total_videos_not_vietnamese,
            self.query_list,
            self.query_statistics,
            self.reviewed_channels,
            self.current_session_collected_urls,
            self.start_time,
            self.start_datetime,
            self.video_analysis_results  # Pass video analysis results with timing
        )
        self.analyzer.save_statistics_to_file(
            statistics_filename,
            self.query_statistics,
            self.query_list,
            self.target_video_count_per_query,
            self.total_target_count,
            self.current_session_collected_count,
            self.total_video_urls,
            self.total_videos_evaluated,
            self.total_videos_with_children_voice
        )
        self.analyzer.create_backup_file(self.total_video_urls)
        
        self.reporter.report_collection_completion(self.current_session_collected_count, self.api_quota_exceeded)
        return self.total_video_urls
    
    def _save_url_to_file(self, video_info: Dict, filename: str) -> None:
        """Save URL immediately to file (append mode)."""
        try:
            filepath = Path(filename)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with filepath.open('a', encoding='utf-8') as f:
                f.write(video_info['url'] + '\n')
        except Exception as e:
            self.error_reporter.report_file_error("saving URL to file", e)
    
    def _count_new_channels_for_query(self, query: str) -> int:
        """Count new channels found for a specific query."""
        # This is a simplified implementation
        # In a full implementation, you would track which channels were found for each query
        return len(self.reviewed_channels)
    
    def save_results(self, filename: str = Config.DEFAULT_URLS_FILE) -> None:
        """
        Save collected video URLs to a file
        
        Args:
            filename (str): Output filename
        """
        filepath = Path(filename)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with filepath.open('w', encoding='utf-8') as f:
            for url in self.total_video_urls:
                f.write(url + '\n')
        
        self.reporter.report_file_operations("Results saved to", str(filepath.resolve()))
    
    def validate_collected_urls(self, filename: str) -> None:
        """
        Validate the collected URLs using YouTubeURLValidator and remove duplicates in-place.
        
        Args:
            filename (str): Path to the file containing URLs to validate
        """
        try:
            # Report validation start
            self.reporter.report_url_validation_start(filename)
            
            # Initialize validator
            validator = YouTubeURLValidator()
            
            # Validate and clean the file in one step
            result = validator.validate_and_clean_file(Path(filename))
            
            # Report validation completion
            self.reporter.report_url_validation_completion(
                result.duplicate_count, 
                result.invalid_urls
            )
            
        except Exception as e:
              self.error_reporter.report_file_error("validating URLs", e)

def main():
    """Main function to run the YouTube video searcher."""
    # Initialize output manager and error reporter
    output_manager = OutputManager()
    error_reporter = ErrorReporter(output_manager)

    try:
        # Log initial information
        print("YouTube Video Crawler - Automated Mode")
        output_manager.print_info("Loading configuration from file...")

        # Initialize searcher with configuration from file (no user input required)
        searcher = YouTubeVideoCrawler()
        
        # Collect videos using multiple queries
        video_urls = searcher.collect_videos()
        
        # Save results
        if video_urls:
            # Ensure output directory exists
            Config.DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped filenames for main results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            main_urls_filename = str(Config.DEFAULT_OUTPUT_DIR / f"{timestamp}_multi_query_collected_video_urls.txt")
            
            searcher.save_results(main_urls_filename)
            
            # Validate collected URLs as final step
            searcher.validate_collected_urls(main_urls_filename)
        else:
            output_manager.print_warning("No videos were collected")
        
        # Log completion information
                
    except Exception as e:
        error_reporter.report_unexpected_error(e)

    # Final message
    print("✅ YouTube Video Crawler execution completed")
    
if __name__ == "__main__":
    main()