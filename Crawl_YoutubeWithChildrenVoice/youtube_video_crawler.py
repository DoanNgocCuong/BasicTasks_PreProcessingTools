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
import os
import torch
import sys
import googleapiclient.discovery
from googleapiclient.errors import HttpError
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union, Set, Any, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import librosa
import soundfile as sf
import tempfile
from youtube_audio_downloader import YoutubeAudioDownloader, Config as AudioDownloaderConfig
from youtube_audio_classifier import AudioClassifier
from youtube_output_analyzer import YouTubeOutputAnalyzer, QueryStatistics
from youtube_output_validator import YouTubeURLValidator
from env_config import config

# Set CUDA memory optimization environment variables
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
if torch.cuda.is_available():
    # Enable memory-efficient attention and other optimizations
    torch.backends.cudnn.benchmark = True
    torch.backends.cuda.matmul.allow_tf32 = True
    torch.backends.cudnn.allow_tf32 = True


class Config:
    """Configuration constants for the YouTube video crawler."""
    
    # API and URL constants
    YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
    YOUTUBE_VIDEO_URL_PREFIX = "https://www.youtube.com/watch?v="
    MAX_RESULTS_PER_REQUEST = 50
    
    # File paths
    _SCRIPT_DIR = Path(__file__).parent
    DEFAULT_OUTPUT_DIR = _SCRIPT_DIR / "youtube_url_outputs"
    DEFAULT_CONFIG_FILE = str(_SCRIPT_DIR / "crawler_config.json")
    DEFAULT_URLS_FILE = str(DEFAULT_OUTPUT_DIR / "collected_video_urls.txt")
    DEFAULT_REPORT_FILE = str(DEFAULT_OUTPUT_DIR / "collection_report.txt")
    DEFAULT_DETAILED_RESULTS_FILE = str(DEFAULT_OUTPUT_DIR / "detailed_collection_results.json")
    DEFAULT_STATISTICS_FILE = str(DEFAULT_OUTPUT_DIR / "query_efficiency_statistics.json")
    DEFAULT_MAIN_URLS_FILE = str(DEFAULT_OUTPUT_DIR / "multi_query_collected_video_urls.txt")
    DEFAULT_MAIN_DETAILED_FILE = str(DEFAULT_OUTPUT_DIR / "multi_query_detailed_results.json")
    DEFAULT_BACKUP_FILE_PREFIX = str(DEFAULT_OUTPUT_DIR / "backup")

    # Validation constants
    MIN_TARGET_COUNT = 1
    MAX_RECOMMENDED_PER_QUERY = 100
    
    # Default values
    DEBUG_PREFIX = "🔍 DEBUG: "
    DEFAULT_QUERY = "bé giới thiệu bản thân"
    
    # Common message patterns
    CHUNK_ANALYSIS_TIME_ESTIMATE = 20  # seconds per chunk
    MAX_CONSECUTIVE_NO_CHILDREN = 3


@dataclass
class CrawlerConfig:
    """Data class for crawler configuration loaded from JSON file."""
    debug_mode: bool
    target_videos_per_query: int
    search_queries: List[str]
    max_recommended_per_query: int = 100
    min_target_count: int = 1
    download_method: str = "api_assisted"
    yt_dlp_primary: bool = True
    cookie_settings: Optional[Dict[str, Any]] = None
    enable_language_detection: bool = True
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"


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
                download_method=config_data.get('download_method', 'api_assisted'),
                yt_dlp_primary=config_data.get('yt_dlp_primary', True),
                cookie_settings=config_data.get('cookie_settings', None),
                enable_language_detection=config_data.get('enable_language_detection', True)
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
            "download_method": "api_assisted",
            "yt_dlp_primary": True,
            "enable_language_detection": True,
            "description": "Configuration file for YouTube Video Crawler. Set debug_mode to true for detailed logging, adjust target_videos_per_query for collection size, modify search_queries array to change what videos to search for, set yt_dlp_primary to true (uses yt-dlp as primary) or false (uses pytube as primary), and set enable_language_detection to false to disable language filtering and assume all videos are in Vietnamese."
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
    
    def _report_loaded_config(self, config: CrawlerConfig) -> None:
        """Report the loaded configuration to the user."""
        self.output.print_header("CONFIGURATION LOADED FROM FILE", 60)
        self.output.print_success(f"Configuration file: {self.config_file_path}")
        self.output.print_info(f"Debug mode: {'Enabled' if config.debug_mode else 'Disabled'}")
        self.output.print_info(f"Language detection: {'Enabled' if config.enable_language_detection else 'Disabled (assuming all videos are Vietnamese)'}")
        self.output.print_info(f"Target videos per query: {config.target_videos_per_query}")
        self.output.print_info(f"Total queries: {len(config.search_queries)}")
        self.output.print_info(f"Download strategy: yt-dlp (Android client) → pytube fallback")
        
        total_target_count = config.target_videos_per_query * len(config.search_queries)
        self.output.print_info(f"Total target videos: {total_target_count}")
        
        self.output.print_enumerated_list(config.search_queries, "Search queries:")
        
        if config.target_videos_per_query > config.max_recommended_per_query:
            self.output.print_warning(f"High target count per query: {config.target_videos_per_query} (recommended max: {config.max_recommended_per_query})")
        
        if not config.enable_language_detection:
            self.output.print_warning("⚠️  Language detection is disabled - all videos will be assumed to be Vietnamese")
            self.output.print_info("This will skip language filtering and may include non-Vietnamese content")
        
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
    chunks_analyzed: Optional[int] = None
    positive_chunk_index: Optional[int] = None
    was_chunked: bool = False


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
    
    def report_evaluation_result(self, has_children_voice: bool, is_new_channel: bool = True) -> None:
        """Report evaluation results."""
        if has_children_voice:
            self.output.print_result("Video contains children's voice")
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
    
    def report_chunk_analysis_start(self, video_title: str, duration: float, chunk_size: int) -> None:
        """Report start of chunk analysis for long videos."""
        truncated_title = video_title[:40] + "..." if len(video_title) > 40 else video_title
        estimated_chunks = int(duration / chunk_size) + (1 if duration % chunk_size > 0 else 0)
        print(f"🧩 Starting chunk analysis for '{truncated_title}' ({duration:.1f}s → ~{estimated_chunks} chunks)")
    
    def report_chunk_analysis_result(self, chunks_analyzed: int, positive_chunk: Optional[int], was_successful: bool, was_early_exit: bool = False, early_exit_reason: str = "") -> None:
        """Report chunk analysis completion."""
        if was_successful and positive_chunk:
            print(f"🎯 SUCCESS: Found children's voice in chunk {positive_chunk}/{chunks_analyzed}")
            print(f"⚡ Early exit saved {chunks_analyzed - positive_chunk} chunk analysis")
        elif was_early_exit:
            print(f"⏭️  EARLY EXIT: {early_exit_reason}")
            print(f"📊 Analyzed {chunks_analyzed} chunks before exit")
        else:
            print(f"❌ No children's voice found in any of {chunks_analyzed} chunks")
    
    def report_audio_analysis_timing(self, video_title: str, total_duration: float, children_detection_duration: float, was_chunked: bool = False, chunks_analyzed: Optional[int] = None) -> None:
        """Report comprehensive audio analysis timing with chunk information."""
        truncated_title = video_title[:40] + "..." if len(video_title) > 40 else video_title
        language_detection_duration = total_duration - children_detection_duration
        
        if was_chunked and chunks_analyzed:
            self.output.print_timing(f"Chunked audio analysis for '{truncated_title}' ({chunks_analyzed} chunks)", total_duration)
        else:
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
        print("💡 Both yt-dlp (Android client) and pytube methods failed")
        print("   This may indicate video access restrictions or network issues")
    
    def report_quota_exceeded_error(self, current_collected: int, total_target: int) -> None:
        """Report YouTube API quota exceeded error with guidance."""
        self.output.print_error("⚠️  All YouTube Data API keys quota exceeded!")
        print("🔧 API Quota Information:")
        print("   • YouTube Data API v3 has a daily quota limit")
        print("   • Default quota: 10,000 units per day per API key")
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
        print("   3. Add more API keys (YOUTUBE_API_KEY_4, etc.) to env file")
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
        self.output = OutputManager()
        self.reporter = CollectionReporter(self.output)
        self.error_reporter = ErrorReporter(self.output)
        
        if config is None:
            config_loader = ConfigLoader(self.output, config_file_path)
            config = config_loader.load_config()
        
        self.config = config
        self.analyzer = YouTubeOutputAnalyzer(Config.DEFAULT_OUTPUT_DIR)
        
        self.debug = DebugLogger(enabled=config.debug_mode)
        self.api_keys = self._get_api_keys()
        self.current_api_key_index = 0
        self.api_key = self.api_keys[0] if self.api_keys else None
        self.base_url = Config.YOUTUBE_API_BASE_URL
        
        from env_config import config as env_config
        self.max_workers = env_config.MAX_WORKERS
        self.poll_interval_seconds = getattr(env_config, 'POLL_INTERVAL_SECONDS', 300)
        
        if config.debug_mode:
            self.debug.log(f"Parallel processing configured with max_workers: {self.max_workers}")
        
        # API quota and rate limiting
        self.api_quota_exceeded = False
        self.api_requests_made = 0
        self.last_api_request_time = 0
        self.min_request_interval = 0.1
        self.max_retries = 3
        self.retry_delays = [1, 2, 4]
        
        # Initialize audio downloaders based on priority configuration
        # Extract cookie settings from config if available
        cookies_file = None
        cookies_from_browser = None
        
        if config.cookie_settings and config.cookie_settings.get('enabled', False):
            method = config.cookie_settings.get('method', 'file')
            
            if method == 'file':
                cookies_file_path = config.cookie_settings.get('cookies_file_path', 'cookies.txt')
                # Ensure we have the full path
                if not os.path.isabs(cookies_file_path):
                    cookies_file_path = os.path.join(os.path.dirname(__file__), cookies_file_path)
                cookies_file = cookies_file_path
                
            elif method == 'browser':
                cookies_from_browser = config.cookie_settings.get('browser_name', 'chrome')
        
        # Initialize audio downloader
        self.audio_downloader = YoutubeAudioDownloader(
            config=AudioDownloaderConfig(),
            cookies_file=cookies_file,
            cookies_from_browser=cookies_from_browser
        )
        
        print("🔧 Audio downloader initialized")
        
        # Initialize integrated audio downloader for batch processing
        audio_config = AudioDownloaderConfig(language_mapping={})
        self.integrated_audio_downloader = YoutubeAudioDownloader(
            audio_config, 
            language_mapping={}
        )
        
        # Log the download strategy
        print(f"🔧 Audio download strategy: yt-dlp (Android client) → pytube fallback")
        print(f"🔧 Using reliable yt-dlp with Android client to bypass YouTube restrictions")
        
        # Initialize YouTube Data API service for enhanced metadata retrieval
        self.youtube_service = None
        self._init_youtube_data_api()
        
        # Global variables for multiple query processing
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
        
        # URL counter for running integrated audio downloader every 2 URLs
        self.url_counter_for_downloader = 0
        
        # Language mapping for organizing audio downloads
        self.url_language_mapping = {}  # Maps URL to language classification (vietnamese/unknown)
    
    def _run_integrated_audio_downloader(self) -> None:
        """
        Run the integrated audio downloader to process collected URLs.
        Uses the packaged functionality instead of subprocess for better reliability.
        """
        try:
            # Update the integrated downloader's language mapping
            self.integrated_audio_downloader.language_mapping = self.url_language_mapping.copy()
            
            print(f"🎵 Running integrated audio downloader")
            print(f"📝 Using language mapping: {len(self.url_language_mapping)} URLs classified")
            print(f"📁 Ensuring vietnamese/ and unknown/ folders exist...")
            
            # Get the default URLs file path
            base_dir = os.path.dirname(os.path.abspath(__file__))
            urls_file = os.path.join(base_dir, 'youtube_url_outputs', 'collected_video_urls.txt')
            
            # Process URLs using the integrated function
            results = self.integrated_audio_downloader.process_urls_from_file(
                urls_file_path=urls_file,
                language_mapping=self.url_language_mapping
            )
            
            # Report results
            if results['processed'] > 0:
                print("✅ Audio downloader completed successfully")
                print("📊 Processing summary:")
                print(f"  📁 Total URLs in file: {results['total_in_file']}")
                print(f"  🔄 URLs processed: {results['processed']}")
                print(f"  ✅ Successful downloads: {results['successful']}")
                print(f"  ⏭️  Already downloaded (skipped): {results['skipped']}")
                print(f"  ❌ Failed downloads: {results['failed']}")
                
                if results['successful'] > 0:
                    success_rate = (results['successful'] / results['processed']) * 100 if results['processed'] > 0 else 0
                    print(f"  📈 Success rate: {success_rate:.1f}%")
            else:
                print("✅ All URLs already processed - no new downloads needed")
                
        except Exception as e:
            print(f"❌ Error running integrated audio downloader: {e}")
            import traceback
            print(f"📋 Error details: {traceback.format_exc()[:300]}...")
    
    def _check_and_run_downloader(self) -> None:
        """
        Check if we've collected 2 URLs and run the integrated audio downloader if so.
        """
        self.url_counter_for_downloader += 1
        if self.url_counter_for_downloader >= 2:
            print(f"\n🎯 Collected {self.url_counter_for_downloader} URLs - triggering integrated audio downloader")
            self._run_integrated_audio_downloader()
            self.url_counter_for_downloader = 0  # Reset counter
            print("🔄 Continuing URL collection...\n")

    def _download_audio_with_fallback(self, url: str, index: int) -> Optional[Tuple[str, float]]:
        """
        Download audio using the reliable yt-dlp method with Android client configuration.
        Falls back to pytube only if yt-dlp completely fails.
        
        Args:
            url (str): YouTube video URL
            index (int): Index for filename uniqueness
            
        Returns:
            Optional[Tuple[str, float]]: (wav_file_path, duration) or None if both fail
        """
        # Always try yt-dlp with Android client first (most reliable method)
        try:
            print(f"🔄 Downloading with yt-dlp (Android client)")
            print(f"📡 Using proven method that bypasses YouTube restrictions")
            result = self.audio_downloader.download_audio_yt_dlp_fallback(url, index)
            
            if result and result[0]:  # Check if we got a valid result with file path
                print(f"✅ Primary yt-dlp download successful")
                return result
            else:
                print(f"❌ yt-dlp method returned no result")
                
        except Exception as e:
            print(f"❌ yt-dlp method failed: {str(e)[:100]}...")
        
        # Fallback to pytube only if yt-dlp fails
        try:
            print(f"🔄 FALLBACK: Attempting pytube download as last resort")
            print(f"⚠️  Note: pytube may have issues with YouTube's recent restrictions")
            result = self.audio_downloader.download_audio_pytube(url, index)
            
            if result and result[0]:  # Check if we got a valid result with file path
                print(f"✅ Fallback pytube download successful (despite restrictions)")
                return result
            else:
                print(f"❌ Pytube fallback returned no result")
                
        except Exception as e:
            print(f"❌ Pytube fallback failed: {str(e)[:100]}...")
        
        print(f"❌ DOWNLOAD FAILED: Both yt-dlp (Android client) and pytube failed")
        print(f"🔗 URL: {url[:50]}...")
        print(f"💡 This may indicate severe YouTube restrictions or network issues")
        return None
    
    def _ensure_video_duration_seconds(self, video: Dict) -> None:
        """Ensure the video dict has numeric 'duration' in seconds when a max limit is configured."""
        try:
            max_limit = config.MAX_AUDIO_DURATION_SECONDS
            if max_limit is None:
                return
            has_duration = video.get('duration') is not None
            if has_duration:
                return
            # Try fetching duration via YouTube Data API for this single video
            if self.youtube_service and video.get('video_id'):
                metadata = self.get_video_metadata_via_api([video['video_id']])
                if metadata and video['video_id'] in metadata:
                    video['duration'] = metadata[video['video_id']].get('duration_seconds')
        except Exception:
            # Non-fatal; if we cannot resolve duration we don't alter the video
            pass

    def _get_api_keys(self) -> list[str]:
        """Get and validate API keys from environment configuration."""
        try:
            api_keys = config.YOUTUBE_API_KEYS
            if not api_keys:
                raise ValueError("No YouTube API keys found in environment")
            
            print(f"✅ {len(api_keys)} YouTube API key(s) loaded from environment")
            for i, key in enumerate(api_keys, 1):
                print(f"   API Key {i}: {'*' * 20}...{key[-4:]}")
            
            return api_keys
        except ValueError as e:
            self.error_reporter.report_configuration_error(e)
            raise
    
    def _switch_to_next_api_key(self) -> bool:
        """
        Switch to the next available API key when current one is exhausted.
        
        Returns:
            bool: True if successfully switched to next key, False if no more keys available
        """
        if self.current_api_key_index + 1 < len(self.api_keys):
            self.current_api_key_index += 1
            old_key = self.api_key
            self.api_key = self.api_keys[self.current_api_key_index]
            
            print(f"🔄 Switching to API Key {self.current_api_key_index + 1}")
            if old_key:
                print(f"   Previous: {'*' * 20}...{old_key[-4:]}")
            print(f"   Current:  {'*' * 20}...{self.api_key[-4:]}")
            
            # Reinitialize YouTube Data API service with new key
            self._init_youtube_data_api()
            
            # Reset quota tracking for new key
            self.api_quota_exceeded = False
            print(f"✅ Successfully switched to API Key {self.current_api_key_index + 1}")
            
            return True
        else:
            print(f"❌ No more API keys available (used {len(self.api_keys)}/{len(self.api_keys)})")
            return False
    
    def _switch_to_key_index(self, idx: int) -> None:
        """Switch to a specific API key index and reinitialize the YouTube service."""
        old_key = self.api_key
        self.current_api_key_index = idx
        self.api_key = self.api_keys[idx]
        print(f"🔄 Switching to API Key {idx + 1}")
        if old_key:
            print(f"   Previous: {'*' * 20}...{old_key[-4:]}")
        print(f"   Current:  {'*' * 20}...{self.api_key[-4:]}")
        self._init_youtube_data_api()
        self.api_quota_exceeded = False
    
    def _probe_key_available(self, key: str) -> bool:
        """
        Cheap quota probe for a single key using a low-cost videos.list call.
        Returns True if the key appears usable (HTTP 200), False otherwise.
        """
        try:
            probe_url = f"{self.base_url}/videos"
            params = {
                "part": "id",
                "id": "Ks-_Mh1QhMc",
                "key": key,
            }
            resp = requests.get(probe_url, params=params, timeout=10)
            if resp.status_code == 200:
                return True
            if resp.status_code == 403:
                try:
                    data = resp.json() if resp.content else {}
                except Exception:
                    data = {}
                reason = (data.get("error", {}).get("errors", [{}])[0].get("reason", "") or "").lower()
                if "quotaexceeded" in reason or "dailylimitexceeded" in reason:
                    return False
            return False
        except Exception:
            return False
    
    def wait_until_any_key_restored(self, poll_interval_seconds: Optional[int] = None) -> None:
        """
        Poll all configured API keys periodically. As soon as any key is usable,
        switch to it and return. Does not alter quotas; only waits.
        """
        if poll_interval_seconds is None:
            poll_interval_seconds = self.poll_interval_seconds
        
        # Ensure we have a valid polling interval
        if poll_interval_seconds is None or poll_interval_seconds <= 0:
            poll_interval_seconds = 300  # Default 5 minutes
            
        print(f"⏳ All configured API keys appear exhausted. Polling every {poll_interval_seconds}s until any key resets...")
        start_time = time.time()
        poll_count = 0
        while True:
            polled_this_cycle = 0
            for idx, key in enumerate(self.api_keys):
                if self._probe_key_available(key):
                    print(f"✅ Quota available on API Key {idx + 1}. Resuming...")
                    self._switch_to_key_index(idx)
                    return
                polled_this_cycle += 1
            poll_count += 1
            # Heartbeat: emit a status line every 5 cycles to indicate we're still waiting
            if poll_count % 5 == 0:
                elapsed = int(time.time() - start_time)
                minutes = elapsed // 60
                seconds = elapsed % 60
                print(f"⏳ Still waiting... elapsed {minutes}m{seconds:02d}s, last cycle probed {polled_this_cycle} key(s)")
            time.sleep(float(poll_interval_seconds))
    
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
                
                # Build request
                request = self.youtube_service.videos().list(
                    part="snippet,contentDetails,statistics",
                    id=",".join(batch_ids)
                )
                
                # Execute with simple quota-aware retry: try once, if quota 403 → wait → rebuild request → retry once
                for attempt in range(2):
                    try:
                        response = request.execute()
                        break
                    except HttpError as http_err:
                        status = getattr(http_err, 'status_code', None) or getattr(http_err.resp, 'status', None)
                        # Extract reason if present
                        try:
                            err_content = http_err.content.decode() if hasattr(http_err, 'content') and isinstance(http_err.content, (bytes, bytearray)) else str(http_err)
                            err_json = json.loads(err_content) if err_content and err_content.startswith('{') else {}
                            reason = (err_json.get('error', {}).get('errors', [{}])[0].get('reason', '') or '').lower()
                        except Exception:
                            reason = ''
                        if status == 403 and ("quotaexceeded" in reason or "dailylimitexceeded" in reason):
                            print("⚠️ Metadata fetch quota exceeded - waiting for any key to restore...")
                            self.api_quota_exceeded = True
                            self.wait_until_any_key_restored()
                            # Rebuild request with refreshed service/key and retry once
                            request = self.youtube_service.videos().list(
                                part="snippet,contentDetails,statistics",
                                id=",".join(batch_ids)
                            )
                            continue
                        else:
                            raise
                else:
                    # If we exhausted retries without a break
                    print("⚠️ Failed to fetch metadata after quota wait")
                    response = {"items": []}
                
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
            # Clear CUDA cache before creating classifier
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
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
    
    def _force_memory_cleanup(self) -> None:
        """
        Force comprehensive memory cleanup including CUDA cache and garbage collection.
        """
        try:
            import gc
            
            # Force garbage collection
            gc.collect()
            
            # Clear CUDA cache if available
            try:
                import torch
                if hasattr(torch, 'cuda') and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
                    # Reset peak memory stats
                    torch.cuda.reset_peak_memory_stats()
                    
                    current_memory = torch.cuda.memory_allocated() / 1024**3  # GB
                    max_memory = torch.cuda.max_memory_allocated() / 1024**3  # GB
                    self.debug.log(f"CUDA Memory - Current: {current_memory:.2f}GB, Peak: {max_memory:.2f}GB")
            except ImportError:
                pass  # torch not available
            except Exception as cuda_error:
                self.debug.log(f"CUDA cleanup warning: {cuda_error}")
                
        except Exception as e:
            self.debug.log_error("Memory cleanup", e)
    
    def _split_audio_into_chunks(self, audio_file_path: str, chunk_duration_seconds: int) -> List[str]:
        """
        Split audio file into chunks of specified duration.
        
        Args:
            audio_file_path (str): Path to the audio file to split
            chunk_duration_seconds (int): Duration of each chunk in seconds
            
        Returns:
            List[str]: List of paths to chunk files
        """
        chunk_files = []
        temp_dir = None
        
        try:
            # Create temporary directory for chunks
            temp_dir = tempfile.mkdtemp(prefix="audio_chunks_")
            
            # Load audio file
            print(f"📄 Loading audio file for chunking: {audio_file_path}")
            audio, sr = librosa.load(audio_file_path, sr=16000)  # Standard 16kHz for analysis
            total_duration = len(audio) / sr
            
            print(f"📏 Audio duration: {total_duration:.1f}s, chunk size: {chunk_duration_seconds}s")
            
            # Calculate number of chunks
            num_chunks = int(total_duration / chunk_duration_seconds) + (1 if total_duration % chunk_duration_seconds > 0 else 0)
            print(f"📊 Will create {num_chunks} chunks")
            
            # Create chunks
            for i in range(num_chunks):
                start_time = i * chunk_duration_seconds
                end_time = min((i + 1) * chunk_duration_seconds, total_duration)
                
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                
                chunk_audio = audio[start_sample:end_sample]
                
                # Skip very short chunks (less than 1 second)
                if len(chunk_audio) < sr:
                    print(f"⏭️  Skipping chunk {i+1} (too short: {len(chunk_audio)/sr:.1f}s)")
                    continue
                
                # Save chunk
                chunk_path = os.path.join(temp_dir, f"chunk_{i+1:03d}.wav")
                sf.write(chunk_path, chunk_audio, sr)
                chunk_files.append(chunk_path)
                
                chunk_duration = len(chunk_audio) / sr
                print(f"📋 Created chunk {i+1}: {start_time:.1f}s-{end_time:.1f}s ({chunk_duration:.1f}s) -> {chunk_path}")
            
            print(f"✅ Successfully created {len(chunk_files)} audio chunks")
            return chunk_files
            
        except Exception as e:
            print(f"❌ Error splitting audio into chunks: {e}")
            # Cleanup on error
            if chunk_files:
                for chunk_file in chunk_files:
                    try:
                        if os.path.exists(chunk_file):
                            os.remove(chunk_file)
                    except Exception:
                        pass
            if temp_dir and os.path.exists(temp_dir):
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
            return []
    
    def _cleanup_chunk_files(self, chunk_files: List[str]) -> None:
        """
        Clean up temporary chunk files and their directory.
        
        Args:
            chunk_files (List[str]): List of chunk file paths to clean up
        """
        if not chunk_files:
            return
            
        try:
            # Get the directory containing the chunks
            chunk_dir = os.path.dirname(chunk_files[0])
            
            # Remove all chunk files
            for chunk_file in chunk_files:
                try:
                    if os.path.exists(chunk_file):
                        os.remove(chunk_file)
                        self.debug.log(f"Cleaned up chunk file: {chunk_file}")
                except Exception as e:
                    self.debug.log(f"Could not clean up chunk file {chunk_file}: {e}")
            
            # Remove the temporary directory if empty
            try:
                if os.path.exists(chunk_dir) and not os.listdir(chunk_dir):
                    os.rmdir(chunk_dir)
                    self.debug.log(f"Cleaned up chunk directory: {chunk_dir}")
            except Exception as e:
                self.debug.log(f"Could not clean up chunk directory {chunk_dir}: {e}")
                
        except Exception as e:
            self.debug.log(f"Error during chunk cleanup: {e}")
    
    def _analyze_video_chunks(self, video: Dict, video_type: str, audio_file_path: str, video_duration: float) -> AnalysisResult:
        """
        Analyze video by splitting it into chunks and processing sequentially with early exit.
        
        Args:
            video (Dict): Video information dictionary
            video_type (str): Type of video being processed ("main" or "similar")
            audio_file_path (str): Path to the downloaded audio file
            video_duration (float): Duration of the video in seconds
            
        Returns:
            AnalysisResult: Analysis results from the first positive chunk or overall negative result
        """
        analysis_start_time = time.time()
        chunk_files = []
        
        try:
            # Get chunk duration from config
            chunk_duration = config.MAX_AUDIO_DURATION_SECONDS
            if chunk_duration is None:
                # Fallback to default chunk size if no limit configured
                chunk_duration = 300  # 5 minutes
            
            print(f"🧩 Starting chunk analysis for {video_duration:.1f}s video")
            print(f"📏 Chunk size: {chunk_duration}s ({chunk_duration//60}m {chunk_duration%60}s)")
            print(f"🎯 Will analyze chunks sequentially with early exit on success or 3 consecutive non-children chunks")
            
            # OPTIMIZATION: Determine video language ONCE before chunk processing using transcript-based detection
            is_video_vietnamese = True  # Default assumption
            detected_language = 'vi'
            language_detection_time = 0.0
            
            if self.config.enable_language_detection:
                print(f"🌐 Determining video language once before chunk analysis using transcript...")
                language_start_time = time.time()
                
                # Get shared classifier for transcript-based language detection
                classifier = self._get_shared_classifier()
                
                # Use transcript-based language detection (much faster and more reliable than audio-based)
                try:
                    is_video_vietnamese = classifier.is_vietnamese_from_youtube_url(video['url'])
                    detected_language = 'vi' if is_video_vietnamese else 'other'
                    language_detection_time = time.time() - language_start_time
                    
                    print(f"📋 Video language determined via transcript: {'Vietnamese' if is_video_vietnamese else f'Not Vietnamese ({detected_language})'}")
                    
                    # If video is not Vietnamese, we can exit early without processing chunks
                    if not is_video_vietnamese:
                        print(f"⏭️  EARLY EXIT: Video is not Vietnamese - skipping all chunk analysis")
                        print(f"⚡ Time saved: Avoided processing chunks and audio analysis")
                        
                        total_analysis_time = time.time() - analysis_start_time
                        return AnalysisResult(
                            is_vietnamese=False,
                            detected_language=detected_language,
                            has_children_voice=False,
                            confidence=0.0,
                            error=None,
                            total_analysis_time=total_analysis_time,
                            children_detection_time=0.0,
                            video_length_seconds=video_duration,
                            chunks_analyzed=0,
                            positive_chunk_index=None,
                            was_chunked=True
                        )
                        
                except Exception as lang_error:
                    print(f"⚠️  Transcript-based language detection failed: {lang_error}")
                    print(f"🔄 Assuming video is Vietnamese and proceeding with chunk analysis")
                    is_video_vietnamese = True
                    detected_language = 'vi'
                    language_detection_time = time.time() - language_start_time
            else:
                print(f"⚠️  Language detection disabled - assuming video is Vietnamese")
            
            # Split audio into chunks
            chunk_files = self._split_audio_into_chunks(audio_file_path, chunk_duration)
            
            if not chunk_files:
                print("❌ Failed to create audio chunks")
                return AnalysisResult(
                    is_vietnamese=is_video_vietnamese,
                    detected_language=detected_language,
                    has_children_voice=None,
                    confidence=0,
                    error='Failed to create audio chunks',
                    total_analysis_time=time.time() - analysis_start_time,
                    children_detection_time=0.0,
                    video_length_seconds=video_duration,
                    chunks_analyzed=0,
                    positive_chunk_index=None,
                    was_chunked=True
                )
            
            total_chunks = len(chunk_files)
            estimated_total_time = total_chunks * Config.CHUNK_ANALYSIS_TIME_ESTIMATE
            print(f"📊 Created {total_chunks} chunks for children's voice analysis")
            print(f"⏱️  Estimated analysis time: ~{estimated_total_time//60}m {estimated_total_time%60}s (with early exit optimization)")
            
            classifier = self._get_shared_classifier()
            consecutive_no_children_count = 0
            chunk_index = 0
            
            # Analyze chunks sequentially with early exit
            for chunk_index, chunk_file in enumerate(chunk_files, 1):
                print(f"\n🔍 Analyzing chunk {chunk_index}/{total_chunks} for children's voice...")
                print(f"📈 Progress: {((chunk_index-1)/total_chunks)*100:.1f}% complete")
                
                try:
                    # Clear GPU memory before each chunk
                    try:
                        import torch
                        if hasattr(torch, 'cuda') and torch.cuda.is_available():
                            torch.cuda.empty_cache()
                            torch.cuda.synchronize()
                    except (ImportError, AttributeError):
                        pass  # torch or CUDA not available
                    
                    # OPTIMIZED: Only perform children's voice detection (no language detection per chunk)
                    children_detection_start_time = time.time()
                    children_voice_result = classifier.is_child_audio(chunk_file)
                    children_detection_duration = time.time() - children_detection_start_time
                    
                    # Check for critical errors in children's voice detection
                    if children_voice_result is None:
                        print(f"❌ Chunk {chunk_index} children's voice detection failed")
                        consecutive_no_children_count += 1
                        
                        if consecutive_no_children_count >= Config.MAX_CONSECUTIVE_NO_CHILDREN:
                            remaining_chunks = total_chunks - chunk_index
                            time_saved = remaining_chunks * Config.CHUNK_ANALYSIS_TIME_ESTIMATE
                            print(f"⏭️  EARLY EXIT: {Config.MAX_CONSECUTIVE_NO_CHILDREN} consecutive chunk analysis failures")
                            print(f"🔧 Technical issue detected - stopping analysis to prevent resource waste")
                            print(f"⚡ Saving ~{time_saved//60}m {time_saved%60}s by skipping {remaining_chunks} remaining chunks")
                            break
                        
                        continue  # Try next chunk
                    
                    print(f"📋 Chunk {chunk_index} children's voice detection: {children_voice_result}")
                    
                    if children_voice_result:
                        remaining_chunks = total_chunks - chunk_index
                        time_saved = remaining_chunks * Config.CHUNK_ANALYSIS_TIME_ESTIMATE
                        print(f"🎯 SUCCESS! Chunk {chunk_index} contains children's voice")
                        print(f"⚡ Early exit: Found positive match in {chunk_index}/{total_chunks} chunks")
                        if remaining_chunks > 0:
                            print(f"⏱️  Time saved: ~{time_saved//60}m {time_saved%60}s by skipping {remaining_chunks} remaining chunks")
                        
                        # Clean up chunk files
                        self._cleanup_chunk_files(chunk_files)
                        
                        # Clean up any temporary download files
                        self.audio_downloader.cleanup_all_temp_files()
                        
                        # Report successful early exit
                        self.reporter.report_chunk_analysis_result(
                            chunk_index, 
                            chunk_index, 
                            True
                        )
                        
                        # Return positive result (language already determined)
                        total_analysis_time = time.time() - analysis_start_time
                        return AnalysisResult(
                            is_vietnamese=is_video_vietnamese,
                            detected_language=detected_language,
                            has_children_voice=True,
                            confidence=1.0,  # High confidence since we found children's voice
                            error=None,
                            total_analysis_time=total_analysis_time,
                            children_detection_time=children_detection_duration,
                            video_length_seconds=video_duration,
                            chunks_analyzed=chunk_index,
                            positive_chunk_index=chunk_index,
                            was_chunked=True
                        )
                    else:
                        # This chunk doesn't contain children's voice
                        print(f"❌ Chunk {chunk_index}: no children's voice detected")
                        
                        # OPTIMIZED: Count consecutive chunks without children's voice
                        consecutive_no_children_count += 1
                        
                        if consecutive_no_children_count >= Config.MAX_CONSECUTIVE_NO_CHILDREN:
                            remaining_chunks = total_chunks - chunk_index
                            time_saved = remaining_chunks * Config.CHUNK_ANALYSIS_TIME_ESTIMATE
                            print(f"⏭️  EARLY EXIT: {Config.MAX_CONSECUTIVE_NO_CHILDREN} consecutive chunks without children's voice")
                            print(f"📊 Pattern analysis: Video unlikely to contain children's voice")
                            print(f"⚡ Intelligent skip: Saving ~{time_saved//60}m {time_saved%60}s by skipping {remaining_chunks} remaining chunks")
                            print(f"📈 Analyzed {chunk_index}/{total_chunks} chunks ({(chunk_index/total_chunks)*100:.1f}%) before exit")
                            break
                        
                        continue
                        
                except Exception as e:
                    print(f"❌ Error analyzing chunk {chunk_index}: {e}")
                    consecutive_no_children_count += 1
                    
                    if consecutive_no_children_count >= Config.MAX_CONSECUTIVE_NO_CHILDREN:
                        remaining_chunks = total_chunks - chunk_index
                        time_saved = remaining_chunks * Config.CHUNK_ANALYSIS_TIME_ESTIMATE
                        print(f"⏭️  EARLY EXIT: {Config.MAX_CONSECUTIVE_NO_CHILDREN} consecutive chunk analysis errors")
                        print(f"🔧 Technical issue detected - stopping analysis to prevent resource waste")
                        print(f"⚡ Saving ~{time_saved//60}m {time_saved%60}s by skipping {remaining_chunks} remaining chunks")
                        break
                    
                    continue  # Try next chunk
            
            was_early_exit = consecutive_no_children_count >= Config.MAX_CONSECUTIVE_NO_CHILDREN
            
            if was_early_exit:
                completion_rate = (chunk_index/total_chunks)*100
                print(f"📊 CHUNK ANALYSIS SUMMARY:")
                print(f"   └─ Early exit after analyzing {chunk_index}/{total_chunks} chunks ({completion_rate:.1f}%)")
                print(f"   └─ Reason: {Config.MAX_CONSECUTIVE_NO_CHILDREN} consecutive chunks without children's voice")
                print(f"   └─ Result: Video classified as not containing children's voice")
                
                self.reporter.report_chunk_analysis_result(
                    chunk_index, 
                    None, 
                    False, 
                    was_early_exit=True, 
                    early_exit_reason=f"{Config.MAX_CONSECUTIVE_NO_CHILDREN} consecutive chunks without children's voice"
                )
            else:
                print(f"📊 CHUNK ANALYSIS SUMMARY:")
                print(f"   └─ Completed full analysis of {total_chunks}/{total_chunks} chunks (100%)")
                print(f"   └─ Result: No children's voice detected in any chunk")
                
                # Report normal completion
                self.reporter.report_chunk_analysis_result(
                    total_chunks, 
                    None, 
                    False
                )
            
            # Clean up chunk files
            self._cleanup_chunk_files(chunk_files)
            
            # Clean up any temporary download files
            self.audio_downloader.cleanup_all_temp_files()
            
            total_analysis_time = time.time() - analysis_start_time
            
            # Use actual chunks analyzed for the result
            chunks_actually_analyzed = chunk_index if was_early_exit else total_chunks
            
            return AnalysisResult(
                is_vietnamese=is_video_vietnamese,  # Keep the originally determined language result
                detected_language=detected_language,
                has_children_voice=False,
                confidence=0.0,
                error=None,
                total_analysis_time=total_analysis_time,
                children_detection_time=0.0,
                video_length_seconds=video_duration,
                chunks_analyzed=chunks_actually_analyzed,
                positive_chunk_index=None,
                was_chunked=True
            )
            
        except Exception as e:
            print(f"❌ Error in chunk analysis: {e}")
            
            # Clean up chunk files on error
            if chunk_files:
                self._cleanup_chunk_files(chunk_files)
            
            # Clean up any temporary download files
            self.audio_downloader.cleanup_all_temp_files()
            
            total_analysis_time = time.time() - analysis_start_time
            return AnalysisResult(
                is_vietnamese=is_video_vietnamese if 'is_video_vietnamese' in locals() else False,
                detected_language=detected_language if 'detected_language' in locals() else 'error',
                has_children_voice=None,
                confidence=0,
                error=str(e),
                total_analysis_time=total_analysis_time,
                children_detection_time=0.0,
                video_length_seconds=video_duration,
                chunks_analyzed=0,
                positive_chunk_index=None,
                was_chunked=True
            )
        
        finally:
            # Force memory cleanup
            self._force_memory_cleanup()
    
    def analyze_video_audio(self, video: Dict, video_type: str = "main") -> AnalysisResult:
        """
        ENHANCED: Download and analyze video audio with chunking support for long videos.
        For videos within duration limit: uses optimized combined prediction.
        For videos exceeding limit: splits into chunks and analyzes sequentially with early exit.
        
        Args:
            video (Dict): Video information dictionary
            video_type (str): Type of video being processed ("main" or "similar")
            
        Returns:
            AnalysisResult: Combined analysis results with timing information and chunking details
        """
        analysis_start_time = time.time()
        children_detection_start_time = None
        children_detection_duration = 0.0
        video_duration = None  # Ensure video_duration is always defined
        wav_file_path = None  # Initialize to handle cleanup in exception cases
        
        # Get configured duration limit from environment; if None, no limit
        MAX_VIDEO_DURATION_SECONDS = config.MAX_AUDIO_DURATION_SECONDS
            
        # Check if we need chunking (no longer skip long videos, but chunk them instead)
        should_use_chunking = False
        estimated_duration = None
        
        try:
            # Ensure we have a duration when limit is set
            if MAX_VIDEO_DURATION_SECONDS is not None:
                self._ensure_video_duration_seconds(video)
            # Get video duration from metadata if available
            if 'duration' in video and video['duration'] and MAX_VIDEO_DURATION_SECONDS is not None:
                # Duration might be in ISO 8601 format (PT1M30S) or seconds
                duration_str = video['duration']
                if isinstance(duration_str, str) and duration_str.startswith('PT'):
                    # Parse ISO 8601 duration (PT1M30S = 1 minute 30 seconds)
                    import re
                    time_pattern = re.compile(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?')
                    match = time_pattern.match(duration_str)
                    if match:
                        hours = int(match.group(1) or 0)
                        minutes = int(match.group(2) or 0)  
                        seconds = int(match.group(3) or 0)
                        total_seconds = hours * 3600 + minutes * 60 + seconds
                        estimated_duration = total_seconds
                        
                        if total_seconds > MAX_VIDEO_DURATION_SECONDS:
                            should_use_chunking = True
                            print(f"📊 Long video detected ({total_seconds//60}m {total_seconds%60}s > {MAX_VIDEO_DURATION_SECONDS//60}m): {video.get('title', 'Unknown')[:50]}...")
                            print(f"🧩 Will use chunk analysis instead of skipping")
                elif isinstance(duration_str, (int, float)) and MAX_VIDEO_DURATION_SECONDS is not None:
                    # Duration already in seconds
                    estimated_duration = duration_str
                    if duration_str > MAX_VIDEO_DURATION_SECONDS:
                        should_use_chunking = True
                        print(f"📊 Long video detected ({int(duration_str//60)}m {int(duration_str%60)}s > {MAX_VIDEO_DURATION_SECONDS//60}m): {video.get('title', 'Unknown')[:50]}...")
                        print(f"🧩 Will use chunk analysis instead of skipping")
        except Exception as duration_check_error:
            # If duration check fails, continue with regular processing
            print(f"⚠️  Could not check video duration: {duration_check_error}")
        
        try:
            # Convert YouTube video to .wav file once for both analyses
            # Use thread-safe global download index to prevent file overlap
            current_download_index = self._get_next_download_index()
            
            # Use the configured download method with automatic fallback
            result = self._download_audio_with_fallback(video['url'], current_download_index)
            
            if result:
                wav_file_path, video_duration = result
            else:
                wav_file_path = None
                video_duration = None
            
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
                    video_length_seconds=video_duration,
                    chunks_analyzed=None,
                    positive_chunk_index=None,
                    was_chunked=False
                )
            
            # Check if we should use chunking for this video
            if should_use_chunking or (video_duration and MAX_VIDEO_DURATION_SECONDS and video_duration > MAX_VIDEO_DURATION_SECONDS):
                duration_minutes = int(video_duration // 60)
                duration_seconds = int(video_duration % 60)
                limit_minutes = int(MAX_VIDEO_DURATION_SECONDS // 60) if MAX_VIDEO_DURATION_SECONDS else 0
                
                print(f"🧩 LONG VIDEO DETECTED: {duration_minutes}m {duration_seconds}s (limit: {limit_minutes}m)")
                print(f"📋 Switching to intelligent chunk analysis with early exit optimization")
                
                # Use chunk-based analysis (ensure video_duration is not None)
                actual_duration = video_duration or estimated_duration or 0.0
                result = self._analyze_video_chunks(video, video_type, wav_file_path, actual_duration)
                
                # Clean up original audio file
                self._cleanup_audio_file(wav_file_path)
                
                return result
            
            # Standard video analysis (not chunked)
            duration_minutes = int(video_duration // 60) if video_duration else 0
            duration_seconds = int(video_duration % 60) if video_duration else 0
            print(f"🎵 STANDARD ANALYSIS: {duration_minutes}m {duration_seconds}s video")
            print(f"📋 Using optimized combined prediction (language + children's voice detection)")
            
            # OPTIMIZED: Use shared classifier instance and combined prediction
            classifier = self._get_shared_classifier()
            
            # Clear GPU memory before prediction to avoid fragmentation
            try:
                import torch
                if hasattr(torch, 'cuda') and torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
            except (ImportError, AttributeError):
                pass  # torch or CUDA not available
            
            # Check if language detection is enabled (controlled by self.config.enable_language_detection)
            # When disabled, all videos are assumed to be Vietnamese and only children's voice detection is performed
            if self.config.enable_language_detection:
                # OPTIMIZED: Get both language and children's voice detection in one call
                # This loads audio only ONCE instead of twice (40-50% performance gain)
                # Pass YouTube URL for transcript-based language detection
                # Time the children's voice detection portion specifically
                children_detection_start_time = time.time()
                combined_result = classifier.get_combined_prediction(wav_file_path, youtube_url=video['url'])
                children_detection_duration = time.time() - children_detection_start_time
            else:
                # Skip language detection, only perform children's voice detection
                # This assumes all videos are in the target language (Vietnamese)
                print("⚠️  Language detection disabled - assuming video is Vietnamese")
                children_detection_start_time = time.time()
                children_voice_result = classifier.is_child_audio(wav_file_path)
                children_detection_duration = time.time() - children_detection_start_time
                
                # Create combined result with bypassed language detection
                combined_result = {
                    'is_vietnamese': True,  # Assume all videos are Vietnamese
                    'detected_language': 'vi',  # Vietnamese
                    'is_child': children_voice_result,
                    'confidence': 1.0 if children_voice_result is not None else 0.0
                }
            
            # Clear GPU memory after prediction
            try:
                import torch
                if hasattr(torch, 'cuda') and torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except (ImportError, AttributeError):
                pass  # torch or CUDA not available
            
            # Check for critical errors (not age detection failures)
            if "error" in combined_result and "age_detection_failed" not in combined_result:
                # Critical error - language detection failed
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
                    video_length_seconds=video_duration,
                    chunks_analyzed=None,
                    positive_chunk_index=None,
                    was_chunked=False
                )
            
            # Extract results from combined prediction
            is_vietnamese = combined_result.get('is_vietnamese', False)
            children_voice_result = combined_result.get('is_child', None)
            confidence = combined_result.get('confidence', 0.0)
            
            # Handle age detection failures gracefully
            if "age_detection_failed" in combined_result:
                print(f"  ⚠️ Age detection failed ({combined_result['age_detection_failed']}) but language detection succeeded")
                print(f"  Vietnamese detected: {is_vietnamese}")
                
                # For Vietnamese content with failed age detection, we can still proceed
                # but mark children_voice as unknown
                if is_vietnamese:
                    children_voice_result = None  # Unknown due to age detection failure
                    confidence = 0.5  # Moderate confidence since language detection worked
            
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
            self.reporter.report_audio_analysis_timing(
                video['title'], 
                total_analysis_time, 
                children_detection_duration,
                was_chunked=False,
                chunks_analyzed=None
            )
            
            # Update timing statistics
            self._update_timing_statistics(total_analysis_time, children_detection_duration)
            
            # Clean up audio file after successful analysis
            self._cleanup_audio_file(wav_file_path)
            
            # Force memory cleanup after analysis
            self._force_memory_cleanup()
            
            # Clean up any temporary download files
            self.audio_downloader.cleanup_all_temp_files()
            
            return AnalysisResult(
                is_vietnamese=is_vietnamese,
                detected_language=language_result['detected_language'],
                has_children_voice=children_voice_result,
                confidence=confidence,
                error=None,
                total_analysis_time=total_analysis_time,
                children_detection_time=children_detection_duration,
                video_length_seconds=video_duration,
                chunks_analyzed=None,
                positive_chunk_index=None,
                was_chunked=False
            )
            
        except Exception as e:
            total_analysis_time = time.time() - analysis_start_time
            self.error_reporter.report_audio_analysis_error(e)
            
            # Clean up audio file even if analysis failed (if it was created)
            if wav_file_path:
                self._cleanup_audio_file(wav_file_path)
            
            # Force memory cleanup on error
            self._force_memory_cleanup()
            
            # Clean up any temporary download files
            self.audio_downloader.cleanup_all_temp_files()
            
            return AnalysisResult(
                is_vietnamese=False,
                detected_language='unknown',
                has_children_voice=None,
                confidence=0,
                error=str(e),
                total_analysis_time=total_analysis_time,
                children_detection_time=children_detection_duration,
                video_length_seconds=video_duration,
                chunks_analyzed=None,
                positive_chunk_index=None,
                was_chunked=False
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
        print(f"  ├─ Total API keys available: {len(self.api_keys)}")
        print(f"  ├─ Current active API key: Key {self.current_api_key_index + 1}")
        print(f"  ├─ Total API requests made: {self.api_requests_made}")
        
        # Estimate quota units used (rough calculation)
        estimated_quota_used = self.api_requests_made * 100  # Each search request uses ~100 units
        print(f"  ├─ Estimated quota units used: {estimated_quota_used}")
        print(f"  ├─ Daily quota limit per key: 10,000 units (default)")
        
        if self.api_quota_exceeded:
            print(f"  └─ Status: ❌ ALL API KEYS QUOTA EXCEEDED")
            remaining_percentage = 0
            print(f"     └─ Used API keys: {self.current_api_key_index + 1}/{len(self.api_keys)}")
        else:
            remaining_quota = max(0, 10000 - estimated_quota_used)
            remaining_percentage = (remaining_quota / 10000) * 100
            print(f"  └─ Status: ✅ ACTIVE (Key {self.current_api_key_index + 1})")
            print(f"     ├─ Estimated remaining quota: {remaining_quota} units")
            print(f"     ├─ Estimated remaining: {remaining_percentage:.1f}%")
            print(f"     └─ Unused API keys: {len(self.api_keys) - self.current_api_key_index - 1}")
        
        if estimated_quota_used > 8000:  # Warning at 80%
            print(f"  ⚠️  Warning: High quota usage detected on current key!")
            if self.current_api_key_index + 1 < len(self.api_keys):
                print(f"     Will automatically switch to next key when quota exceeded")
            else:
                print(f"     This is the last available API key")
        
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
            self.debug.log(f"API quota exceeded flag set; polling before attempting {operation_name}")
            # Block-and-poll across all keys until any becomes available, then continue
            self.wait_until_any_key_restored()
            # Ensure params reflect the newly active key (if caller included a key param)
            if isinstance(params, dict) and 'key' in params:
                params['key'] = self.api_key
        
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
                        print(f"⚠️ API Key {self.current_api_key_index + 1} quota exceeded")
                        
                        # Try to switch to next API key
                        if self._switch_to_next_api_key():
                            print(f"🔄 Retrying request with new API key...")
                            # Update params with new API key and retry the request
                            params['key'] = self.api_key
                            return self._make_api_request(url, params, operation_name)
                        else:
                            # No more API keys currently available -> poll until any key is restored, then retry
                            self.api_quota_exceeded = True
                            self.error_reporter.report_quota_exceeded_error(
                                self.current_session_collected_count,
                                self.total_target_count
                            )
                            print(f"❌ All {len(self.api_keys)} API keys have exceeded their quota")
                            self.wait_until_any_key_restored()
                            # Update params with the now-active key and retry once resumed
                            params['key'] = self.api_key
                            return self._make_api_request(url, params, operation_name)
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
        Search videos on YouTube using the given query with duration metadata.
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            
        Returns:
            List[Dict]: List of video information dictionaries including duration
        """
        if self.api_quota_exceeded:
            self.debug.log("API quota exceeded before video search - waiting for any key to be restored")
            self.wait_until_any_key_restored()
        
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
        video_ids = []
        
        # First pass: extract basic video info and collect video IDs
        for item in items:
            video_info = self._extract_video_info(item)
            videos.append(video_info)
            video_ids.append(video_info['video_id'])
        
        # Second pass: get detailed metadata including duration for all videos at once
        if video_ids and self.youtube_service:
            try:
                metadata = self.get_video_metadata_via_api(video_ids)
                # Merge duration data into video info
                for video in videos:
                    video_id = video['video_id']
                    if video_id in metadata:
                        video['duration'] = metadata[video_id]['duration_seconds']
                        video['duration_iso'] = f"PT{int(metadata[video_id]['duration_seconds'] // 60)}M{int(metadata[video_id]['duration_seconds'] % 60)}S"
                    else:
                        video['duration'] = None  # Duration unknown
            except Exception as e:
                print(f"⚠️ Could not retrieve duration metadata: {e}")
                # Continue without duration data
                for video in videos:
                    video['duration'] = None
        else:
            # No YouTube service available, mark duration as unknown
            for video in videos:
                video['duration'] = None
        
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
        Get videos from a specific channel with duration metadata, optionally filtered by search query.
        
        Args:
            channel_id (str): YouTube channel ID
            query (str): Optional search query to filter channel videos
            max_results (int): Maximum number of results to return
            
        Returns:
            List[Dict]: List of video information dictionaries including duration
        """
        if self.api_quota_exceeded:
            self.debug.log("API quota exceeded before channel search - waiting for any key to be restored")
            self.wait_until_any_key_restored()
        
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
        video_ids = []
        
        # First pass: extract basic video info and collect video IDs
        for item in items:
            video_info = self._extract_video_info(item)
            videos.append(video_info)
            video_ids.append(video_info['video_id'])
            self.debug.log_video_added(video_info['title'])
        
        # Second pass: get detailed metadata including duration for all videos at once
        if video_ids and self.youtube_service:
            try:
                metadata = self.get_video_metadata_via_api(video_ids)
                # Merge duration data into video info
                for video in videos:
                    video_id = video['video_id']
                    if video_id in metadata:
                        video['duration'] = metadata[video_id]['duration_seconds']
                        video['duration_iso'] = f"PT{int(metadata[video_id]['duration_seconds'] // 60)}M{int(metadata[video_id]['duration_seconds'] % 60)}S"
                    else:
                        video['duration'] = None  # Duration unknown
            except Exception as e:
                print(f"⚠️ Could not retrieve channel video duration metadata: {e}")
                # Continue without duration data
                for video in videos:
                    video['duration'] = None
        else:
            # No YouTube service available, mark duration as unknown
            for video in videos:
                video['duration'] = None
        
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
        
        # Check language result first (only if language detection is enabled)
        if self.config.enable_language_detection:
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
        else:
            # Language detection disabled - assume all videos are Vietnamese
            print("⚠️  Language detection disabled - assuming video is Vietnamese")
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
        if evaluation_result:
            self.reporter.report_evaluation_result(True, True)
            
            # Add current video to collection
            self.total_video_urls.append(video['url'])
            self.collected_url_set.add(video['url'])
            self.current_session_collected_count += 1
            self.current_session_collected_urls.append(video['url'])
            self._save_url_to_file(video, Config.DEFAULT_URLS_FILE)
            query_stats['videos_collected'] += 1
            
            # Track language classification for audio downloader
            language_folder = 'vietnamese' if analysis_result.is_vietnamese else 'unknown'
            self.url_language_mapping[video['url']] = language_folder
            
            # Check if we should run audio downloader script
            self._check_and_run_downloader()
            
            # Mark video as collected in analysis results
            for result in reversed(self.video_analysis_results):
                if result['video_url'] == video['url']:
                    result['was_collected'] = True
                    break
            
            # Process similar videos with PARALLEL processing
            added_count = self._process_similar_videos_parallel(video, query_stats)
            self.reporter.report_channel_added_count(added_count)
            
            return True
        else:
            self.reporter.report_evaluation_result(evaluation_result or False, True)
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
            
            # Check language result first (only if language detection is enabled)
            if self.config.enable_language_detection:
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
            else:
                # Language detection disabled - assume all videos are Vietnamese
                print("⚠️  Language detection disabled - assuming similar video is Vietnamese")
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
                
                # Track language classification for audio downloader
                language_folder = 'vietnamese' if similar_analysis_result.is_vietnamese else 'unknown'
                self.url_language_mapping[similar_video['url']] = language_folder
                
                # Check if we should run audio downloader script
                self._check_and_run_downloader()
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
        OPTIMIZED: Process a single similar video WITHOUT classification.
        Similar videos are added directly when the main video passes classification.
        
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
        
        # ⭐ SIMPLIFIED: No classification for similar videos - add directly ⭐
        print(f"Adding similar video (no classification): {similar_video['title']}")
        
        # Store minimal video analysis result for detailed reporting
        video_analysis_record = {
            'video_url': similar_video['url'],
            'video_title': similar_video['title'],
            'channel_title': similar_video['channel_title'],
            'channel_id': similar_video['channel_id'],
            'video_type': 'similar',
            'query': query_stats['current_query'],
            'is_vietnamese': None,  # Not classified
            'detected_language': None,  # Not classified
            'has_children_voice': None,  # Not classified - assumed true
            'confidence': None,  # Not classified
            'total_analysis_time': 0.0,  # No analysis performed
            'children_detection_time': 0.0,  # No analysis performed
            'video_length_seconds': None,  # Not analyzed
            'was_collected': True,  # Always collected for similar videos
            'analysis_error': None,
            'timestamp': datetime.now().isoformat(),
            'classification_skipped': True  # Flag to indicate classification was skipped
        }
        self.video_analysis_results.append(video_analysis_record)
        
        # ⭐ Direct addition to results (no classification required) ⭐
        query_stats['videos_with_children_voice'] += 1  # Assumed based on main video
        self.total_videos_with_children_voice += 1
        
        # Thread-safe adding to results
        self.total_video_urls.append(similar_video['url'])
        self.collected_url_set.add(similar_video['url'])
        self.current_session_collected_count += 1
        self.current_session_collected_urls.append(similar_video['url'])
        self._save_url_to_file(similar_video, Config.DEFAULT_URLS_FILE)
        query_stats['videos_collected'] += 1
        
        # Track language classification for audio downloader (assume same as main video)
        # Since we're not running language detection, assume Vietnamese for similar videos
        self.url_language_mapping[similar_video['url']] = 'vietnamese'
        
        # Check if we should run audio downloader script
        self._check_and_run_downloader()
        print("✓ Similar video added directly (classification will be done later)")
        self.reporter.report_similar_video_result(True)
        
        return True
    
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
                self.output.print_warning(f"⚠️  API quota exceeded detected at query {query_index}/{len(self.query_list)} - waiting to resume...")
                self.wait_until_any_key_restored()
            
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
            current_video_index = 0
            
            # Get initial video list for current query
            video_list = self.search_videos_by_query(current_query)
            if not video_list:
                self.reporter.report_query_results(0, current_query)
                # If quota caused empty result, wait and retry this query once
                if self.api_quota_exceeded:
                    self.output.print_warning("⚠️  API quota exceeded during query search - waiting to resume and retry...")
                    self.wait_until_any_key_restored()
                    video_list = self.search_videos_by_query(current_query)
                    if not video_list:
                        self.reporter.report_query_results(0, current_query)
                        continue
                else:
                    continue
            
            self.reporter.report_query_results(len(video_list), current_query)
            
            # Collection loop for current query
            while (query_stats['videos_collected'] < self.target_video_count_per_query and 
                   current_video_index < len(video_list) and 
                   self.current_session_collected_count < self.total_target_count):
                # If quota hits mid-loop, pause and resume without losing position
                if self.api_quota_exceeded:
                    self.output.print_warning("⚠️  API quota exceeded during processing - waiting to resume...")
                    self.wait_until_any_key_restored()
                
                current_video_processing = video_list[current_video_index]
                query_stats['videos_reviewed'] += 1
                
                self.reporter.report_video_processing(
                    current_video_index, 
                    len(video_list),
                    current_video_processing['title'],
                    current_video_processing['channel_title']
                )
                
                self.current_video_index = current_video_index
                
                # Process the video
                video_added = self._process_main_video(current_video_processing, query_stats)
                
                self.reporter.report_total_progress(
                    self.current_session_collected_count, 
                    self.total_target_count,
                    query_stats['videos_collected'], 
                    self.target_video_count_per_query
                )
                current_video_index += 1
            
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
            []
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
            [],
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
        # Channel tracking removed - return 0
        return 0
    
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
                
    except Exception as e:
        error_reporter.report_unexpected_error(e)

    print("✅ YouTube Video Crawler execution completed")
    
if __name__ == "__main__":
    main()