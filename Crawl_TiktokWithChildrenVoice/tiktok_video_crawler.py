#!/usr/bin/env python3
"""
TikTok Video Crawler for Children's Voice Content Collection

This module provides comprehensive functionality for collecting and analyzing TikTok videos
onta            \"description\": \"Default configuration for TikTok Children's Voice Crawler with Keyword Search\"ning Vietese children's voices. It integrates with TikTok RapidA        self.output.print_progress(f\"Collecting videos from keyword: '{keyword}' (EXHAUSTIVE mode)\")       self.output.print_progress(f\"Collecting videos from keyword: '{keyword}' (EXHAUSTIVE mode)\")I to search
for videos, downloads and analyzes adio content using machine learning models, and provides
detailed reporting and statistics.

Based on the proven architecture of the YouTube Children's Voice Crawler, adapted for TikTok.

Author: Generated for TikTok Children's Voice Crawler
Version: 1.0
"""

import json
import os
import time
import threading
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Union, Set, Any, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import project modules
try:
    from env_config import config
    USE_ENV_CONFIG = True
except ImportError:
    config = None
    USE_ENV_CONFIG = False

try:
    from tiktok_api_client import TikTokAPIClient
    from tiktok_audio_classifier import TikTokAudioClassifier, AudioAnalysisResult
    from tiktok_video_downloader import TikTokVideoDownloader
    API_CLIENT_AVAILABLE = True
except ImportError as e:
    API_CLIENT_AVAILABLE = False
    print(f"❌ Failed to import TikTok modules: {e}")
    print("Please ensure all required modules are available")



# Constants
DEFAULT_MAX_WORKERS = 4
DEFAULT_MAX_VIDEOS = 100
DEFAULT_CHILDREN_VOICE_THRESHOLD = 0.5
DEFAULT_AGE_THRESHOLD = 0.3
PROGRESS_UPDATE_INTERVAL = 10  # Update progress every N items
MIN_VALID_VIDEO_DURATION = 1.0  # Minimum duration for valid videos
DEFAULT_OUTPUT_DIR = "./tiktok_url_outputs"
DEFAULT_FINAL_AUDIO_DIR = "./final_audio_files"


# Configuration constants
class Config:
    """Configuration constants for the TikTok video crawler."""
    
    # File names (relative to the script's directory)
    _SCRIPT_DIR = Path(__file__).parent
    DEFAULT_CONFIG_FILE = str(_SCRIPT_DIR / "crawler_config.json")
    DEFAULT_URLS_FILE = str(_SCRIPT_DIR / "tiktok_url_outputs/collected_video_urls.txt")
    DEFAULT_REPORT_FILE = str(_SCRIPT_DIR / "tiktok_url_outputs/collection_report.txt")
    DEFAULT_DETAILED_RESULTS_FILE = str(_SCRIPT_DIR / "tiktok_url_outputs/detailed_collection_results.json")
    DEFAULT_STATISTICS_FILE = str(_SCRIPT_DIR / "tiktok_url_outputs/query_efficiency_statistics.json")
    
    # Additional file paths
    DEFAULT_OUTPUT_DIR = _SCRIPT_DIR / "tiktok_url_outputs"
    DEFAULT_MAIN_URLS_FILE = str(DEFAULT_OUTPUT_DIR / "multi_query_collected_video_urls.txt")
    DEFAULT_MAIN_DETAILED_FILE = str(DEFAULT_OUTPUT_DIR / "multi_query_detailed_results.json")
    DEFAULT_BACKUP_FILE_PREFIX = str(DEFAULT_OUTPUT_DIR / "backup")
    
    # Processing constants
    MAX_RESULTS_PER_REQUEST = 50
    MIN_TARGET_COUNT = 1
    MAX_RECOMMENDED_PER_QUERY = 100
    
    # Debug and logging
    DEBUG_PREFIX = "🔍 DEBUG: "
    
    # Default values
    DEFAULT_QUERY = "thiếu nhi"


@dataclass
class CrawlerConfig:
    """Data class for crawler configuration loaded from JSON file."""
    debug_mode: bool
    target_videos_per_query: int
    keyword_queries: List[str] = field(default_factory=list)
    max_recommended_per_query: int = 100
    min_target_count: int = 1
    download_method: str = "direct_api"
    enable_language_detection: bool = True
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
    rate_limiting: Optional[Dict[str, Any]] = None
    video_filters: Optional[Dict[str, Any]] = None
    transcription_services: Optional[Dict[str, Any]] = None
    user_agent_settings: Optional[Dict[str, Any]] = None


class ConfigLoader:
    """Loads configuration from JSON file."""
    
    def __init__(self, output_manager, config_file_path: Optional[str] = None):
        """Initialize with output manager and optional config file path."""
        self.output = output_manager
        self.config_file_path = config_file_path or Config.DEFAULT_CONFIG_FILE
    
    def load_config(self) -> CrawlerConfig:
        """Load configuration from JSON file or create default."""
        config_path = Path(self.config_file_path)
        
        if not config_path.exists():
            self.output.print_info(f"Creating default config file: {self.config_file_path}")
            self._create_default_config(config_path)
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Validate required fields
            required_fields = ['debug_mode', 'target_videos_per_query']
            for field in required_fields:
                if field not in config_data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create config object
            crawler_config = CrawlerConfig(
                debug_mode=config_data.get('debug_mode', False),
                target_videos_per_query=config_data.get('target_videos_per_query', 50),
                keyword_queries=config_data.get('keyword_queries', []),
                max_recommended_per_query=config_data.get('max_recommended_per_query', 100),
                min_target_count=config_data.get('min_target_count', 1),
                download_method=config_data.get('download_method', 'direct_api'),
                enable_language_detection=config_data.get('enable_language_detection', True),
                user_agent=config_data.get('user_agent', ''),
                rate_limiting=config_data.get('rate_limiting', {}),
                video_filters=config_data.get('video_filters', {}),
                transcription_services=config_data.get('transcription_services', {}),
                user_agent_settings=config_data.get('user_agent_settings', {})
            )
            
            self.output.print_info(f"✅ Configuration loaded from: {self.config_file_path}")
            return crawler_config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ValueError(f"Error loading config file: {e}")
    
    def _create_default_config(self, config_path: Path) -> None:
        """Create a default configuration file."""
        default_config = {
            "debug_mode": True,
            "target_videos_per_query": 50,
            "enable_language_detection": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
            "search_queries": [
                "moxierobot",
                "farmeesvietnam", 
                "popskids",
                "nidovietnam",
                "babyccinotv"
            ],

            "max_recommended_per_query": 100,
            "min_target_count": 1,
            "download_method": "direct_api",
            "rate_limiting": {
                "enabled": True,
                "min_delay_ms": 1000,
                "max_delay_ms": 3000
            },
            "video_filters": {
                "min_duration_seconds": 3,
                "max_duration_seconds": 600,
                "min_views": 100
            },
            "transcription_services": {
                "preferred_service": "groq",
                "fallback_service": "whisper"
            },
            "enable_channel_discovery": True,
            "auto_add_promising_channels": True,
            "channel_quality_threshold": 0.3,
            "max_channel_videos": 50,
            "description": "Default configuration for TikTok Children's Voice Crawler with Channel Discovery"
        }
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)


class OutputManager:
    """Manages console output and logging."""
    
    def __init__(self, debug_mode: bool = False):
        """Initialize output manager."""
        self.debug_mode = debug_mode
        self.start_time = time.time()
    
    def print_header(self, title: str, width: int = 60) -> None:
        """Print formatted header."""
        print("\n" + "=" * width)
        print(f"{title:^{width}}")
        print("=" * width)
    
    def print_info(self, message: str) -> None:
        """Print info message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ℹ️  {message}")
    
    def print_progress(self, message: str) -> None:
        """Print progress message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] 🔄 {message}")
    
    def print_success(self, message: str) -> None:
        """Print success message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ✅ {message}")
    
    def print_warning(self, message: str) -> None:
        """Print warning message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ⚠️  {message}")
    
    def print_error(self, message: str) -> None:
        """Print error message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ❌ {message}")
    
    def debug_log(self, message: str) -> None:
        """Print debug message if debug mode is enabled."""
        if self.debug_mode:
            timestamp = datetime.now().strftime('%H:%M:%S')
            print(f"[{timestamp}] {Config.DEBUG_PREFIX}{message}")
    
    def report_configuration(self, target_per_query: int, total_target: int, queries: List[str]) -> None:
        """Report configuration summary."""
        self.print_header("TikTok Crawler Configuration")
        print(f"📊 Target videos per query: {target_per_query}")
        print(f"📊 Total queries: {len(queries)}")
        print(f"📊 Total target videos: {total_target}")
        print(f"🔍 Debug mode: {'Enabled' if self.debug_mode else 'Disabled'}")
        print(f"\n📝 Channel queries ({len(queries)}):")
        for i, query in enumerate(queries, 1):
            print(f"   {i:2d}. {query}")
        print()


class TikTokVideoCollector:
    """Main TikTok video collector with children's voice detection."""
    
    def __init__(self):
        """Initialize the TikTok video collector."""
        # Initialize output manager first
        self.output = OutputManager(debug_mode=True)  # Will be updated with actual config
        
        # Load configuration
        self.config_loader = ConfigLoader(self.output)
        try:
            self.config = self.config_loader.load_config()
        except Exception as e:
            self.output.print_error(f"Failed to load configuration: {e}")
            raise
        
        # Update output manager with actual debug mode
        self.output.debug_mode = self.config.debug_mode
        
        # Initialize components
        if not API_CLIENT_AVAILABLE:
            raise RuntimeError("Required TikTok modules are not available")
        
        try:
            self.api_client = TikTokAPIClient(self.output)
            self.audio_classifier = TikTokAudioClassifier(self.output)
            self.video_downloader = TikTokVideoDownloader(self.output)
        except Exception as e:
            self.output.print_error(f"Failed to initialize components: {e}")
            raise
        

        
        # Create output directory
        Config.DEFAULT_OUTPUT_DIR.mkdir(exist_ok=True)
        
        # Collection tracking
        self.collected_videos: List[Dict] = []
        self.collected_urls: Set[str] = set()
        self.total_videos_analyzed = 0
        self.total_videos_collected = 0
        
        # Statistics tracking
        self.total_vietnamese_videos = 0
        self.total_children_voice_videos = 0
        self.total_processing_time = 0.0
        
        # Threading
        self.download_index_lock = threading.Lock()
        self.global_download_index = 0
        
        # Report configuration
        all_queries = [f"'{kw}'" for kw in self.config.keyword_queries]
        total_target = self.config.target_videos_per_query * len(all_queries)
        self.output.report_configuration(self.config.target_videos_per_query, total_target, all_queries)
        
        self.output.print_success("TikTok Video Collector initialized successfully")
    
    def _get_next_download_index(self) -> int:
        """Get next unique download index (thread-safe)."""
        with self.download_index_lock:
            self.global_download_index += 1
            return self.global_download_index
    
    def collect_videos_from_user(self, username: str, max_videos: int) -> List[Dict]:
        """
        Collect videos from a specific TikTok user.
        
        Args:
            username (str): TikTok username (without @)
            max_videos (int): Maximum number of videos to collect
            
        Returns:
            List[Dict]: List of video information
        """
        self.output.print_progress(f"Collecting videos from user: @{username}")
        
        try:
            # Get user videos from API
            videos = self.api_client.get_user_videos(username, count=max_videos)
            
            if not videos:
                self.output.print_warning(f"No videos found for user: @{username}")
                return []
            
            # Filter videos based on configuration
            filtered_videos = self._filter_videos(videos)
            
            self.output.print_info(f"Found {len(filtered_videos)} videos from @{username} (filtered from {len(videos)})")
            return filtered_videos
            
        except Exception as e:
            self.output.print_error(f"Failed to collect videos from @{username}: {e}")
            return []
    


    def collect_videos_from_keyword(self, keyword: str, max_videos: int) -> List[Dict]:
        """
        Collect videos from a keyword search.
        
        Args:
            keyword (str): Keyword or phrase to search for
            max_videos (int): Maximum number of videos to collect
            
        Returns:
            List[Dict]: List of video information
        """
        self.output.print_progress(f"Collecting videos from keyword: '{keyword}'")
        
        try:
            # Always use exhaustive pagination for complete extraction
            if max_videos > 50 or max_videos == 0:
                # Use exhaustive pagination to get ALL available results
                self.output.print_info(f"Using EXHAUSTIVE pagination for '{keyword}' (max: {max_videos if max_videos > 0 else 'ALL'})")
                videos = self.api_client.search_videos_by_keyword_with_pagination(keyword, max_videos if max_videos > 0 else None)
            else:
                # For smaller requests, use single request
                response = self.api_client.search_videos_by_keyword(keyword, count=max_videos)
                videos = response.get('data', {}).get('videos', []) if isinstance(response, dict) else []
            
            if not videos:
                self.output.print_warning(f"No videos found for keyword: '{keyword}'")
                return []
            
            # Filter videos based on configuration
            filtered_videos = self._filter_videos(videos)
            
            self.output.print_info(f"Found {len(filtered_videos)} videos for '{keyword}' (filtered from {len(videos)})")
            return filtered_videos
            
        except Exception as e:
            self.output.print_error(f"Failed to collect videos for '{keyword}': {e}")
            return []
    
    def _filter_videos(self, videos: List[Dict]) -> List[Dict]:
        """
        Filter videos based on configuration criteria.
        
        Args:
            videos (List[Dict]): Raw video list
            
        Returns:
            List[Dict]: Filtered video list
        """
        if not self.config.video_filters:
            return videos
        
        filtered = []
        filters = self.config.video_filters
        
        for video in videos:
            # Duration filter
            duration = video.get('duration', 0)
            min_duration = filters.get('min_duration_seconds', 0)
            max_duration = filters.get('max_duration_seconds', float('inf'))
            
            if not (min_duration <= duration <= max_duration):
                continue
            
            # View count filter
            min_views = filters.get('min_views', 0)
            views = video.get('play_count', 0)
            if views < min_views:
                continue
            
            # Content filter (exclude keywords)
            exclude_keywords = filters.get('exclude_keywords', [])
            description = video.get('description', '').lower()
            title = video.get('title', '').lower()
            
            if any(keyword.lower() in description or keyword.lower() in title for keyword in exclude_keywords):
                continue
            
            # Skip duplicates
            if video['url'] in self.collected_urls:
                continue
            
            filtered.append(video)
        
        return filtered
    
    def analyze_video_audio(self, video: Dict) -> AudioAnalysisResult:
        """
        Analyze video audio for Vietnamese language and children's voice.
        
        Args:
            video (Dict): Video information
            
        Returns:
            AudioAnalysisResult: Analysis results
        """
        self.output.debug_log(f"Analyzing video: {video['title'][:50]}...")
        
        try:
            # Download and convert video to audio
            download_index = self._get_next_download_index()
            audio_path, duration = self.video_downloader.download_and_convert_audio(video, download_index)
            
            if not audio_path:
                return AudioAnalysisResult(
                    is_vietnamese=False,
                    detected_language=None,
                    has_children_voice=False,
                    confidence=0.0,
                    total_analysis_time=0.0,
                    children_detection_time=0.0,
                    video_length_seconds=duration or 0.0,
                    error="Failed to download/convert video"
                )
            
            # Analyze audio
            analysis_result = self.audio_classifier.analyze_audio(audio_path)
            
            # Clean up temporary audio file
            self.video_downloader.cleanup_audio_file(audio_path)
            
            return analysis_result
            
        except Exception as e:
            self.output.print_error(f"Error analyzing video {video['url']}: {e}")
            return AudioAnalysisResult(
                is_vietnamese=False,
                detected_language=None,
                has_children_voice=False,
                confidence=0.0,
                total_analysis_time=0.0,
                children_detection_time=0.0,
                video_length_seconds=0.0,
                error=str(e)
            )
    
    def process_video(self, video: Dict) -> bool:
        """
        Process a single video through the analysis pipeline.
        
        Args:
            video (Dict): Video information
            
        Returns:
            bool: True if video was collected, False otherwise
        """
        self.total_videos_analyzed += 1
        
        # Skip duplicates
        if video['url'] in self.collected_urls:
            self.output.debug_log("Skipping duplicate video")
            return False
        
        # Analyze audio
        analysis_result = self.analyze_video_audio(video)
        
        # Update statistics
        self.total_processing_time += analysis_result.total_analysis_time
        
        # Check if analysis failed
        if analysis_result.error:
            self.output.print_warning(f"Analysis failed: {analysis_result.error}")
            return False
        
        # Check language detection (if enabled)
        if self.config.enable_language_detection:
            if not analysis_result.is_vietnamese:
                self.output.debug_log(f"Video is not Vietnamese (detected: {analysis_result.detected_language})")
                return False
            else:
                self.total_vietnamese_videos += 1
                self.output.debug_log("✓ Video is Vietnamese")
        
        # Check children's voice detection
        if not analysis_result.has_children_voice:
            self.output.debug_log(f"No children's voice detected (confidence: {analysis_result.confidence:.2f})")
            
            # Still track channel for discovery (as non-qualified)

            
            return False
        
        # Video meets criteria - collect it
        self.total_children_voice_videos += 1
        is_qualified = True  # Mark as qualified video
        
        # Add to collection
        video_record = {
            **video,
            'analysis_result': {
                'is_vietnamese': analysis_result.is_vietnamese,
                'detected_language': analysis_result.detected_language,
                'has_children_voice': analysis_result.has_children_voice,
                'confidence': analysis_result.confidence,
                'analysis_time': analysis_result.total_analysis_time,
                'transcription': analysis_result.transcription
            },
            'collected_at': datetime.now().isoformat()
        }
        
        self.collected_videos.append(video_record)
        self.collected_urls.add(video['url'])
        self.total_videos_collected += 1
        
        # Channel discovery integration

        
        # Save URL immediately
        self._save_url_to_file(video['url'])
        
        self.output.print_success(f"✓ Collected video: {video['title'][:50]}... (confidence: {analysis_result.confidence:.2f})")
        return True
    
    def _save_url_to_file(self, url: str) -> None:
        """Save URL immediately to file."""
        try:
            filepath = Path(Config.DEFAULT_MAIN_URLS_FILE)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with filepath.open('a', encoding='utf-8') as f:
                f.write(url + '\n')
        except Exception as e:
            self.output.print_error(f"Error saving URL to file: {e}")
    
    def run_collection(self) -> List[Dict]:
        """
        Run the complete video collection process.
        
        Returns:
            List[Dict]: Collected videos with analysis results
        """
        self.output.print_header("Starting TikTok Children's Voice Collection")
        start_time = time.time()
        
        try:

            # Process keyword queries
            for i, keyword in enumerate(self.config.keyword_queries, 1):
                self.output.print_header(f"Processing Keyword {i}/{len(self.config.keyword_queries)}: '{keyword}'")
                
                # Collect videos from keyword
                keyword_videos = self.collect_videos_from_keyword(keyword, self.config.target_videos_per_query)
                
                # Process each video
                for video in keyword_videos:
                    self.process_video(video)
                    
                    # Check if we've reached our target
                    if self.total_videos_collected >= self.config.target_videos_per_query:
                        self.output.print_info(f"Reached target for '{keyword}'")
                        break
                
                # Progress report
                self.output.print_info(f"Progress: {self.total_videos_collected} collected, {self.total_videos_analyzed} analyzed")
            
            # Final processing
            total_time = time.time() - start_time
            
            # Channel discovery post-processing


            
            self._generate_final_report(total_time)
            self._save_results()
            
            return self.collected_videos
            
        except KeyboardInterrupt:
            self.output.print_warning("Collection interrupted by user")
            self._generate_final_report(time.time() - start_time)
            self._save_results()
            return self.collected_videos
        except Exception as e:
            self.output.print_error(f"Collection failed: {e}")
            raise
        finally:
            # Cleanup
            self.video_downloader.cleanup_temp_files()
    
    def _generate_final_report(self, total_time: float) -> None:
        """Generate and display final collection report."""
        self.output.print_header("Collection Complete - Final Report")
        
        # Basic statistics
        print(f"📊 Collection Statistics:")
        print(f"   Total Videos Analyzed: {self.total_videos_analyzed}")
        print(f"   Total Videos Collected: {self.total_videos_collected}")
        print(f"   Vietnamese Videos: {self.total_vietnamese_videos}")
        print(f"   Children's Voice Videos: {self.total_children_voice_videos}")
        print(f"   Collection Rate: {(self.total_videos_collected / max(self.total_videos_analyzed, 1)) * 100:.1f}%")
        print(f"   Total Processing Time: {total_time:.1f}s")
        
        if self.total_videos_analyzed > 0:
            avg_time_per_video = self.total_processing_time / self.total_videos_analyzed
            print(f"   Average Time per Video: {avg_time_per_video:.2f}s")
        
        # API usage statistics
        print(f"\n🔧 API Usage:")
        api_stats = self.api_client.get_api_usage_stats()
        print(f"   API Requests: {api_stats['requests_made']}")
        print(f"   API Success Rate: {api_stats['success_rate']:.1f}%")
        print(f"   API Keys Used: {api_stats['current_api_key_index'] + 1}/{api_stats['total_api_keys']}")
        
        # Download statistics
        print(f"\n📥 Download Statistics:")
        download_stats = self.video_downloader.get_download_statistics()
        print(f"   Downloads Attempted: {download_stats['total_downloads']}")
        print(f"   Downloads Successful: {download_stats['successful_downloads']}")
        print(f"   Download Success Rate: {download_stats['success_rate']:.1f}%")
        
        # Audio analysis statistics
        print(f"\n🎵 Audio Analysis:")
        classifier_stats = self.audio_classifier.get_statistics()
        print(f"   Audio Analyses: {classifier_stats['total_analyses']}")
        print(f"   Analysis Success Rate: {classifier_stats['success_rate']:.1f}%")
        print(f"   Processing Device: {classifier_stats['device']}")
        
        # Channel discovery statistics


    
    def _save_results(self) -> None:
        """Save collection results to files."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        try:
            # Save detailed results
            detailed_file = Config.DEFAULT_OUTPUT_DIR / f"{timestamp}_detailed_collection_results.json"
            with detailed_file.open('w', encoding='utf-8') as f:
                json.dump({
                    'collection_summary': {
                        'total_analyzed': self.total_videos_analyzed,
                        'total_collected': self.total_videos_collected,
                        'vietnamese_videos': self.total_vietnamese_videos,
                        'children_voice_videos': self.total_children_voice_videos,
                        'collection_time': datetime.now().isoformat()
                    },
                    'configuration': {
                        'target_per_query': self.config.target_videos_per_query,

                        'keyword_queries': self.config.keyword_queries,
                        'enable_language_detection': self.config.enable_language_detection
                    },
                    'collected_videos': self.collected_videos
                }, f, indent=2, ensure_ascii=False)
            
            self.output.print_success(f"Detailed results saved: {detailed_file.name}")
            
            # Save summary report
            report_file = Config.DEFAULT_OUTPUT_DIR / f"{timestamp}_collection_report.txt"
            with report_file.open('w', encoding='utf-8') as f:
                f.write("TikTok Children's Voice Collection Report\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Collection Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total Videos Analyzed: {self.total_videos_analyzed}\n")
                f.write(f"Total Videos Collected: {self.total_videos_collected}\n")
                f.write(f"Vietnamese Videos: {self.total_vietnamese_videos}\n")
                f.write(f"Children's Voice Videos: {self.total_children_voice_videos}\n")
                f.write(f"Collection Rate: {(self.total_videos_collected / max(self.total_videos_analyzed, 1)) * 100:.1f}%\n\n")
                
                

                    
                
                if self.config.keyword_queries:
                    f.write("\nKeyword Queries:\n")
                    for i, keyword in enumerate(self.config.keyword_queries, 1):
                        f.write(f"  {i}. '{keyword}'\n")
                
                f.write("\nCollected Video URLs:\n")
                for video in self.collected_videos:
                    f.write(f"{video['url']}\n")
            
            self.output.print_success(f"Report saved: {report_file.name}")
            
        except Exception as e:
            self.output.print_error(f"Error saving results: {e}")
    

    

    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get current collection statistics."""
        return {
            'total_analyzed': self.total_videos_analyzed,
            'total_collected': self.total_videos_collected,
            'vietnamese_videos': self.total_vietnamese_videos,
            'children_voice_videos': self.total_children_voice_videos,
            'collection_rate': (self.total_videos_collected / max(self.total_videos_analyzed, 1)) * 100,
            'average_processing_time': self.total_processing_time / max(self.total_videos_analyzed, 1)
        }


def main():
    """Main function to run the TikTok video crawler."""
    try:
        print("🚀 Starting TikTok Children's Voice Crawler...")
        
        # Initialize and run collector
        collector = TikTokVideoCollector()
        collected_videos = collector.run_collection()
        
        # Print final summary
        stats = collector.get_collection_stats()
        print(f"\n🎉 Collection completed successfully!")
        print(f"   Collected {stats['total_collected']} videos from {stats['total_analyzed']} analyzed")
        print(f"   Success rate: {stats['collection_rate']:.1f}%")
        
        # Print output file locations
        print(f"\n📁 Output files saved in: {Config.DEFAULT_OUTPUT_DIR}")
        print(f"   - Collected URLs: {Config.DEFAULT_MAIN_URLS_FILE}")
        print(f"   - Detailed results: Check timestamped JSON files")
        print(f"   - Collection report: Check timestamped TXT files")
        
        return collected_videos
        
    except KeyboardInterrupt:
        print("\n⚠️ Collection interrupted by user")
        return []
    except Exception as e:
        print(f"\n❌ Collection failed: {e}")
        import traceback
        traceback.print_exc()
        return []


if __name__ == "__main__":
    main()