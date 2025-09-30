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
import csv
import shutil
import pickle
from datetime import datetime, timedelta
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

# Forever running constants
KEY_TEST_INTERVAL = 300  # Test keys every 5 minutes when exhausted
STATE_SAVE_INTERVAL = 60  # Save state every minute
QUOTA_RESET_WAIT = 3600  # Wait 1 hour before retesting exhausted keys


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
    DEFAULT_FINAL_AUDIO_DIR = _SCRIPT_DIR / "final_audio_files"
    DEFAULT_MAIN_URLS_FILE = str(DEFAULT_OUTPUT_DIR / "multi_query_collected_video_urls.txt")
    DEFAULT_MAIN_DETAILED_FILE = str(DEFAULT_OUTPUT_DIR / "multi_query_detailed_results.json")
    DEFAULT_BACKUP_FILE_PREFIX = str(DEFAULT_OUTPUT_DIR / "backup")
    DEFAULT_MANIFEST_CSV = str(DEFAULT_FINAL_AUDIO_DIR / "manifest.csv")
    
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
    download_method: str = "yt_dlp"
    enable_language_detection: bool = True
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
    rate_limiting: Optional[Dict[str, Any]] = None
    video_filters: Optional[Dict[str, Any]] = None
    transcription_services: Optional[Dict[str, Any]] = None
    user_agent_settings: Optional[Dict[str, Any]] = None
    # Channel discovery configuration
    enable_channel_discovery: bool = True
    auto_add_promising_channels: bool = True
    channel_quality_threshold: float = 0.3
    max_channel_videos: int = 50
    exhaustive_channel_analysis: bool = True
    # Forever running configuration
    enable_forever_mode: bool = False
    quota_monitoring: bool = True
    auto_resume: bool = True
    key_test_interval: int = 300
    state_save_interval: int = 60


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
                download_method=config_data.get('download_method', 'yt_dlp'),
                enable_language_detection=config_data.get('enable_language_detection', True),
                user_agent=config_data.get('user_agent', ''),
                rate_limiting=config_data.get('rate_limiting', {}),
                video_filters=config_data.get('video_filters', {}),
                transcription_services=config_data.get('transcription_services', {}),
                user_agent_settings=config_data.get('user_agent_settings', {}),
                # Channel discovery configuration
                enable_channel_discovery=config_data.get('enable_channel_discovery', True),
                auto_add_promising_channels=config_data.get('auto_add_promising_channels', True),
                channel_quality_threshold=config_data.get('channel_quality_threshold', 0.3),
                max_channel_videos=config_data.get('max_channel_videos', 50),
                exhaustive_channel_analysis=config_data.get('exhaustive_channel_analysis', True),
                # Forever running configuration
                enable_forever_mode=config_data.get('enable_forever_mode', False),
                quota_monitoring=config_data.get('quota_monitoring', True),
                auto_resume=config_data.get('auto_resume', True),
                key_test_interval=config_data.get('key_test_interval', 300),
                state_save_interval=config_data.get('state_save_interval', 60)
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
            "download_method": "yt_dlp",
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
            "exhaustive_channel_analysis": True,
            "enable_forever_mode": False,
            "quota_monitoring": True,
            "auto_resume": True,
            "key_test_interval": 300,
            "state_save_interval": 60,
            "description": "Default configuration for TikTok Children's Voice Crawler with Channel Discovery and Forever Running Mode"
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
        Config.DEFAULT_FINAL_AUDIO_DIR.mkdir(exist_ok=True)
        
        # Initialize manifest tracking
        self.manifest_file = Config.DEFAULT_MANIFEST_CSV
        self.downloaded_urls = self._load_manifest()
        
        # Collection tracking
        self.collected_videos: List[Dict] = []
        self.collected_urls: Set[str] = self._load_existing_collected_urls()  # Load existing URLs to prevent duplicates
        self.total_videos_analyzed = 0
        self.total_videos_collected = 0
        
        # Channel discovery tracking
        self.processed_channels: Set[str] = set()  # Track channels we've already processed
        self.promising_channels: Set[str] = set()  # Channels with qualifying videos
        self.channel_discovery_stats = {
            'channels_discovered': 0,
            'channels_processed': 0,
            'videos_from_channel_discovery': 0
        }
        
        # Statistics tracking
        self.total_vietnamese_videos = 0
        self.total_children_voice_videos = 0
        self.total_processing_time = 0.0
        
        # Failure tracking for graceful degradation
        self.consecutive_download_failures = 0
        self.max_consecutive_failures = 10  # Stop if too many consecutive failures
        self.total_download_failures = 0
        
        # Forever running and quota monitoring
        self.is_running = False
        self.quota_exhausted = False
        self.exhausted_keys = set()  # Track which keys are exhausted
        self.last_key_test = datetime.now()
        self.state_file = Config.DEFAULT_OUTPUT_DIR / "crawler_state.json"
        self.quota_monitor_thread = None
        self.state_save_thread = None
        self.resume_checkpoint = None  # Store current processing position
        
        # Threading
        self.download_index_lock = threading.Lock()
        self.global_download_index = 0
        
        # Report configuration
        all_queries = [f"'{kw}'" for kw in self.config.keyword_queries]
        total_target = self.config.target_videos_per_query * len(all_queries)
        self.output.report_configuration(self.config.target_videos_per_query, total_target, all_queries)
        
        # Report channel discovery configuration
        if self.config.enable_channel_discovery:
            self.output.print_info(f"🎯 Channel discovery: Enabled")
            self.output.print_info(f"🎯 Exhaustive channel analysis: {'Yes' if self.config.exhaustive_channel_analysis else f'Max {self.config.max_channel_videos} videos per channel'}")
            self.output.print_info(f"🎯 Channel quality threshold: {self.config.channel_quality_threshold}")
        else:
            self.output.print_info(f"🎯 Channel discovery: Disabled")
        
        self.output.print_success("TikTok Video Collector initialized successfully")
    
    def _load_manifest(self) -> Set[str]:
        """Load existing manifest CSV and return set of downloaded URLs."""
        downloaded_urls = set()
        
        if Path(self.manifest_file).exists():
            try:
                with open(self.manifest_file, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('status') == 'success':
                            downloaded_urls.add(row.get('url', ''))
                self.output.print_info(f"📋 Loaded {len(downloaded_urls)} existing downloads from manifest")
            except Exception as e:
                self.output.print_error(f"Error loading manifest: {e}")
        else:
            # Create manifest file with headers
            self._create_manifest_headers()
            self.output.print_info("📋 Created new manifest file")
        
        return downloaded_urls
    
    def _load_existing_collected_urls(self) -> Set[str]:
        """Load existing URLs from multi_query_collected_video_urls.txt to prevent duplicates."""
        existing_urls = set()
        urls_file = Path(Config.DEFAULT_MAIN_URLS_FILE)
        
        if urls_file.exists():
            try:
                with open(urls_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        url = line.strip()
                        if url:
                            existing_urls.add(url)
                self.output.print_info(f"📋 Loaded {len(existing_urls)} existing URLs from {urls_file.name}")
            except Exception as e:
                self.output.print_warning(f"Error loading existing URLs: {e}")
        else:
            self.output.print_info(f"📋 No existing URLs file found at {urls_file}")
        
        return existing_urls
    
    def _generate_unique_audio_filename(self, video: Dict, from_channel_discovery: bool = False) -> str:
        """Generate a unique, consistent filename for audio files.
        
        Format: {timestamp}_{sequential_id}_{username}_{video_id}.wav
        This ensures chronological ordering, uniqueness, and traceability.
        
        Args:
            video (Dict): Video information
            from_channel_discovery (bool): Whether from channel discovery
            
        Returns:
            str: Unique filename for the audio file
        """
        # Get current timestamp for chronological ordering
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Get next sequential ID (thread-safe)
        sequential_id = self._get_next_download_index()
        
        # Extract and clean video info
        video_id = video.get('video_id', 'unknown')[:12]  # Limit length
        username = video.get('author_username', 'unknown')
        
        # Clean username for filename (keep alphanumeric, hyphens, underscores)
        safe_username = "".join(c for c in username if c.isalnum() or c in ('-', '_'))[:15]
        
        # Add channel discovery indicator
        discovery_suffix = "_CD" if from_channel_discovery else ""
        
        # Generate filename: timestamp_sequentialId_username_videoId[_CD].wav
        filename = f"{timestamp}_{sequential_id:04d}_{safe_username}_{video_id}{discovery_suffix}.wav"
        
        return filename
    
    def _save_crawler_state(self) -> None:
        """Save current crawler state for resumption."""
        try:
            state = {
                'timestamp': datetime.now().isoformat(),
                'current_keyword_index': getattr(self, 'current_keyword_index', 0),
                'current_video_index': getattr(self, 'current_video_index', 0),
                'total_videos_analyzed': self.total_videos_analyzed,
                'total_videos_collected': self.total_videos_collected,
                'collected_urls': list(self.collected_urls),
                'processed_channels': list(self.processed_channels),
                'promising_channels': list(self.promising_channels),
                'exhausted_keys': list(self.exhausted_keys),
                'quota_exhausted': self.quota_exhausted,
                'channel_discovery_stats': self.channel_discovery_stats,
                'resume_checkpoint': self.resume_checkpoint
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.output.print_error(f"Error saving crawler state: {e}")
    
    def _load_crawler_state(self) -> bool:
        """Load previous crawler state for resumption."""
        try:
            if not self.state_file.exists():
                return False
                
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            # Restore state
            self.current_keyword_index = state.get('current_keyword_index', 0)
            self.current_video_index = state.get('current_video_index', 0)
            self.total_videos_analyzed = state.get('total_videos_analyzed', 0)
            self.total_videos_collected = state.get('total_videos_collected', 0)
            self.collected_urls.update(state.get('collected_urls', []))
            self.processed_channels.update(state.get('processed_channels', []))
            self.promising_channels.update(state.get('promising_channels', []))
            self.exhausted_keys.update(state.get('exhausted_keys', []))
            self.quota_exhausted = state.get('quota_exhausted', False)
            self.channel_discovery_stats.update(state.get('channel_discovery_stats', {}))
            self.resume_checkpoint = state.get('resume_checkpoint')
            
            saved_time = datetime.fromisoformat(state['timestamp'])
            self.output.print_info(f"📥 Restored crawler state from {saved_time.strftime('%Y-%m-%d %H:%M:%S')}")
            self.output.print_info(f"📊 Resuming from keyword {self.current_keyword_index + 1}/{len(self.config.keyword_queries)}")
            
            return True
            
        except Exception as e:
            self.output.print_error(f"Error loading crawler state: {e}")
            return False
    
    def _test_api_key_availability(self) -> bool:
        """Test if any API keys are available for use."""
        try:
            # Get fresh API usage stats
            api_stats = self.api_client.get_api_usage_stats()
            
            # Test a simple API call
            test_result = self.api_client.search_videos_by_keyword("test", count=1)
            
            if test_result and len(test_result.get('data', {}).get('videos', [])) >= 0:
                self.quota_exhausted = False
                self.exhausted_keys.clear()
                self.output.print_success("✅ API keys are available again!")
                return True
            else:
                return False
                
        except Exception as e:
            self.output.debug_log(f"API key test failed: {e}")
            return False
    
    def _start_quota_monitor(self) -> None:
        """Start background thread to monitor API quota availability."""
        if not self.config.enable_forever_mode or not self.config.quota_monitoring:
            return
            
        def quota_monitor_worker():
            while self.is_running:
                if self.quota_exhausted:
                    # Test if keys are available again
                    time_since_last_test = (datetime.now() - self.last_key_test).total_seconds()
                    
                    if time_since_last_test >= self.config.key_test_interval:
                        self.output.print_info("🔍 Testing API key availability...")
                        
                        if self._test_api_key_availability():
                            self.output.print_success("🎉 API quota restored! Resuming collection...")
                            # Signal main thread to resume
                            self.quota_exhausted = False
                        else:
                            self.output.print_info(f"⏳ Keys still exhausted. Next test in {self.config.key_test_interval}s")
                        
                        self.last_key_test = datetime.now()
                
                time.sleep(30)  # Check every 30 seconds
        
        self.quota_monitor_thread = threading.Thread(target=quota_monitor_worker, daemon=True)
        self.quota_monitor_thread.start()
        self.output.print_info("🔄 Started quota monitoring thread")
    
    def _start_state_saver(self) -> None:
        """Start background thread to periodically save crawler state."""
        if not self.config.enable_forever_mode:
            return
            
        def state_saver_worker():
            while self.is_running:
                time.sleep(self.config.state_save_interval)
                if self.is_running:  # Check again after sleep
                    self._save_crawler_state()
        
        self.state_save_thread = threading.Thread(target=state_saver_worker, daemon=True)
        self.state_save_thread.start()
        self.output.debug_log("💾 Started state saver thread")
    
    def _handle_quota_exhaustion(self) -> None:
        """Handle when all API keys are exhausted."""
        self.quota_exhausted = True
        self._save_crawler_state()  # Save current progress
        
        self.output.print_header("🚫 ALL API KEYS EXHAUSTED", 60)
        self.output.print_warning("All API keys have reached their quota limits.")
        
        if self.config.enable_forever_mode:
            self.output.print_info("🔄 Forever mode enabled - will wait for quota restoration")
            self.output.print_info(f"⏰ Will test keys every {self.config.key_test_interval} seconds")
            self.output.print_info("💾 Current progress has been saved and will resume automatically")
            
            # Wait for quota restoration
            while self.quota_exhausted and self.is_running:
                time.sleep(60)  # Check every minute
                
        else:
            self.output.print_warning("Forever mode disabled - stopping crawler")
            self.output.print_info("💡 Enable forever_mode in config to auto-resume when quota restores")
    
    def _create_manifest_headers(self) -> None:
        """Create manifest CSV file with headers."""
        try:
            with open(self.manifest_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'url', 'video_id', 'title', 'author_username', 'duration_seconds',
                    'confidence', 'is_vietnamese', 'has_children_voice', 
                    'output_path', 'status', 'timestamp', 'from_channel_discovery'
                ])
        except Exception as e:
            self.output.print_error(f"Error creating manifest: {e}")
    
    def _update_manifest(self, video: Dict, audio_path: str, analysis_result: Any, from_channel_discovery: bool = False) -> None:
        """Update manifest CSV with new download entry."""
        try:
            with open(self.manifest_file, 'a', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    video.get('url', ''),
                    video.get('video_id', ''),
                    video.get('title', '').replace('"', "'"),  # Clean quotes
                    video.get('author_username', ''),
                    video.get('duration', 0),
                    getattr(analysis_result, 'confidence', 0.0),
                    getattr(analysis_result, 'is_vietnamese', False),
                    getattr(analysis_result, 'has_children_voice', False),
                    audio_path,
                    'success',
                    datetime.now().isoformat(),
                    from_channel_discovery
                ])
        except Exception as e:
            self.output.print_error(f"Error updating manifest: {e}")
    
    def _save_to_final_audio_and_manifest(self, audio_path: str, video: Dict, analysis_result: Any, from_channel_discovery: bool = False) -> str:
        """Save validated audio to final_audio_files directory and update manifest."""
        try:
            if not audio_path or not Path(audio_path).exists():
                self.output.print_error(f"Audio file not found: {audio_path}")
                return ""
            
            # Create final audio directory
            final_audio_dir = Path("./final_audio_files")
            final_audio_dir.mkdir(exist_ok=True)
            
            # Generate filename based on video info
            video_id = video.get('video_id', 'unknown')
            username = video.get('author_username', 'unknown')
            safe_username = "".join(c for c in username if c.isalnum() or c in ('-', '_'))[:20]
            
            final_filename = f"{safe_username}_{video_id}.wav"
            final_audio_path = final_audio_dir / final_filename
            
            # Copy audio file to final directory
            import shutil
            shutil.copy2(audio_path, final_audio_path)
            
            # Update manifest
            self._update_manifest(video, str(final_audio_path), analysis_result, from_channel_discovery)
            
            self.output.print_success(f"💾 Saved to final_audio_files: {final_filename}")
            return str(final_audio_path)
            
        except Exception as e:
            self.output.print_error(f"Error saving to final audio: {e}")
            return ""
    
    def _get_next_audio_filename(self) -> str:
        """Generate next sequential audio filename."""
        audio_dir = Path(Config.DEFAULT_FINAL_AUDIO_DIR)
        existing_files = list(audio_dir.glob("*.wav"))
        
        # Find the highest existing number
        max_num = 0
        for file in existing_files:
            try:
                # Extract number from filename like "0001_video_title.wav"
                num_str = file.stem.split('_')[0]
                if num_str.isdigit():
                    max_num = max(max_num, int(num_str))
            except (IndexError, ValueError):
                continue
        
        # Return next number
        return f"{max_num + 1:04d}"
    
    def _save_final_audio(self, temp_audio_path: str, video: Dict, analysis_result: Any, from_channel_discovery: bool = False) -> Optional[str]:
        """Save validated audio to final_audio_files directory with consistent naming."""
        try:
            if not temp_audio_path or not Path(temp_audio_path).exists():
                self.output.print_error(f"Audio file not found: {temp_audio_path}")
                return None
            
            # Create final audio directory
            final_audio_dir = Path(Config.DEFAULT_FINAL_AUDIO_DIR)
            final_audio_dir.mkdir(exist_ok=True)
            
            # Generate unique, consistent filename
            filename = self._generate_unique_audio_filename(video, from_channel_discovery)
            final_audio_path = final_audio_dir / filename
            
            # Copy audio file to final directory
            import shutil
            shutil.copy2(temp_audio_path, final_audio_path)
            
            self.output.print_success(f"💾 Saved final audio: {filename}")
            return str(final_audio_path)
            
        except Exception as e:
            self.output.print_error(f"Error saving final audio: {e}")
            return None
    
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
    
    def process_channel_exhaustively(self, username: str, source_video: Dict) -> int:
        """
        Exhaustively process all videos from a promising channel.
        
        Args:
            username (str): TikTok username (without @)
            source_video (Dict): The original video that led to this channel discovery
            
        Returns:
            int: Number of additional qualifying videos found
        """
        if not self.config.enable_channel_discovery:
            return 0
        
        # Check if we've already processed this channel
        if username in self.processed_channels:
            self.output.debug_log(f"Channel @{username} already processed, skipping")
            return 0
        
        # Mark channel as processed
        self.processed_channels.add(username)
        self.channel_discovery_stats['channels_processed'] += 1
        
        self.output.print_header(f"🎯 CHANNEL DISCOVERY: @{username}", 70)
        self.output.print_info(f"📺 Exhaustively analyzing channel @{username}")
        self.output.print_info(f"💡 Triggered by video: {source_video['title'][:50]}...")
        
        try:
            # Collect all videos from this channel
            max_videos = self.config.max_channel_videos if not self.config.exhaustive_channel_analysis else 0
            
            # Get user videos in batches for exhaustive analysis
            all_channel_videos = []
            cursor = 0
            page_size = 50
            max_pages = 20  # Safety limit
            
            for page in range(max_pages):
                videos_batch = self.api_client.get_user_videos(username, count=page_size, cursor=cursor)
                
                if not videos_batch:
                    self.output.debug_log(f"No more videos found at cursor {cursor}")
                    break
                
                all_channel_videos.extend(videos_batch)
                self.output.debug_log(f"Page {page + 1}: +{len(videos_batch)} videos (total: {len(all_channel_videos)})")
                
                # If we got less than page_size, we've reached the end
                if len(videos_batch) < page_size:
                    break
                
                # Update cursor (TikTok uses time-based pagination)
                if videos_batch:
                    last_video = videos_batch[-1]
                    cursor = last_video.get('create_time', cursor + page_size)
                
                # Respect max_videos limit if exhaustive is disabled
                if max_videos > 0 and len(all_channel_videos) >= max_videos:
                    all_channel_videos = all_channel_videos[:max_videos]
                    break
            
            if not all_channel_videos:
                self.output.print_warning(f"No videos found in channel @{username}")
                return 0
            
            self.output.print_info(f"📊 Found {len(all_channel_videos)} total videos in @{username}")
            
            # Filter out videos we've already processed
            new_videos = [v for v in all_channel_videos if v['url'] not in self.collected_urls]
            self.output.print_info(f"🆕 {len(new_videos)} new videos to analyze (skipped {len(all_channel_videos) - len(new_videos)} duplicates)")
            
            # Process each video
            channel_qualifications = 0
            channel_processed = 0
            
            for i, video in enumerate(new_videos, 1):
                self.output.print_progress(f"📹 [{i}/{len(new_videos)}] Analyzing: {video['title'][:40]}...")
                
                # Process video through the normal pipeline
                if self.process_video(video, is_from_channel_discovery=True):
                    channel_qualifications += 1
                    self.channel_discovery_stats['videos_from_channel_discovery'] += 1
                
                channel_processed += 1
                
                # Progress update every 10 videos
                if i % 10 == 0:
                    self.output.print_info(f"📊 Channel progress: {channel_qualifications} qualified from {channel_processed} analyzed")
            
            # Channel analysis complete
            qualification_rate = (channel_qualifications / max(channel_processed, 1)) * 100
            
            self.output.print_success(f"✅ Channel @{username} analysis complete!")
            self.output.print_info(f"📊 Results: {channel_qualifications} qualified videos from {channel_processed} analyzed")
            self.output.print_info(f"📊 Channel qualification rate: {qualification_rate:.1f}%")
            
            # Mark as promising channel if it meets threshold
            if qualification_rate >= (self.config.channel_quality_threshold * 100):
                self.promising_channels.add(username)
                self.output.print_success(f"⭐ @{username} marked as promising channel ({qualification_rate:.1f}% qualification rate)")
            
            return channel_qualifications
            
        except Exception as e:
            self.output.print_error(f"Failed to process channel @{username}: {e}")
            return 0
    


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
            download_result = self.video_downloader.download_and_convert_audio(video, download_index)
            
            # Handle graceful skip for failed downloads
            if download_result is None or download_result == (None, None):
                return AudioAnalysisResult(
                    is_vietnamese=False,
                    detected_language=None,
                    has_children_voice=False,
                    confidence=0.0,
                    total_analysis_time=0.0,
                    children_detection_time=0.0,
                    video_length_seconds=0.0,
                    error="Failed to download/convert video"
                )
            
            audio_path, duration = download_result
            
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
            
            # Store temp audio path in result for later use
            analysis_result.temp_audio_path = audio_path
            
            # Clean up temporary audio file only if analysis failed
            if analysis_result.error:
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
    
    def process_video(self, video: Dict, is_from_channel_discovery: bool = False) -> bool:
        """
        Process a single video through the analysis pipeline.
        
        Args:
            video (Dict): Video information
            is_from_channel_discovery (bool): Whether this video came from channel discovery
            
        Returns:
            bool: True if video was collected, False otherwise
        """
        self.total_videos_analyzed += 1
        
        # Skip duplicates - check if URL is already in collected URLs (from multi_query_collected_video_urls.txt)
        if video['url'] in self.collected_urls:
            self.output.debug_log("Skipping duplicate video (already in collected URLs)")
            return False
        
        # Check if already downloaded (manifest check)
        if video['url'] in self.downloaded_urls:
            self.output.debug_log("Skipping already downloaded video (in manifest)")
            return False
        
        # Analyze audio
        analysis_result = self.analyze_video_audio(video)
        
        # Update statistics
        self.total_processing_time += analysis_result.total_analysis_time
        
        # Check if analysis failed
        if analysis_result.error:
            self.output.print_warning(f"Analysis failed: {analysis_result.error}")
            
            # Track consecutive download failures
            if "Failed to download" in analysis_result.error:
                self.consecutive_download_failures += 1
                self.total_download_failures += 1
                
                # Provide guidance if too many consecutive failures
                if self.consecutive_download_failures >= self.max_consecutive_failures:
                    self.output.print_error(f"⚠️ Too many consecutive download failures ({self.consecutive_download_failures})")
                    self.output.print_error("🔧 Suggestions:")
                    self.output.print_error("   - Check your internet connection")
                    self.output.print_error("   - TikTok may have updated their anti-bot measures")
                    self.output.print_error("   - Try using a VPN or different IP address")
                    self.output.print_error("   - Consider running during different hours")
                    self.output.print_error("   - Update yt-dlp: pip install --upgrade yt-dlp")
                    self.output.print_error("💡 The crawler will continue with the next videos...")
            else:
                # Reset consecutive failures if it's not a download issue
                self.consecutive_download_failures = 0
            
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
            return False
        
        # Check for quota exhaustion during processing
        if self.config.enable_forever_mode and self.api_client.is_quota_exhausted():
            self.output.print_warning("🚫 API quota exhaustion detected during video processing")
            self.quota_exhausted = True
            # Save current state before handling exhaustion
            self._save_crawler_state()
            raise Exception("API quota exhausted - triggering forever mode wait")
        
        # Video meets criteria - collect it
        self.total_children_voice_videos += 1
        
        # Reset consecutive failures on successful processing
        self.consecutive_download_failures = 0
        
        # Save URL immediately to prevent duplicates in channel discovery
        self._save_url_to_file(video['url'])
        self.collected_urls.add(video['url'])
        
        # Save audio to final directory
        temp_audio_path = getattr(analysis_result, 'temp_audio_path', None)
        final_audio_path = None
        
        if temp_audio_path and Path(temp_audio_path).exists():
            final_audio_path = self._save_final_audio(temp_audio_path, video, analysis_result, is_from_channel_discovery)
            if final_audio_path:
                # Update manifest
                self._update_manifest(video, final_audio_path, analysis_result, is_from_channel_discovery)
                # Update downloaded URLs set
                self.downloaded_urls.add(video['url'])
        
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
            'collected_at': datetime.now().isoformat(),
            'from_channel_discovery': is_from_channel_discovery,
            'final_audio_path': final_audio_path
        }
        
        self.collected_videos.append(video_record)
        self.total_videos_collected += 1
        
        # Channel discovery integration - only trigger for videos NOT from channel discovery
        if not is_from_channel_discovery and self.config.enable_channel_discovery:
            username = video.get('author_username')
            if username and username not in self.processed_channels:
                self.output.print_info(f"🎯 Triggering channel discovery for @{username}")
                self.channel_discovery_stats['channels_discovered'] += 1
                
                # Process the channel exhaustively in the background or immediately
                additional_videos = self.process_channel_exhaustively(username, video)
                if additional_videos > 0:
                    self.output.print_success(f"🎉 Channel discovery found {additional_videos} additional qualifying videos!")
        
        discovery_note = " [FROM CHANNEL DISCOVERY]" if is_from_channel_discovery else ""
        self.output.print_success(f"✅ Video collected successfully{discovery_note}: {video['title'][:50]}...")
        
        return True
    
    def process_remaining_urls_from_file(self, urls_file: str) -> int:
        """
        Process remaining URLs from the collected URLs file that haven't been downloaded yet.
        
        Args:
            urls_file (str): Path to file containing collected URLs
            
        Returns:
            int: Number of videos processed
        """
        if not Path(urls_file).exists():
            self.output.print_warning(f"URLs file not found: {urls_file}")
            return 0
        
        # Read URLs from file
        try:
            with open(urls_file, 'r', encoding='utf-8') as f:
                all_urls = [line.strip() for line in f if line.strip()]
        except Exception as e:
            self.output.print_error(f"Error reading URLs file: {e}")
            return 0
        
        # Filter out already downloaded URLs
        remaining_urls = [url for url in all_urls if url not in self.downloaded_urls]
        
        if not remaining_urls:
            self.output.print_info("✅ All URLs have already been processed")
            return 0
        
        self.output.print_header(f"Processing {len(remaining_urls)} Remaining URLs")
        self.output.print_info(f"📊 Total URLs: {len(all_urls)}")
        self.output.print_info(f"📊 Already processed: {len(all_urls) - len(remaining_urls)}")
        self.output.print_info(f"📊 Remaining to process: {len(remaining_urls)}")
        
        processed_count = 0
        
        for i, url in enumerate(remaining_urls, 1):
            self.output.print_progress(f"[{i}/{len(remaining_urls)}] Processing URL: {url[:60]}...")
            
            try:
                # Extract video info from URL (basic info for processing)
                video_info = {
                    'url': url,
                    'video_id': self._extract_video_id_from_url(url),
                    'title': 'Unknown',
                    'author_username': 'unknown'
                }
                
                # Process the video
                if self.process_video(video_info, is_from_channel_discovery=False):
                    processed_count += 1
                    self.output.print_success(f"✅ Processed: {url[:60]}...")
                else:
                    self.output.debug_log(f"❌ Skipped: {url[:60]}...")
                
            except Exception as e:
                self.output.print_error(f"Error processing {url}: {e}")
                continue
        
        self.output.print_success(f"🎉 Completed processing {processed_count} videos from remaining URLs")
        return processed_count
    
    def _extract_video_id_from_url(self, url: str) -> str:
        """Extract video ID from TikTok URL."""
        try:
            import re
            # Common TikTok URL patterns
            patterns = [
                r'tiktok\.com/@[^/]+/video/(\d+)',
                r'tiktok\.com/.*?/video/(\d+)',
                r'vm\.tiktok\.com/(\w+)',
                r'vt\.tiktok\.com/(\w+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            # Fallback: use URL hash
            return str(hash(url))[-8:]
            
        except Exception:
            return 'unknown'
    
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
        Run the complete video collection process with forever mode support.
        
        Returns:
            List[Dict]: Collected videos with analysis results
        """
        self.output.print_header("Starting TikTok Children's Voice Collection")
        start_time = time.time()
        self.is_running = True
        
        try:
            # Load previous state if forever mode is enabled
            if self.config.enable_forever_mode:
                self.output.print_info("🔄 Forever mode enabled - checking for previous state...")
                if self._load_crawler_state():
                    self.output.print_success("📥 Previous state loaded - resuming from checkpoint")
                else:
                    self.output.print_info("🆕 No previous state found - starting fresh")
                
                # Start background monitoring threads
                self._start_quota_monitor()
                self._start_state_saver()
            
            # Main collection loop with resumption support
            while self.is_running:
                try:
                    # Process keyword queries starting from checkpoint
                    start_index = getattr(self, 'current_keyword_index', 0)
                    
                    for i in range(start_index, len(self.config.keyword_queries)):
                        if not self.is_running:
                            break
                            
                        self.current_keyword_index = i
                        keyword = self.config.keyword_queries[i]
                        
                        self.output.print_header(f"Processing Keyword {i+1}/{len(self.config.keyword_queries)}: '{keyword}'")
                        
                        # Check for quota exhaustion before processing
                        if self.quota_exhausted:
                            self.output.print_warning("⏸️ Quota exhausted - waiting for restoration...")
                            self._handle_quota_exhaustion()
                            continue
                        
                        # Collect videos from keyword with resumption support
                        try:
                            keyword_videos = self.collect_videos_from_keyword(keyword, self.config.target_videos_per_query)
                            
                            # Process each video with checkpoint tracking
                            video_start_index = getattr(self, 'current_video_index', 0) if i == start_index else 0
                            
                            for j, video in enumerate(keyword_videos[video_start_index:], video_start_index):
                                if not self.is_running or self.quota_exhausted:
                                    break
                                    
                                self.current_video_index = j
                                self.resume_checkpoint = {
                                    'keyword_index': i,
                                    'video_index': j,
                                    'keyword': keyword,
                                    'video_url': video.get('url', 'unknown')
                                }
                                
                                try:
                                    self.process_video(video)
                                except Exception as e:
                                    # Handle quota exhaustion during video processing
                                    if "quota" in str(e).lower() or "rate" in str(e).lower():
                                        self.output.print_warning("🚫 Quota exhaustion detected during processing")
                                        self._handle_quota_exhaustion()
                                        break
                                    else:
                                        self.output.print_error(f"Error processing video: {e}")
                                        continue
                                
                                # Check if we've reached our target
                                if self.total_videos_collected >= self.config.target_videos_per_query:
                                    self.output.print_info(f"Reached target for '{keyword}'")
                                    break
                            
                            # Reset video index for next keyword
                            self.current_video_index = 0
                            
                        except Exception as e:
                            if "quota" in str(e).lower() or "rate" in str(e).lower():
                                self.output.print_warning(f"🚫 Quota exhaustion on keyword '{keyword}'")
                                self._handle_quota_exhaustion()
                                continue
                            else:
                                self.output.print_error(f"Error processing keyword '{keyword}': {e}")
                                continue
                        
                        # Progress report
                        self.output.print_info(f"Progress: {self.total_videos_collected} collected, {self.total_videos_analyzed} analyzed")
                    
                    # If we completed all keywords, check if forever mode should continue
                    if self.config.enable_forever_mode and self.current_keyword_index >= len(self.config.keyword_queries) - 1:
                        self.output.print_info("🔄 Completed all keywords - restarting from beginning in forever mode")
                        self.current_keyword_index = 0
                        self.current_video_index = 0
                        time.sleep(60)  # Brief pause before restarting
                    else:
                        break  # Exit main loop if not in forever mode
                        
                except KeyboardInterrupt:
                    self.output.print_warning("⏸️ Collection paused by user")
                    self._save_crawler_state()
                    if self.config.enable_forever_mode:
                        self.output.print_info("💾 State saved - you can resume later")
                    break
                    
            # Final processing
            total_time = time.time() - start_time
            
            # Channel discovery summary
            if self.config.enable_channel_discovery:
                self.output.print_header("Channel Discovery Summary")
                self.output.print_info(f"📊 Channels discovered: {self.channel_discovery_stats['channels_discovered']}")
                self.output.print_info(f"📊 Channels processed: {self.channel_discovery_stats['channels_processed']}")
                self.output.print_info(f"📊 Additional videos from channel discovery: {self.channel_discovery_stats['videos_from_channel_discovery']}")
                self.output.print_info(f"⭐ Promising channels identified: {len(self.promising_channels)}")
            
            self._generate_final_report(total_time)
            self._save_results()
            
            return self.collected_videos
            
        except KeyboardInterrupt:
            self.output.print_warning("Collection interrupted by user")
            self._save_crawler_state()
            self._generate_final_report(time.time() - start_time)
            self._save_results()
            return self.collected_videos
        except Exception as e:
            self.output.print_error(f"Collection failed: {e}")
            self._save_crawler_state()
            raise
        finally:
            self.is_running = False
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
        print(f"   Total Download Failures: {self.total_download_failures}")
        
        # Add recommendations if success rate is low
        if 'recommendations' in download_stats and download_stats['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in download_stats['recommendations']:
                print(f"   - {rec}")
        
        # Audio analysis statistics
        print(f"\n🎵 Audio Analysis:")
        classifier_stats = self.audio_classifier.get_statistics()
        print(f"   Audio Analyses: {classifier_stats['total_analyses']}")
        print(f"   Analysis Success Rate: {classifier_stats['success_rate']:.1f}%")
        print(f"   Processing Device: {classifier_stats['device']}")
        
        # Channel discovery statistics
        if self.config.enable_channel_discovery:
            print(f"\n🎯 Channel Discovery Statistics:")
            print(f"   Channels Discovered: {self.channel_discovery_stats['channels_discovered']}")
            print(f"   Channels Processed: {self.channel_discovery_stats['channels_processed']}")
            print(f"   Videos from Channel Discovery: {self.channel_discovery_stats['videos_from_channel_discovery']}")
            print(f"   Promising Channels Found: {len(self.promising_channels)}")
            if self.promising_channels:
                print(f"   Promising Channels: {', '.join(['@' + ch for ch in list(self.promising_channels)[:5]])}{'...' if len(self.promising_channels) > 5 else ''}")
        
        # Final audio files statistics
        print(f"\n💾 Final Audio Files:")
        print(f"   Audio Directory: {Config.DEFAULT_FINAL_AUDIO_DIR}")
        print(f"   Manifest File: {self.manifest_file}")
        print(f"   Total Downloaded: {len(self.downloaded_urls)}")
        if Path(Config.DEFAULT_FINAL_AUDIO_DIR).exists():
            audio_files = list(Path(Config.DEFAULT_FINAL_AUDIO_DIR).glob("*.wav"))
            total_size = sum(f.stat().st_size for f in audio_files) / (1024*1024)  # MB
            print(f"   Audio Files: {len(audio_files)} files ({total_size:.1f} MB)")
    
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
                        'collection_time': datetime.now().isoformat(),
                        'channel_discovery_stats': self.channel_discovery_stats,
                        'promising_channels': list(self.promising_channels)
                    },
                    'configuration': {
                        'target_per_query': self.config.target_videos_per_query,
                        'keyword_queries': self.config.keyword_queries,
                        'enable_language_detection': self.config.enable_language_detection,
                        'enable_channel_discovery': self.config.enable_channel_discovery,
                        'exhaustive_channel_analysis': self.config.exhaustive_channel_analysis,
                        'max_channel_videos': self.config.max_channel_videos,
                        'channel_quality_threshold': self.config.channel_quality_threshold
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
                
                # Channel discovery statistics
                if self.config.enable_channel_discovery:
                    f.write("Channel Discovery Results:\n")
                    f.write(f"  Channels Discovered: {self.channel_discovery_stats['channels_discovered']}\n")
                    f.write(f"  Channels Processed: {self.channel_discovery_stats['channels_processed']}\n")
                    f.write(f"  Videos from Channel Discovery: {self.channel_discovery_stats['videos_from_channel_discovery']}\n")
                    f.write(f"  Promising Channels: {len(self.promising_channels)}\n")
                    if self.promising_channels:
                        f.write(f"  Promising Channel List: {', '.join(['@' + ch for ch in self.promising_channels])}\n")
                    f.write("\n")
                
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