#!/usr/bin/env python3
"""
YouTube Video Crawler for Children's Voice Content Collection

This module provides comprehensive functionality for collecting and analyzing YouTube videos
containing Vietnamese children's voices. It integrates with YouTube Data API v3 to search
for videos, downloads and analyzes audio content using machine learning models, and provides
detailed reporting and statistics.

Key Features:
    - Multi-query video collection with intelligent deduplication
    - Automated audio analysis for children's voice detection
    - Vietnamese language detection and filtering
    - Channel exploration for finding similar content
    - Real-time progress tracking and statistics
    - Comprehensive output analysis and reporting
    - Configurable target limits and collection criteria

Architecture:
    The module follows a modular design with specialized classes:
    - YouTubeVideoCrawler: Main orchestrator for video collection
    - OutputManager: Centralized output formatting and display
    - CollectionReporter: Handles collection progress and statistics reporting
    - ErrorReporter: Manages error reporting and exception handling
    - UserInputManager: Handles all user interaction and input validation
    - DebugLogger: Provides detailed debugging and logging capabilities

Workflow:
    1. User configuration (target counts, search queries, debug mode)
    2. YouTube API search for videos matching queries
    3. Audio download and analysis (language + children's voice detection)
    4. Channel exploration for finding similar content
    5. Real-time progress tracking and duplicate prevention
    6. Comprehensive reporting and statistics generation

Dependencies:
    - YouTube Data API v3 (requires YOUTUBE_API_KEY environment variable)
    - youtube_audio_downloader: For converting YouTube videos to audio
    - youtube_audio_classifier: For ML-based audio analysis
    - youtube_output_analyzer: For generating comprehensive reports

Usage:
    python youtube_video_crawler.py
    
Environment Variables:
    YOUTUBE_API_KEY: Required Google YouTube Data API v3 key

Output Files:
    - collected_video_urls.txt: List of collected video URLs
    - collection_report.txt: Human-readable collection summary
    - detailed_collection_results.json: Comprehensive statistics and metadata
    - query_efficiency_statistics.json: Per-query performance metrics

Author: Le Hoang Minh
Created: 2025
Version: 1.0
"""

import os
import requests
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union, Set
from dataclasses import dataclass
from youtube_audio_downloader import Config as AudioConfig, YoutubeAudioDownloader
from youtube_audio_classifier import AudioClassifier
from youtube_output_analyzer import YouTubeOutputAnalyzer, QueryStatistics
from youtube_output_validator import YouTubeURLValidator


# Configuration constants
class Config:
    """Configuration constants for the YouTube video crawler."""
    
    # API and URL constants
    YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"
    YOUTUBE_VIDEO_URL_PREFIX = "https://www.youtube.com/watch?v="
    MAX_RESULTS_PER_REQUEST = 50
    
    # File names (relative to the script's directory)
    _SCRIPT_DIR = Path(__file__).parent
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
class AnalysisResult:
    """Data class for audio analysis results."""
    is_vietnamese: bool
    detected_language: str
    has_children_voice: Optional[bool]
    confidence: float
    error: Optional[str]


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
    
    def report_collection_completion(self, total_collected: int) -> None:
        """Report completion of entire collection."""
        print(f"\nCollection completed! Videos collected in current session: {total_collected}")
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


class YouTubeVideoCrawler:
    """YouTube video searcher for collecting children's voice content."""
    
    def __init__(self, debug_mode: bool = False) -> None:
        """
        Initialize YouTube API searcher using Google's YouTube Data API v3.
        
        Args:
            debug_mode (bool): Enable debug logging
        """
        # Initialize output management
        self.output = OutputManager()
        self.reporter = CollectionReporter(self.output)
        self.error_reporter = ErrorReporter(self.output)
        self.input_manager = UserInputManager(self.output)
        
        # Initialize output analyzer
        self.analyzer = YouTubeOutputAnalyzer(Config.DEFAULT_OUTPUT_DIR)
        
        self.debug = DebugLogger(enabled=debug_mode)
        self.api_key = self._get_api_key()
        self.base_url = Config.YOUTUBE_API_BASE_URL
        
        # Initialize audio downloader
        audio_config = AudioConfig()
        self.audio_downloader = YoutubeAudioDownloader(audio_config)
        
        # Global variables for multiple query processing
        self.reviewed_channels: List[str] = []
        self.total_video_urls: List[str] = []
        self.collected_url_set: Set[str] = set()  # For fast duplicate checking
        
        # Load existing URLs from file if it exists
        self._load_existing_urls()
        
        # Track videos collected in current session only (not including pre-existing ones)
        self.current_session_collected_count = 0
        self.current_session_collected_urls: List[str] = []
        
        self.target_video_count_per_query = self.input_manager.get_target_count_per_query()
        self.query_list = self.input_manager.get_query_list()
        
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
        
        # Current processing state
        self.current_video: Optional[Dict] = None
        self.current_video_index = 0
        self.global_video_download_index = 0  # Global index for all video downloads to prevent file overlap
        self.start_time = time.time()
        self.start_datetime = datetime.now()
        
    def _get_api_key(self) -> str:
        """Get and validate API key from environment."""
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY environment variable not set")
        return api_key
    
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
        
    def analyze_video_audio(self, video: Dict, video_type: str = "main") -> AnalysisResult:
        """
        Download and analyze video audio for both language detection and children's voice detection.
        This method downloads the audio once and performs both analyses to avoid duplicate downloads.
        
        Args:
            video (Dict): Video information dictionary
            video_type (str): Type of video being processed ("main" or "similar")
            
        Returns:
            AnalysisResult: Combined analysis results
        """
        try:
            # Convert YouTube video to .wav file once for both analyses
            # Use global download index to prevent file overlap
            wav_file_path = self.audio_downloader.download_audio_from_yturl(video['url'], index=self.global_video_download_index)
            current_download_index = self.global_video_download_index
            self.global_video_download_index += 1  # Increment for next download
            
            if not wav_file_path:
                self.error_reporter.report_audio_download_failure()
                return AnalysisResult(
                    is_vietnamese=False,
                    detected_language='unknown',
                    has_children_voice=None,
                    confidence=0,
                    error='Failed to download audio'
                )
            
            # Use classifier for both language detection and children's voice detection
            classifier = AudioClassifier()
            
            # Language detection
            is_vietnamese = classifier.is_vietnamese(wav_file_path)
            
            # Children's voice detection (only if language detection succeeds)
            children_voice_result = None
            if is_vietnamese is not None:
                children_voice_result = classifier.is_child_audio(wav_file_path)
            
            # Prepare results
            language_result = {
                'is_vietnamese': is_vietnamese if is_vietnamese is not None else False,
                'detected_language': 'vi' if is_vietnamese else 'other',
                'confidence': 1.0 if is_vietnamese else 0.0,
                'error': None if is_vietnamese is not None else 'Language detection failed'
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
            
            return AnalysisResult(
                is_vietnamese=language_result['is_vietnamese'],
                detected_language=language_result['detected_language'],
                has_children_voice=children_voice_result,
                confidence=language_result['confidence'],
                error=language_result['error']
            )
            
        except Exception as e:
            self.error_reporter.report_audio_analysis_error(e)
            self.debug.log_error("Audio analysis", e)
            return AnalysisResult(
                is_vietnamese=False,
                detected_language='unknown',
                has_children_voice=None,
                confidence=0,
                error=str(e)
            )

    def search_videos_by_query(self, query: str, max_results: int = 50) -> List[Dict]:
        """
        Search videos on YouTube using the given query.
        
        Args:
            query (str): Search query
            max_results (int): Maximum number of results to return
            
        Returns:
            List[Dict]: List of video information dictionaries
        """
        url = f"{self.base_url}/search"
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': min(max_results, Config.MAX_RESULTS_PER_REQUEST),  # YouTube API max is 50 per request
            'key': self.api_key
        }
        
        try:
            self.debug.log_api_request(url, params)
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            items = data.get('items', [])
            self.debug.log_api_response(response.status_code, list(data.keys()), len(items))
            
            videos = []
            for item in items:
                video_info = self._extract_video_info(item)
                videos.append(video_info)
                self.debug.log_video_added(video_info['title'])
            
            self.debug.log_final_count(len(videos))
            return videos
            
        except requests.exceptions.RequestException as e:
            self.error_reporter.report_api_error(e)
            response_text = getattr(e.response, 'text', '') if hasattr(e, 'response') and e.response else ''
            self.debug.log_error("API request", e, response_text)
            return []
    
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
        
        try:
            self.debug.log_api_request(url, params)
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            items = data.get('items', [])
            self.debug.log_api_response(response.status_code, list(data.keys()), len(items))
            
            videos = []
            for item in items:
                video_info = self._extract_video_info(item)
                videos.append(video_info)
                self.debug.log_video_added(video_info['title'])
            
            self.debug.log_final_count(len(videos))
            return videos
            
        except requests.exceptions.RequestException as e:
            self.error_reporter.report_channel_search_error(e)
            response_text = getattr(e.response, 'text', '') if hasattr(e, 'response') and e.response else ''
            self.debug.log_error("Channel search", e, response_text)
            return []
        except Exception as e:
            self.error_reporter.report_unexpected_error(e)
            self.debug.log_error("Unexpected", e)
            return []
    
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
            
            # Mark channel as reviewed and process similar videos
            added_count = self._process_similar_videos(video, query_stats)
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
                continue
            
            self.reporter.report_query_results(len(video_list), current_query)
            
            # Collection loop for current query
            while (query_stats['videos_collected'] < self.target_video_count_per_query and 
                   video_index_current < len(video_list) and 
                   self.current_session_collected_count < self.total_target_count):
                
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
            self.start_datetime
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
        
        self.reporter.report_collection_completion(self.current_session_collected_count)
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
    output_manager = OutputManager()
    error_reporter = ErrorReporter(output_manager)
    input_manager = UserInputManager(output_manager)
    
    try:
        # Ask user about debug mode
        debug_mode = input_manager.get_debug_mode_preference()
        
        # Initialize searcher (this will check for API key and get user inputs)
        searcher = YouTubeVideoCrawler(debug_mode=debug_mode)
        
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
            
    except ValueError as e:
        error_reporter.report_configuration_error(e)
    except Exception as e:
        error_reporter.report_unexpected_error(e)

if __name__ == "__main__":
    main()