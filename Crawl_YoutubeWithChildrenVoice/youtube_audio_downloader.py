#!/usr/bin/env python3
"""
YouTube Audio Downloader and Converter with Video Length Tracking

This module provides functionality for downloading audio from YouTube videos and converting
them to WAV format for further audio analysis. It uses yt-dlp for video downloading and
FFmpeg for audio format conversion, with enhanced capabilities for video duration tracking.

Key Features:
- Anti-detection mechanisms with user agent rotation
- Rate limiting to prevent bot detection
- Multiple download methods (yt-dlp, pytube fallback, ffmpeg)
- YouTube Data API integration for metadata
- Cookie support for authenticated downloads
- Language-based file organization
- Comprehensive error handling and retry logic

Author: Le Hoang Minh
"""

from __future__ import unicode_literals

# Core libraries
import json
import os
import random
import shutil
import subprocess
import sys
import time
from urllib.parse import urlparse, parse_qs

# External dependencies
import ffmpeg
import googleapiclient.discovery
import yt_dlp

# Local imports
from youtube_audio_downloader_alternative import YouTubeAudioDownloaderAlternative


# =================================================================
# CONSTANTS AND CONFIGURATION
# =================================================================

# Default user agents and timeouts
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0'
DEFAULT_CHROME_VERSION = '139'

# Rate limiting and timing settings
DEFAULT_SLEEP_INTERVAL = 8
DEFAULT_MAX_SLEEP_INTERVAL = 15
DEFAULT_RETRIES = 3
DEFAULT_FRAGMENT_RETRIES = 3
DEFAULT_EXTRACTOR_RETRIES = 3

# Timeout settings (in seconds)
FFMPEG_TIMEOUT_SECONDS = 180
YT_DLP_TIMEOUT_SECONDS = 30
CONVERSION_TIMEOUT_SECONDS = 180
DEFAULT_MAX_AUDIO_DURATION = 300  # 5 minutes

# YouTube URL patterns
YOUTUBE_DOMAIN = 'youtube.com'
YOUTUBE_SHORT_DOMAIN = 'youtu.be'

# System paths and configurations
FFMPEG_COMMON_PATHS = [
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
]

# Browser support
SUPPORTED_BROWSERS = ['chrome', 'firefox', 'safari', 'edge', 'opera', 'brave']

# Error detection patterns
UNAVAILABLE_VIDEO_PATTERNS = [
    'video unavailable', 'removed by the uploader', 'private video', 'copyright'
]

BOT_DETECTION_PATTERNS = [
    'sign in', 'bot', 'automated', 'captcha', 'blocked'
]


# =================================================================
# CONFIGURATION CLASS
# =================================================================

class Config:
    """Configuration class to store paths and settings."""
    
    def __init__(self, user_agent=None, language_mapping=None):
        # Determine the parent directory of the script
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        # Store audio in youtube_audio_outputs relative to the parent directory
        self.output_dir = os.path.join(self.base_dir, 'youtube_audio_outputs')
        
        # Store language mapping for organizing files
        self.language_mapping = language_mapping or {}
        
        # Use provided user agent or load from crawler config
        if user_agent:
            default_user_agent = user_agent
        else:
            user_agent_settings = self._load_user_agent_settings()
            default_user_agent = user_agent_settings.get('default_user_agent', DEFAULT_USER_AGENT)
        
        # Enhanced Audio format settings with anti-detection
        self.ydl_opts = {
            'format': 'bestaudio/best',
            # Add user agent rotation
            'user_agent': default_user_agent,
            # Add headers to mimic browser behavior
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br, zstd',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            },
            # Rate limiting - much longer intervals to prevent detection
            'sleep_interval': DEFAULT_SLEEP_INTERVAL,  # Sleep 8 seconds between downloads (increased from 2)
            'max_sleep_interval': DEFAULT_MAX_SLEEP_INTERVAL,  # Increased from 5
            # Retry settings
            'retries': DEFAULT_RETRIES,
            'fragment_retries': DEFAULT_FRAGMENT_RETRIES,
            # Bypass geo-blocking
            'geo_bypass': True,
            # Extractor settings
            'extractor_retries': DEFAULT_EXTRACTOR_RETRIES,
        }
        
        # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _load_user_agent_settings(self):
        """Load user agent settings from crawler_config.json"""
        try:
            config_file = os.path.join(self.base_dir, 'crawler_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    return config_data.get('user_agent_settings', {})
            else:
                print(f"⚠️ crawler_config.json not found, using default user agents")
                return {}
        except Exception as e:
            print(f"⚠️ Error loading user agent settings from crawler_config.json: {e}")
            return {}
    
    def _get_chrome_version(self):
        """Extract Chrome version from user agent settings"""
        user_agent_settings = self._load_user_agent_settings()
        return user_agent_settings.get('chrome_version', DEFAULT_CHROME_VERSION)
    
    def get_output_path(self, filename):
        """Get the full path for an output file."""
        return os.path.join(self.output_dir, filename)
    
    def get_language_output_dir(self, url):
        """Get the output directory based on URL language classification."""
        # Get language classification for this URL
        language_folder = self.language_mapping.get(url, 'unknown')
        
        # Create the language-specific subfolder
        language_output_dir = os.path.join(self.output_dir, language_folder)
        os.makedirs(language_output_dir, exist_ok=True)
        
        return language_output_dir
    
    def get_language_output_path(self, filename, url):
        """Get the full path for an output file in the appropriate language subfolder."""
        language_dir = self.get_language_output_dir(url)
        return os.path.join(language_dir, filename)
    
    def get_m4a_filename(self, index):
        """Get the m4a filename for a given index."""
        # Allow run-as-script to inject a custom base name
        custom_base = getattr(self, '_current_basename', None)
        if custom_base:
            return f'{custom_base}.m4a'
        return f'output_{index}.m4a'
    
    def get_wav_filename(self, index):
        """Get the wav filename for a given index."""
        custom_base = getattr(self, '_current_basename', None)
        if custom_base:
            return f'{custom_base}.wav'
        return f'output_{index}.wav'


# =================================================================
# MAIN YOUTUBE AUDIO DOWNLOADER CLASS
# =================================================================

class YoutubeAudioDownloader:
    """
    Class to handle YouTube audio downloading and conversion.
    
    This class provides comprehensive functionality for downloading audio from YouTube
    videos with anti-detection mechanisms, rate limiting, and multiple fallback methods.
    
    Features:
    - Anti-bot detection with user agent rotation
    - Intelligent rate limiting and delays
    - Multiple download methods (yt-dlp, pytube, ffmpeg)
    - YouTube Data API integration
    - Cookie-based authentication
    - Audio format conversion (M4A to WAV)
    - Language-based file organization
    - Comprehensive error handling
    
    Args:
        config (Config): Configuration object with paths and settings
        cookies_file (str, optional): Path to Netscape format cookies file
        cookies_from_browser (str, optional): Browser name for cookie extraction
        language_mapping (dict, optional): URL to language folder mapping
    """
    
    def __init__(self, config, cookies_file=None, cookies_from_browser=None, language_mapping=None):
        self.config = config
        self.last_request_time = 0
        self.request_count = 0
        self.youtube_api_key = None
        self.youtube_service = None
        # Runtime flags
        self.disable_rate_limit = False
        
        # Store language mapping for organizing downloads
        self.language_mapping = language_mapping or {}
        
        # Cookie settings
        self.cookies_file = cookies_file
        self.cookies_from_browser = cookies_from_browser
        
        # Try to initialize YouTube Data API
        self._init_youtube_api()
        
        # Check cookie availability
        self._ensure_cookies_available()
        
        # Initialize alternative downloader used by the crawler
        try:
            # Use the same output directory as the script's config
            self.alt_downloader = YouTubeAudioDownloaderAlternative(
                output_dir=self.config.output_dir,
                cookies_file=self.cookies_file,
                cookies_from_browser=self.cookies_from_browser
            )
            print("✅ Initialized YouTubeAudioDownloaderAlternative (crawler method)")
        except Exception as e:
            print(f"⚠️ Could not initialize alternative downloader: {e}")
            self.alt_downloader = None
    
    # =================================================================
    # INITIALIZATION AND CONFIGURATION METHODS
    # =================================================================
    
    def _init_youtube_api(self):
        """Initialize YouTube Data API if available."""
        try:
            # Try to get API key from environment config
            try:
                from env_config import config as env_config
                self.youtube_api_key = env_config.YOUTUBE_API_KEY
            except (ImportError, AttributeError):
                self.youtube_api_key = os.getenv('YOUTUBE_API_KEY')
            
            if self.youtube_api_key:
                self.youtube_service = googleapiclient.discovery.build(
                    "youtube", "v3", developerKey=self.youtube_api_key
                )
                print("✅ YouTube Data API initialized for metadata retrieval")
            else:
                print("⚠️ YouTube Data API key not found, using yt-dlp for metadata")
        except Exception as e:
            print(f"⚠️ Could not initialize YouTube Data API: {e}")
            self.youtube_service = None
    
    # =================================================================
    # RATE LIMITING AND DELAY METHODS
    # =================================================================
    
    def _reset_request_counter(self):
        """Reset request counter to get fresh delays when issues are detected"""
        print("🔄 Resetting request counter for fresh delays")
        self.request_count = 0
        self.last_request_time = time.time()
    
    def _should_add_extra_delay(self):
        """Check if we should add extra delays based on recent activity"""
        if self.request_count > 15:
            return True
        elif self.request_count > 10:
            return random.random() < 0.7  # 70% chance
        elif self.request_count > 5:
            return random.random() < 0.5  # 50% chance
        return False
    
    def _add_random_delay(self, min_delay=2, max_delay=8):
        """Add a random delay to simulate human behavior and prevent detection"""
        delay = random.uniform(min_delay, max_delay)
        print(f"⏳ Adding random delay: {delay:.1f}s")
        time.sleep(delay)
    
    def _rate_limit_delay(self):
        """Implement intelligent rate limiting with extended delays to prevent detection"""
        if getattr(self, 'disable_rate_limit', False):
            return
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        # Significantly increase delays to prevent detection completely
        if self.request_count > 20:
            min_delay = 15 + random.uniform(5, 10)  # 20-25 seconds
        elif self.request_count > 15:
            min_delay = 12 + random.uniform(3, 8)   # 15-20 seconds
        elif self.request_count > 10:
            min_delay = 10 + random.uniform(2, 5)   # 12-15 seconds
        elif self.request_count > 5:
            min_delay = 8 + random.uniform(1, 3)    # 9-11 seconds
        else:
            min_delay = 5 + random.uniform(1, 2)    # 6-7 seconds
        
        if time_since_last < min_delay:
            sleep_time = min_delay - time_since_last
            print(f"⏳ Rate limiting: sleeping for {sleep_time:.1f} seconds...")
            time.sleep(sleep_time)
        
        # Add additional random delay for extra protection
        self._add_random_delay(1, 3)
        
        # Add extra delay if we've been very active
        if self._should_add_extra_delay():
            extra_delay = random.uniform(5, 10)
            print(f"⏳ Adding extra delay due to high activity: {extra_delay:.1f}s")
            time.sleep(extra_delay)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    # =================================================================
    # ANTI-DETECTION AND USER AGENT METHODS
    # =================================================================
    
    def _add_anti_detection_headers(self, ydl_opts):
        """Add additional anti-detection headers to prevent bot detection"""
        if 'http_headers' not in ydl_opts:
            ydl_opts['http_headers'] = {}
        
        # Get Chrome version from config
        chrome_version = self.config._get_chrome_version()
        
        # Add more browser-like headers
        ydl_opts['http_headers'].update({
            'Sec-Ch-Ua': f'"Google Chrome";v="{chrome_version}", "Chromium";v="{chrome_version}", "Not_A Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-GPC': '1',
            'Cache-Control': 'max-age=0',
            'TE': 'trailers',
            'Priority': 'u=0, i',
        })
        
        return ydl_opts
    
    def _generate_user_agent_variations(self, base_user_agent):
        """Generate user agent variations based on the config settings"""
        # Load user agents from config first
        user_agent_settings = self.config._load_user_agent_settings()
        rotation_user_agents = user_agent_settings.get('rotation_user_agents')
        
        if rotation_user_agents:
            # Use user agents from config
            return rotation_user_agents
        
        # Fallback: Extract Chrome version from base user agent and generate variations
        import re
        chrome_match = re.search(r'Chrome/(\d+\.\d+\.\d+\.\d+)', base_user_agent)
        if chrome_match:
            chrome_version = chrome_match.group(1)
        else:
            chrome_version = "139.0.0.0"  # fallback
        
        # Generate variations for different platforms using the same Chrome version
        variations = [
            f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36',
            f'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36',
            f'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36',
            # Add a couple Firefox variations as well for diversity
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0'
        ]
        
        return variations
    
    def _get_dynamic_ydl_opts(self):
        """Get yt-dlp options with dynamic user agent rotation and cookie support"""
        # Get base user agent from config and create variations
        base_user_agent = self.config.ydl_opts['user_agent']
        
        # Create user agent variations based on the base one
        user_agents = self._generate_user_agent_variations(base_user_agent)
        
        opts = self.config.ydl_opts.copy()
        opts['user_agent'] = random.choice(user_agents)
        
        # Add additional anti-detection measures
        if not getattr(self, 'disable_rate_limit', False):
            opts['sleep_interval'] = random.uniform(8, 15)  # Random sleep between 8-15 seconds
            opts['max_sleep_interval'] = 20  # Maximum sleep interval
        # Force Android client to bypass bot detection
        opts['extractor_args'] = {
            'youtube': {
                'player_client': ['android']
            }
        }
        # Avoid playlist processing unless explicitly desired
        opts['noplaylist'] = True
        
        # Add anti-detection headers
        opts = self._add_anti_detection_headers(opts)
        
        # Do NOT use cookies by default when Android client is enabled
        
        return opts
    
    # =================================================================
    # COOKIE AND VALIDATION METHODS
    # =================================================================
    
    def _ensure_cookies_available(self):
        """Ensure cookies are available and log status for debugging"""
        cookie_status = self.get_cookie_status()
        if not cookie_status['cookies_file_exists'] and not cookie_status['cookies_from_browser']:
            print("⚠️ Warning: No cookies configured - this may trigger bot detection")
            print("💡 Consider setting cookies using --cookies-file or --cookies-browser")
        else:
            print(f"✅ Cookies configured: {cookie_status}")
        return cookie_status
    
    def _validate_cookies(self):
        """Validate that cookies are properly configured and accessible"""
        if self.cookies_file and os.path.exists(self.cookies_file):
            try:
                file_size = os.path.getsize(self.cookies_file)
                if file_size < 100:  # Cookies file should be at least 100 bytes
                    print(f"⚠️ Warning: Cookies file seems too small ({file_size} bytes)")
                    return False
                print(f"🍪 Cookie file size: {file_size} characters")
                return True
            except OSError:
                print("⚠️ Warning: Could not read cookies file")
                return False
        elif self.cookies_from_browser:
            print(f"🍪 Using cookies from browser: {self.cookies_from_browser}")
            return True
        else:
            print("⚠️ Warning: No cookies configured")
            return False
    
    def _apply_cookies_to_opts(self, ydl_opts):
        """Bypass cookie usage when using Android client; return options unchanged."""
        return ydl_opts
    
    # =================================================================
    # UTILITY AND HELPER METHODS
    # =================================================================
    
    def _is_video_unavailable(self, error_message):
        """Check if error message indicates video is unavailable."""
        error_msg_lower = error_message.lower()
        return any(pattern in error_msg_lower for pattern in UNAVAILABLE_VIDEO_PATTERNS)
    
    def _is_bot_detection_error(self, error_message):
        """Check if error message indicates bot detection."""
        error_msg_lower = error_message.lower()
        return any(pattern in error_msg_lower for pattern in BOT_DETECTION_PATTERNS)
    
    def _cleanup_files(self, file_paths):
        """Clean up multiple files, ignoring errors."""
        cleanup_count = 0
        for file_path in file_paths:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    cleanup_count += 1
                except OSError:
                    pass  # File might be in use by another process
        return cleanup_count
    
    # =================================================================
    # YOUTUBE API AND METADATA METHODS
    # =================================================================
    
    def _extract_video_id(self, url):
        """Extract video ID from YouTube URL."""
        parsed_url = urlparse(url)
        if YOUTUBE_DOMAIN in parsed_url.netloc:
            query_params = parse_qs(parsed_url.query)
            return query_params.get('v', [None])[0]
        elif YOUTUBE_SHORT_DOMAIN in parsed_url.netloc:
            return parsed_url.path[1:]
        return None
    
    def get_video_info_via_api(self, video_id):
        """Get video information using YouTube Data API."""
        if not self.youtube_service:
            return None
        
        try:
            request = self.youtube_service.videos().list(
                part="snippet,contentDetails,statistics",
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                item = response['items'][0]
                snippet = item['snippet']
                content_details = item['contentDetails']
                statistics = item['statistics']
                
                # Parse duration from ISO 8601 format (PT4M13S -> 253 seconds)
                duration_iso = content_details['duration']
                duration_seconds = self._parse_iso_duration(duration_iso)
                
                return {
                    'duration': duration_seconds,
                    'title': snippet['title'],
                    'uploader': snippet['channelTitle'],
                    'upload_date': snippet['publishedAt'][:10].replace('-', ''),
                    'view_count': int(statistics.get('viewCount', 0)),
                    'like_count': int(statistics.get('likeCount', 0)),
                    'description': snippet['description']
                }
        except Exception as e:
            print(f"⚠️ YouTube API error: {e}")
        
        return None
    
    def _parse_iso_duration(self, duration_iso):
        """Parse ISO 8601 duration (PT4M13S) to seconds."""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return None
    
    def get_video_info_with_duration(self, url):
        """
        Get video information including duration without downloading.
        Prioritizes YouTube Data API if available, falls back to yt-dlp.
        
        Args:
            url (str): YouTube URL to get information from
            
        Returns:
            dict or None: Video information with duration if successful, None otherwise
            Dictionary contains: {'duration': float, 'title': str, 'uploader': str, etc.}
        """
        # Try YouTube Data API first if available
        video_id = self._extract_video_id(url)
        if video_id and self.youtube_service:
            api_info = self.get_video_info_via_api(video_id)
            if api_info:
                print(f"📡 Retrieved metadata via YouTube Data API")
                return api_info
        
        # Fallback to yt-dlp with anti-detection
        self._rate_limit_delay()
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            ]),
            **({} if getattr(self, 'disable_rate_limit', False) else {'sleep_interval': random.uniform(1, 3)}),
            'retries': 1,
            'fragment_retries': 1,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']
                }
            },
            'noplaylist': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if info is not None:
                duration_raw = info.get('duration')
                print(f"🔧 Retrieved metadata via yt-dlp (android client)")
                return {
                    'duration': float(duration_raw) if duration_raw is not None else None,
                    'title': info.get('title', ''),
                    'uploader': info.get('uploader', ''),
                    'upload_date': info.get('upload_date', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'description': info.get('description', '')
                }
        except Exception as e:
            if self._is_video_unavailable(str(e)):
                setattr(self, '_last_error_reason', 'unavailable')
                print(f"⏭️  Skipping unavailable video: {e}")
                return None
            print(f"⚠️ Metadata retrieval error: {e}")
        return None

    def get_video_duration(self, url):
        """
        Get video duration from YouTube URL without downloading.
        Prioritizes YouTube Data API if available.
        
        Args:
            url (str): YouTube URL to get duration from
            
        Returns:
            float or None: Video duration in seconds if successful, None otherwise
        """
        # Try YouTube Data API first
        video_id = self._extract_video_id(url)
        if video_id and self.youtube_service:
            api_info = self.get_video_info_via_api(video_id)
            if api_info and api_info.get('duration'):
                return api_info['duration']
        
        # Fallback to yt-dlp
        self._rate_limit_delay()
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            ]),
            **({} if getattr(self, 'disable_rate_limit', False) else {'sleep_interval': random.uniform(1, 3)}),
            'retries': 1,
            'fragment_retries': 1,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android']
                }
            },
            'noplaylist': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if info is not None:
                duration = info.get('duration')
                return float(duration) if duration is not None else None
        except Exception as e:
            if self._is_video_unavailable(str(e)):
                setattr(self, '_last_error_reason', 'unavailable')
                print(f"⏭️  Skipping unavailable video: {e}")
                return None
            print(f"⚠️ Error getting video duration: {e}")
        return None
    
    def get_audio_length_from_file(self, audio_file_path):
        """
        Get audio length from an audio file using ffprobe.
        
        Args:
            audio_file_path (str): Path to the audio file
            
        Returns:
            float or None: Audio length in seconds if successful, None otherwise
        """
        try:
            probe = ffmpeg.probe(audio_file_path)
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e:
            print(f"⚠️ Error getting audio length: {e}")
            return None
    
    # =================================================================
    # MAIN DOWNLOAD METHODS
    # =================================================================
    
    def download_audio_from_yturl(self, url, index=0):
        """
        Download audio from YouTube URL and convert to WAV with enhanced anti-detection.
        
        Args:
            url (str): YouTube URL to download
            index (int): Index for output file naming
            
        Returns:
            tuple: (wav_file_path, audio_duration) where audio_duration is in seconds,
                   returns (None, None) if failed
        """
        print("🔧 ============================================")
        print("🔧 DOWNLOAD METHOD: CRAWLER-ALIGNED (Alternative) → yt-dlp")
        print("🔧 ============================================")
        print(f"🎵 Starting download for video {index}")
        print(f"🔗 URL: {url[:80]}...")
        
        # 0) Try the exact same method as the crawler first (most reliable in this repo)
        if self.alt_downloader is not None:
            try:
                print("🔄 Trying crawler's alternative downloader (yt-dlp Android client → pytube fallback)...")
                alt_result = self.alt_downloader.download_audio_yt_dlp_fallback(url, index)
                if not alt_result or not alt_result[0]:
                    print("⚠️ Alternative yt-dlp method returned no result, trying pytube fallback...")
                    try:
                        alt_result = self.alt_downloader.download_audio_pytube(url, index)
                    except Exception as _:
                        alt_result = None
                if alt_result and alt_result[0]:
                    print("🎉 Alternative downloader succeeded")
                    # Ensure target output directory alignment
                    wav_path, duration = alt_result
                    return wav_path, duration
                else:
                    print("⚠️ Alternative downloader failed; falling back to local yt-dlp flow")
            except Exception as e_alt:
                print(f"⚠️ Alternative downloader error: {e_alt}")

        # If alternative path failed or not available, do not use a different method to stay EXACT with crawler
        print("❌ Alternative downloader failed. Not switching methods to remain consistent with crawler.")
        return None, None
        self._rate_limit_delay()
        
        # Optionally get video duration for manifest metadata; do not enforce any length limit here
        print("📏 Getting video duration...")
        video_duration = self.get_video_duration(url)
        if video_duration:
            minutes = int(video_duration // 60)
            seconds = int(video_duration % 60)
            print(f"📊 Video duration: {minutes}:{seconds:02d} ({video_duration}s)")
        else:
            print("⚠️ Could not determine video duration")
        
        # Ensure output directory exists (thread-safe)
        os.makedirs(self.config.output_dir, exist_ok=True)
        print(f"📁 Output directory: {self.config.output_dir}")
        
        # Clean up any existing files with the same index to prevent conflicts
        m4a_file = self.config.get_output_path(self.config.get_m4a_filename(index))
        wav_file = self.config.get_output_path(self.config.get_wav_filename(index))
        part_file = m4a_file + '.part'
        
        print(f"🎯 Target files:")
        print(f"   M4A: {m4a_file}")
        print(f"   WAV: {wav_file}")
        
        # Remove existing files that might cause conflicts
        cleanup_count = self._cleanup_files([m4a_file, wav_file, part_file])
        if cleanup_count > 0:
            print(f"🧹 Cleaned up {cleanup_count} existing file(s)")
        
        # Configure dynamic options with anti-detection (Android client; no cookies)
        print("⚙️ Configuring yt-dlp options...")
        ydl_opts = self._get_dynamic_ydl_opts()
        # Ensure no cookies are applied
        ydl_opts['outtmpl'] = m4a_file
        
        max_retries = 1
        for attempt in range(max_retries):
            try:
                # Add exponential backoff between retries
                if attempt > 0:
                    wait_time = (5 ** attempt) + random.uniform(10, 20)  # Much longer waits: 35-45s, 135-145s, 635-645s
                    print(f"⏳ Waiting {wait_time:.1f}s before retry attempt {attempt + 1}...")
                    time.sleep(wait_time)
                
                print(f"🔄 Download attempt {attempt + 1}/{max_retries}")
                print(f"   User Agent: {ydl_opts.get('user_agent', 'Unknown')[:50]}...")
                
                # Download audio
                print("⏬ Starting yt-dlp download...")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # Verify download
                if not os.path.exists(m4a_file):
                    print(f"❌ Download failed: M4A file not created")
                    continue
                
                file_size = os.path.getsize(m4a_file)
                print(f"✅ M4A downloaded successfully: {file_size} bytes")
                
                # Convert to WAV and get actual audio length
                print("🎵 Converting to WAV format...")
                wav_path, audio_length = self._convert_to_wav_with_duration(index)
                
                if wav_path:
                    # Use actual audio length if available, otherwise fall back to video duration
                    final_duration = audio_length if audio_length is not None else video_duration
                    
                    wav_size = os.path.getsize(wav_path)
                    print("🎉 ============================================")
                    print("🎉 YT-DLP PRIMARY METHOD SUCCESSFUL!")
                    print("🎉 ============================================")
                    print(f"✅ Successfully downloaded and converted audio")
                    print(f"📄 WAV file: {wav_path}")
                    print(f"📊 WAV size: {wav_size} bytes")
                    if final_duration:
                        minutes = int(final_duration // 60)
                        seconds = int(final_duration % 60)
                        print(f"📏 Final duration: {minutes}:{seconds:02d}")
                    return wav_path, final_duration
                else:
                    print(f"❌ WAV conversion failed")
                    continue
                
            except Exception as e:
                error_msg = str(e).lower()
                print(f"❌ Download attempt {attempt + 1} failed: {str(e)[:100]}...")
                
                # Unavailable or removed => mark skip and stop
                if self._is_video_unavailable(error_msg):
                    setattr(self, '_last_error_reason', 'unavailable')
                    print("⏭️  Skipping this video due to availability restrictions")
                    return None, None
                # Clean up any partial files on error
                cleanup_count = self._cleanup_files([m4a_file, wav_file, part_file])
                if cleanup_count > 0:
                    print(f"🧹 Cleaned up {cleanup_count} partial file(s)")

                # Check for specific YouTube blocking errors and fallback
                if self._is_bot_detection_error(error_msg):
                    print(f"🚫 Bot detection triggered on attempt {attempt + 1}")
                    print("❌ Attempt exhausted due to bot detection; trying ffmpeg fallback...")
                    return self.download_audio_via_ffmpeg(url, index)
                else:
                    print(f"⚠️ General download error (attempt {attempt + 1})")
                    print("❌ yt-dlp attempt failed, trying ffmpeg fallback...")
                    return self.download_audio_via_ffmpeg(url, index)
        
        # If we get here, try ffmpeg fallback
        print("❌ yt-dlp method failed, trying ffmpeg fallback as last resort...")
        return self.download_audio_via_ffmpeg(url, index)
    
    def download_audio_via_api(self, url, index=0):
        """
        Download audio using YouTube Data API to bypass bot detection.
        This method gets direct download URLs from the API instead of scraping.
        
        Args:
            url (str): YouTube URL to download
            index (int): Index for output file naming
            
        Returns:
            tuple: (wav_file_path, audio_duration) where audio_duration is in seconds,
                   returns (None, None) if failed
        """
        print("🔧 ============================================")
        print("🔧 API-ASSISTED DOWNLOAD METHOD ACTIVATED")
        print("🔧 ============================================")
        print(f"🎵 Starting API-assisted download for video {index}")
        print(f"🔗 URL: {url[:80]}...")
        
        if not self.youtube_service:
            print("❌ YouTube API not available, falling back to yt-dlp")
            return self.download_audio_from_yturl(url, index)
        
        try:
            # Extract video ID
            print("🔍 Extracting video ID...")
            video_id = self._extract_video_id(url)
            if not video_id:
                print("❌ Could not extract video ID, falling back to yt-dlp")
                return self.download_audio_from_yturl(url, index)
            print(f"✅ Video ID: {video_id}")
            
            # Get video info via API
            print("📡 Getting video info via YouTube Data API...")
            video_info = self.get_video_info_via_api(video_id)
            if not video_info:
                print("❌ Could not get video info via API, falling back to yt-dlp")
                return self.download_audio_from_yturl(url, index)
            
            print(f"✅ API metadata retrieved:")
            print(f"   Title: {video_info.get('title', 'Unknown')[:50]}...")
            print(f"   Duration: {video_info.get('duration', 'Unknown')}s")
            print(f"   Uploader: {video_info.get('uploader', 'Unknown')}")
            
            # Use yt-dlp with API-provided metadata to reduce scraping
            print("🔄 Using yt-dlp with API metadata to reduce scraping...")
            return self._download_with_api_metadata(url, video_info, index)
            
        except Exception as e:
            print(f"❌ API download failed: {str(e)[:100]}...")
            print("🔄 Falling back to yt-dlp standard method")
            return self.download_audio_from_yturl(url, index)
    
    def _download_with_api_metadata(self, url, video_info, index):
        """
        Download using yt-dlp but with API metadata to reduce scraping needs.
        """
        self._rate_limit_delay()
        
        # Ensure output directory exists
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # Clean up existing files
        m4a_file = self.config.get_output_path(self.config.get_m4a_filename(index))
        wav_file = self.config.get_output_path(self.config.get_wav_filename(index))
        part_file = m4a_file + '.part'
        
        self._cleanup_files([m4a_file, wav_file, part_file])
        
        # Enhanced yt-dlp options with API metadata
        ydl_opts = self._get_dynamic_ydl_opts()
        ydl_opts = self._apply_cookies_to_opts(ydl_opts) # Apply cookies here
        ydl_opts['outtmpl'] = m4a_file
        
        # Add metadata from API to reduce scraping
        if video_info.get('title'):
            ydl_opts['writethumbnail'] = False  # Skip thumbnail to reduce requests
            ydl_opts['writesubtitles'] = False  # Skip subtitles to reduce requests
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = (5 ** attempt) + random.uniform(10, 20)  # Much longer waits: 35-45s, 135-145s, 635-645s
                    print(f"⏳ Waiting {wait_time:.1f}s before retry attempt {attempt + 1}...")
                    time.sleep(wait_time)
                
                print(f"🔄 API-assisted download attempt {attempt + 1}/{max_retries}")
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # Convert to WAV
                wav_path, audio_length = self._convert_to_wav_with_duration(index)
                final_duration = audio_length if audio_length is not None else video_info.get('duration')
                
                print(f"✅ Successfully downloaded via API-assisted method")
                return wav_path, final_duration
                
            except Exception as e:
                error_msg = str(e)
                
                if self._is_bot_detection_error(error_msg):
                    print(f"🚫 Bot detection still triggered, trying alternative method...")
                    # Try with different yt-dlp options
                    return self._try_alternative_download_method(url, index, attempt)
                else:
                    print(f"⚠️ Download error (attempt {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        print("❌ All yt-dlp attempts failed, trying ffmpeg fallback...")
                        # Try ffmpeg as final fallback
                        return self.download_audio_via_ffmpeg(url, index)
                
                # Clean up partial files
                self._cleanup_files([m4a_file, wav_file, part_file])
        
        # If we get here, all yt-dlp attempts failed, try ffmpeg fallback
        print("❌ All yt-dlp methods exhausted, trying ffmpeg fallback as last resort...")
        return self.download_audio_via_ffmpeg(url, index)
    
    def _try_alternative_download_method(self, url, index, attempt):
        """
        Try alternative download methods when bot detection occurs.
        """
        print(f"🔄 Trying alternative download method {attempt + 1}...")
        
        # Method 1: Use different user agent and headers
        ydl_opts = self._get_dynamic_ydl_opts()
        ydl_opts = self._apply_cookies_to_opts(ydl_opts) # Apply cookies here
        ydl_opts['outtmpl'] = self.config.get_output_path(self.config.get_m4a_filename(index))
        
        # Add more browser-like headers
        ydl_opts['http_headers'].update({
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-GPC': '1',
        })
        
        # Use cookies from instance settings or fallback to browser
        if self.cookies_file and os.path.exists(self.cookies_file):
            ydl_opts['cookiefile'] = self.cookies_file
        elif self.cookies_from_browser:
            ydl_opts['cookiesfrombrowser'] = (self.cookies_from_browser,)
        else:
            # Fallback to chrome cookies if no other option
            try:
                ydl_opts['cookiesfrombrowser'] = ('chrome',)
            except:
                pass
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            wav_path, audio_length = self._convert_to_wav_with_duration(index)
            print(f"✅ Alternative method succeeded")
            return wav_path, audio_length
            
        except Exception as e:
            print(f"⚠️ Alternative yt-dlp method failed: {e}")
            print("🔄 Trying ffmpeg fallback as final alternative...")
            return self.download_audio_via_ffmpeg(url, index)
    
    # =================================================================
    # FFMPEG CONVERSION AND FALLBACK METHODS
    # =================================================================
    
    def _find_ffmpeg_executable(self):
        """Find FFmpeg executable in system PATH or common locations."""
        # Try to find ffmpeg in PATH first
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path:
            return ffmpeg_path
        
        # Common FFmpeg locations on Windows
        common_paths = FFMPEG_COMMON_PATHS + [
            os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe"),  # Python Scripts directory
            os.path.join(os.path.dirname(sys.executable), "Scripts", "ffmpeg.exe"),  # Python Scripts/Scripts directory
        ]
        
        # Check if any of the common paths exist
        for path in common_paths:
            if os.path.isfile(path):
                return path
        
        # Try to use subprocess to test if ffmpeg is available
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return 'ffmpeg'  # Available in PATH but shutil.which didn't find it
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        return None
    
    def _convert_to_wav_with_duration(self, index):
        """
        Convert M4A file to WAV format and return both path and duration.
        
        Args:
            index (int): Index for file naming
            
        Returns:
            tuple: (wav_file_path, audio_duration_seconds) or (None, None) if failed
        """
        input_file = self.config.get_output_path(self.config.get_m4a_filename(index))
        output_file = self.config.get_output_path(self.config.get_wav_filename(index))
        
        # Check if input file exists before conversion
        if not os.path.exists(input_file):
            print(f"⚠️ Input file not found: {input_file}")
            return None, None
        
        try:
            # Remove output file if it already exists to prevent conflicts
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except OSError:
                    pass
            
            # Find FFmpeg executable
            ffmpeg_path = self._find_ffmpeg_executable()
            if not ffmpeg_path:
                print("⚠️ FFmpeg not found in system PATH or common locations.")
                print("💡 Please install FFmpeg:")
                print("   1. Download from: https://ffmpeg.org/download.html")
                print("   2. Extract to C:\\ffmpeg\\ ")
                print("   3. Add C:\\ffmpeg\\bin to your system PATH")
                print("   4. Restart your terminal/IDE")
                return None, None
            
            print(f"🔧 Using FFmpeg from: {ffmpeg_path}")
            
            # Try multiple conversion methods
            conversion_methods = [
                self._convert_with_ffmpeg_python,
                self._convert_with_subprocess,
                self._convert_with_basic_command
            ]
            
            for method in conversion_methods:
                try:
                    success = method(input_file, output_file, ffmpeg_path)
                    if success:
                        break
                except Exception as e:
                    print(f"⚠️ Conversion method failed: {e}")
                    continue
            else:
                print("❌ All conversion methods failed")
                return None, None
            
            # Verify conversion was successful
            if not os.path.exists(output_file):
                print(f"⚠️ Conversion failed: output file not created")
                return None, None
            
            # Get audio duration from the converted WAV file
            audio_duration = None
            try:
                audio_duration = self.get_audio_length_from_file(output_file)
            except Exception as duration_error:
                print(f"⚠️ Warning: Could not get audio duration: {duration_error}")
                # Continue anyway, duration is not critical
            
            # Clean up intermediate file
            if os.path.exists(input_file):
                try:
                    os.remove(input_file)
                except OSError as cleanup_error:
                    print(f"⚠️ Warning: Could not remove intermediate file: {cleanup_error}")
            
            print(f"✅ Audio successfully converted to WAV")
            return output_file, audio_duration
                
        except Exception as e:
            print(f"⚠️ Error converting to WAV: {e}")
            # Clean up both intermediate and output files on error
            self._cleanup_files([input_file, output_file])
            return None, None
    
    def _convert_with_ffmpeg_python(self, input_file, output_file, ffmpeg_path):
        """Convert using ffmpeg-python library."""
        try:
            stream = ffmpeg.input(input_file)
            stream = ffmpeg.output(stream, output_file)
            ffmpeg.run(stream, cmd=ffmpeg_path, quiet=True, overwrite_output=True)
            return True
        except Exception:
            # Try without explicit cmd parameter
            stream = ffmpeg.input(input_file)
            stream = ffmpeg.output(stream, output_file)
            ffmpeg.run(stream, quiet=True, overwrite_output=True)
            return True
    
    def _convert_with_subprocess(self, input_file, output_file, ffmpeg_path):
        """Convert using subprocess directly."""
        import subprocess
        cmd = [ffmpeg_path, '-i', input_file, '-y', output_file]
        try:
            # Use shorter timeout and better process control
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                     stdin=subprocess.PIPE, text=True)
            process.stdin.close()
            stdout, stderr = process.communicate(timeout=CONVERSION_TIMEOUT_SECONDS)  # Extended from 2min to 3min
            return process.returncode == 0
        except subprocess.TimeoutExpired:
            print("⏰ FFmpeg conversion timeout, killing process...")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            return False
    
    def _convert_with_basic_command(self, input_file, output_file, ffmpeg_path):
        """Convert using basic os.system command."""
        cmd = f'"{ffmpeg_path}" -i "{input_file}" -y "{output_file}"'
        return os.system(cmd) == 0
    
    def _convert_to_wav(self, index):
        """
        Convert M4A file to WAV format.
        
        Args:
            index (int): Index for file naming
            
        Returns:
            str or None: Path to output WAV file if successful, None otherwise
        """
        wav_path, _ = self._convert_to_wav_with_duration(index)
        return wav_path

    def set_cookies_from_file(self, cookies_file_path):
        """
        Set cookies from a Netscape format cookies file.
        
        Args:
            cookies_file_path (str): Path to the cookies file
        """
        if os.path.exists(cookies_file_path):
            self.cookies_file = cookies_file_path
            self.cookies_from_browser = None
            print(f"🍪 Cookies set from file: {cookies_file_path}")
        else:
            print(f"⚠️ Cookies file not found: {cookies_file_path}")
    
    def set_cookies_from_browser(self, browser_name):
        """
        Set cookies from a browser.
        
        Args:
            browser_name (str): Browser name ('chrome', 'firefox', 'safari', 'edge', 'opera', 'brave')
        """
        if browser_name.lower() in SUPPORTED_BROWSERS:
            self.cookies_from_browser = browser_name.lower()
            self.cookies_file = None
            print(f"🍪 Cookies set from browser: {browser_name}")
        else:
            print(f"⚠️ Unsupported browser: {browser_name}. Supported: {', '.join(SUPPORTED_BROWSERS)}")
    
    def download_audio_via_ffmpeg(self, url, index=0):
        """
        Download and convert YouTube audio using ffmpeg directly.
        This method uses yt-dlp only to get the direct stream URL, then uses ffmpeg for downloading.
        
        Args:
            url (str): YouTube video URL
            index (int): Index for unique filename generation
            
        Returns:
            tuple: (wav_file_path, duration) or (None, None) if failed
        """
        print("🔧 ============================================")
        print("🔧 FFMPEG FALLBACK METHOD ACTIVATED")
        print("🔧 yt-dlp has failed, trying direct ffmpeg approach")
        print("🔧 ============================================")
        print(f"🎵 Starting ffmpeg-based download for video {index}")
        
        # Generate unique output filename
        timestamp = int(time.time() * 1000)  # Millisecond timestamp
        process_id = os.getpid()
        wav_file = os.path.join(self.config.base_dir, f"youtube_audio_{index}_{timestamp}_{process_id}.wav")
        
        try:
            # Step 1: Get direct stream URL using yt-dlp
            print("📡 Getting direct stream URL...")
            
            # Build yt-dlp command to extract URL only with Android client
            cmd_get_url = [
                "yt-dlp", 
                "--get-url", 
                "-f", "bestaudio/best",
                "--extractor-args", "youtube:player_client=android",  # Use Android client to bypass restrictions
                "--user-agent", self.config.ydl_opts.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0')
            ]
            
            # Add cookies if configured
            if self.cookies_file and os.path.exists(self.cookies_file):
                cmd_get_url.extend(["--cookies", self.cookies_file])
            elif self.cookies_from_browser:
                cmd_get_url.extend(["--cookies-from-browser", self.cookies_from_browser])
            
            cmd_get_url.append(url)
            
            # Execute yt-dlp to get direct URL with better timeout handling
            try:
                process = subprocess.Popen(cmd_get_url, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                         stdin=subprocess.PIPE, text=True)
                process.stdin.close()
                stdout, stderr = process.communicate(timeout=YT_DLP_TIMEOUT_SECONDS)
                result = type('Result', (), {'returncode': process.returncode, 'stdout': stdout, 'stderr': stderr})()
            except subprocess.TimeoutExpired:
                print("⏰ yt-dlp URL extraction timeout")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                return None, None
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                print(f"❌ Failed to get stream URL: {error_msg}")
                return None, None
            
            direct_url = result.stdout.strip()
            if not direct_url:
                print("❌ No stream URL returned")
                return None, None
                
            print(f"✅ Got direct stream URL: {direct_url[:100]}...")
            
            # Step 2: Use ffmpeg to download and convert
            print("🎵 Downloading and converting with ffmpeg...")
            
            # Build ffmpeg command
            cmd_ffmpeg = [
                "ffmpeg",
                "-i", direct_url,
                "-vn",  # No video
                "-acodec", "pcm_s16le",  # Convert to WAV PCM
                "-ar", "16000",  # 16kHz sample rate
                "-ac", "1",  # Mono
                "-t", str(DEFAULT_MAX_AUDIO_DURATION),  # Limit to 5 minutes max
                "-y",  # Overwrite existing file
                wav_file
            ]
            
            # Add user agent to ffmpeg
            cmd_ffmpeg = [
                "ffmpeg",
                "-user_agent", self.config.ydl_opts.get('user_agent', DEFAULT_USER_AGENT),
                "-i", direct_url,
                "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "-t", str(DEFAULT_MAX_AUDIO_DURATION), "-y",
                wav_file
            ]
            
            # Execute ffmpeg with better timeout handling
            try:
                process = subprocess.Popen(cmd_ffmpeg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                         stdin=subprocess.PIPE, text=True)
                process.stdin.close()
                stdout, stderr = process.communicate(timeout=FFMPEG_TIMEOUT_SECONDS)  # Extended from 2min to 3min
                result = type('Result', (), {'returncode': process.returncode, 'stdout': stdout, 'stderr': stderr})()
            except subprocess.TimeoutExpired:
                print("⏰ FFmpeg download timeout")
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                return None, None
            
            if result.returncode != 0:
                error_msg = result.stderr.strip()
                print(f"❌ ffmpeg failed: {error_msg}")
                return None, None
            
            # Verify file was created
            if not os.path.exists(wav_file):
                print("❌ WAV file was not created")
                return None, None
            
            # Get audio duration
            audio_duration = None
            try:
                audio_duration = self.get_audio_length_from_file(wav_file)
                if audio_duration:
                    minutes = int(audio_duration // 60)
                    seconds = int(audio_duration % 60)
                    print(f"📏 Audio duration: {minutes}:{seconds:02d}")
            except Exception as duration_error:
                print(f"⚠️ Could not get audio duration: {duration_error}")
            
            print("🎉 ============================================")
            print("🎉 FFMPEG FALLBACK METHOD SUCCESSFUL!")
            print("🎉 Downloaded when yt-dlp failed")
            print("🎉 ============================================")
            print(f"✅ Successfully downloaded via ffmpeg method: {wav_file}")
            return wav_file, audio_duration
            
        except subprocess.TimeoutExpired:
            print("❌ Download timeout (ffmpeg method)")
            return None, None
        except Exception as e:
            print(f"❌ ffmpeg download error: {e}")
            return None, None
        finally:
            # Clean up on error
            if os.path.exists(wav_file) and (not hasattr(self, '_last_successful_file') or self._last_successful_file != wav_file):
                try:
                    # Only remove if the download wasn't successful
                    if not os.path.exists(wav_file) or os.path.getsize(wav_file) == 0:
                        os.remove(wav_file)
                except OSError:
                    pass
    def clear_cookies(self):
        """Clear all cookie settings."""
        self.cookies_file = None
        self.cookies_from_browser = None
        print("🍪 Cookies cleared")
    
    def get_cookie_status(self):
        """
        Get current cookie configuration status.
        
        Returns:
            dict: Cookie configuration information
        """
        cookie_file_size = 0
        if self.cookies_file and os.path.exists(self.cookies_file):
            try:
                cookie_file_size = os.path.getsize(self.cookies_file)
            except OSError:
                pass
        
        return {
            'cookies_file': self.cookies_file,
            'cookies_from_browser': self.cookies_from_browser,
            'cookies_file_exists': os.path.exists(self.cookies_file) if self.cookies_file else False,
            'cookies_file_size': cookie_file_size
        }

    # =================================================================
    # TEST AND UTILITY METHODS
    # =================================================================

    def test_video_duration_extraction(self, url):
        """
        Test method to verify video duration extraction without downloading.
        
        Args:
            url (str): YouTube URL to test
            
        Returns:
            dict: Test results with duration and metadata
        """
        print(f"🧪 Testing video duration extraction for: {url}")
        
        # Test duration extraction
        duration = self.get_video_duration(url)
        print(f"📏 Video duration: {duration} seconds")
        if duration:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            print(f"📏 Video duration formatted: {minutes}:{seconds:02d}")
        
        # Test full video info extraction
        video_info = self.get_video_info_with_duration(url)
        if video_info:
            print(f"📺 Video title: {video_info.get('title', 'N/A')}")
            print(f"👤 Uploader: {video_info.get('uploader', 'N/A')}")
            print(f"📅 Upload date: {video_info.get('upload_date', 'N/A')}")
            print(f"👁️ View count: {video_info.get('view_count', 'N/A')}")
        
        return {
            'url': url,
            'duration_seconds': duration,
            'video_info': video_info,
            'success': duration is not None
        }


# =================================================================
# MAIN FUNCTION AND CLI INTERFACE
# =================================================================

def main():
    """Main function to handle command line interface with behavior aligned to the alternative script."""
    # Parse command line arguments for language mapping
    language_mapping = {}
    args = sys.argv[1:]
    
    # Check for language mapping argument
    if '--language-mapping' in args:
        mapping_index = args.index('--language-mapping')
        if mapping_index + 1 < len(args):
            mapping_file = args[mapping_index + 1]
            try:
                with open(mapping_file, 'r', encoding='utf-8') as f:
                    language_mapping = json.load(f)
                print(f"[INFO] Loaded language mapping from {mapping_file} ({len(language_mapping)} URLs)")
            except Exception as e:
                print(f"[WARNING] Failed to load language mapping: {e}")
            # Remove mapping arguments from args list
            args = args[:mapping_index] + args[mapping_index + 2:]
    
    config = Config(language_mapping=language_mapping)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    final_output_dir = os.path.join(base_dir, 'final_audio_files')
    os.makedirs(final_output_dir, exist_ok=True)
    
    # Create language subfolders
    vietnamese_dir = os.path.join(final_output_dir, 'vietnamese')
    unknown_dir = os.path.join(final_output_dir, 'unknown')
    os.makedirs(vietnamese_dir, exist_ok=True)
    os.makedirs(unknown_dir, exist_ok=True)
    print(f"📁 Created language folders: vietnamese/ and unknown/")
    
    config.output_dir = final_output_dir

    # Initialize downloader early (no special CLI flags; behavior mirrors alternative script)
    downloader = YoutubeAudioDownloader(config, language_mapping=language_mapping)
    setattr(downloader, 'no_length_limit', True)
    setattr(downloader, 'disable_rate_limit', True)
    
    manifest_path = os.path.join(final_output_dir, 'manifest.json')
    
    def _load_manifest(path):
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        records = data
                        try:
                            total = float(sum(float(r.get('duration_seconds', 0) or 0) for r in records))
                        except Exception:
                            total = 0.0
                        return {'total_duration_seconds': total, 'records': records}
                    elif isinstance(data, dict):
                        records = data.get('records', []) or []
                        if 'total_duration_seconds' not in data:
                            try:
                                data['total_duration_seconds'] = float(sum(float(r.get('duration_seconds', 0) or 0) for r in records))
                            except Exception:
                                data['total_duration_seconds'] = 0.0
                        else:
                            try:
                                data['total_duration_seconds'] = float(data['total_duration_seconds'])
                            except Exception:
                                data['total_duration_seconds'] = 0.0
                        data['records'] = records
                        return data
        except Exception:
            pass
        return {'total_duration_seconds': 0.0, 'records': []}
    
    def _save_manifest(path, manifest_data):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(manifest_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Unable to write manifest: {e}")
    
    def _index_manifest(records):
        by_id = {}
        for rec in records:
            vid = rec.get('video_id')
            if vid:
                by_id[vid] = rec
        return by_id
    
    manifest_data = _load_manifest(manifest_path)
    manifest_records = manifest_data.get('records', [])
    manifest_index = _index_manifest(manifest_records)

    # Backfill missing titles (mirrors alternative script timing; use metadata to avoid downloads)
    def _backfill_missing_titles_similar_behavior():
        updated = False
        updated_count = 0
        failed_count = 0
        skipped_count = 0
        total_missing = sum(1 for r in manifest_records if r.get('status') == 'success' and not r.get('title'))
        
        if total_missing:
            print(f"🔧 Backfilling titles for {total_missing} records without titles...")
            print("=" * 60)
        else:
            print("✅ All records already have titles - no backfilling needed")
            return
            
        for idx_bf, rec in enumerate(manifest_records, start=1):
            try:
                if rec.get('status') == 'success' and not rec.get('title'):
                    url_val = rec.get('url')
                    if not url_val:
                        vid_local = rec.get('video_id')
                        if vid_local:
                            url_val = f"https://www.youtube.com/watch?v={vid_local}"
                    if not url_val:
                        vid_print = rec.get('video_id') or 'unknown'
                        print(f"⏭️  [{idx_bf}/{len(manifest_records)}] Skipping record {vid_print}: No URL available")
                        skipped_count += 1
                        continue
                    
                    vid_print = rec.get('video_id') or url_val[:50] + "..."
                    print(f"🔍 [{idx_bf}/{len(manifest_records)}] Processing: {vid_print}")
                    
                    title_val = None
                    try:
                        info = downloader.get_video_info_with_duration(url_val)
                        if info and info.get('title'):
                            title_val = info['title']
                            print(f"   🎯 Found title: {title_val[:50]}...")
                        else:
                            print("   ⚠️ No title found in metadata")
                    except Exception as e:
                        print(f"   ❌ Metadata extraction failed: {str(e)[:100]}...")
                    
                    if title_val:
                        rec['title'] = title_val
                        updated = True
                        updated_count += 1
                        try:
                            manifest_data['records'] = manifest_records
                            _save_manifest(manifest_path, manifest_data)
                            print("   💾 Manifest updated incrementally")
                        except Exception as save_error:
                            print(f"   ⚠️ Incremental save failed: {save_error}")
                    else:
                        failed_count += 1
                        print(f"   ❌ FAILED: Could not retrieve title for {vid_print}")
            except Exception as record_error:
                failed_count += 1
                vid_print = rec.get('video_id', 'unknown') if rec else 'unknown'
                print(f"❌ [{idx_bf}/{len(manifest_records)}] Record processing failed for {vid_print}: {str(record_error)[:100]}...")
        
        print("=" * 60)
        print("📊 BACKFILL SUMMARY:")
        print(f"   📋 Total records processed: {len(manifest_records)}")
        print(f"   🔍 Records needing titles: {total_missing}")
        print(f"   ✅ Successfully updated: {updated_count}")
        print(f"   ❌ Failed to update: {failed_count}")
        print(f"   ⏭️  Skipped (no URL): {skipped_count}")
        
        if updated:
            try:
                print("💾 Finalizing manifest update...")
                try:
                    manifest_data['total_duration_seconds'] = float(sum(float(r.get('duration_seconds', 0) or 0) for r in manifest_records))
                except Exception:
                    manifest_data['total_duration_seconds'] = 0.0
                manifest_data['records'] = manifest_records
                _save_manifest(manifest_path, manifest_data)
                print("✅ Backfill complete!")
            except Exception as final_save_error:
                print(f"❌ Final manifest save failed: {final_save_error}")
                
    _backfill_missing_titles_similar_behavior()

    def _to_camel_case_lower_suffix(text: str, max_len: int = 40) -> str:
        try:
            import re
            words = re.split(r'[^a-z0-9]+', (text or '').lower())
            words = [w for w in words if w]
            camel = ''.join(w.capitalize() for w in words)
            return camel[:max_len] if camel else 'NoTitle'
        except Exception:
            return 'NoTitle'
    
    def _build_basename(idx: int, url: str) -> str:
        # Try to derive title via pytube (cheap; already used later) - match alternative exactly
        title = None
        try:
            from pytubefix import YouTube
            yt_tmp = YouTube(url)
            title = yt_tmp.title
        except Exception:
            try:
                from pytube import YouTube
                yt_tmp = YouTube(url)
                title = yt_tmp.title
            except Exception:
                title = None
        # Extract video id - match alternative exactly
        vid_local = None
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            if 'youtube.com' in parsed.netloc:
                vid_local = parse_qs(parsed.query).get('v', [None])[0]
            elif 'youtu.be' in parsed.netloc:
                vid_local = parsed.path[1:]
        except Exception:
            pass
        camel = _to_camel_case_lower_suffix(title or '')
        short_id = (vid_local or 'noid')[:8]
        return f"{idx:04d}_{short_id}_{camel}"
    
    def _run_single(url: str, index: int):
        """Download a single URL with language-specific organization."""
        print(f"🎯 Processing URL {index}: {url}")
        
        # Determine language classification and output directory
        language_folder = language_mapping.get(url, 'unknown')
        language_output_dir = os.path.join(final_output_dir, language_folder)
        os.makedirs(language_output_dir, exist_ok=True)
        
        print(f"📁 Language classification: {language_folder}")
        print(f"📂 Output directory: {language_output_dir}")
        
        # Load language-specific manifest
        language_manifest_path = os.path.join(language_output_dir, 'manifest.json')
        language_manifest_data = _load_manifest(language_manifest_path)
        language_manifest_records = language_manifest_data.get('records', [])
        language_manifest_index = _index_manifest(language_manifest_records)
        
        # Check if already downloaded in this language folder
        vid = downloader._extract_video_id(url)
        if vid and vid in language_manifest_index and language_manifest_index[vid].get('status') == 'success':
            print(f"⏭️  Already downloaded in {language_folder} folder (skipping duplicate)")
            return
            
        # Update config to use language-specific directory temporarily
        original_output_dir = config.output_dir
        config.output_dir = language_output_dir
        
        try:
            # Set basename on the alternative downloader 
            basename = _build_basename(index, url)
            if hasattr(downloader, 'alt_downloader') and downloader.alt_downloader:
                downloader.alt_downloader._current_basename = basename
                
            result = downloader.download_audio_from_yturl(url, index=index)
            
            # Clear basename after download
            if hasattr(downloader, 'alt_downloader') and downloader.alt_downloader:
                downloader.alt_downloader._current_basename = None
            
            if isinstance(result, tuple):
                wav_path, duration = result
                if wav_path:
                    print(f"✅ Saved: {wav_path} ({duration}s)")
                    title_val = ''
                    try:
                        # Match alternative downloader's title extraction approach
                        from pytubefix import YouTube
                        yt_tmp2 = YouTube(url)
                        title_val = yt_tmp2.title or ''
                    except Exception:
                        try:
                            from pytube import YouTube
                            yt_tmp2 = YouTube(url)
                            title_val = yt_tmp2.title or ''
                        except Exception:
                            title_val = ''
                    
                    # Create record for language-specific manifest
                    record = {
                        'video_id': vid or '',
                        'url': url,
                        'output_path': wav_path,
                        'status': 'success',
                        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                        'duration_seconds': duration,
                        'title': title_val,
                        'language_folder': language_folder,
                        'download_index': index
                    }
                    
                    # Add to language-specific manifest
                    if vid:
                        language_manifest_index[vid] = record
                    language_manifest_records.append(record)
                    language_manifest_data['records'] = language_manifest_records
                    language_manifest_data['total_duration_seconds'] = sum(r.get('duration_seconds', 0) for r in language_manifest_records)
                    _save_manifest(language_manifest_path, language_manifest_data)
                    print(f"📋 Updated {language_folder} manifest: {len(language_manifest_records)} files, {language_manifest_data['total_duration_seconds']:.1f}s total")
                else:
                    print("❌ Download failed")
            else:
                print("❌ Download failed")
        finally:
            # Restore original output directory
            config.output_dir = original_output_dir

    args = args  # Use the modified args list after removing language mapping arguments
    default_urls_file = os.path.join(base_dir, 'youtube_url_outputs', 'collected_video_urls.txt')

    if not args:
        if os.path.exists(default_urls_file):
            with open(default_urls_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip().startswith('http')]
            print(f"📋 Batch download from: {default_urls_file} ({len(urls)} URLs)")
            print(f"🌍 Language mapping: {len(language_mapping)} URLs classified")
            for idx, url in enumerate(urls, start=1):
                print(f"\n===== [{idx}/{len(urls)}] {url} =====\n")
                _run_single(url, idx)
            print("\n🎉 Batch download completed")
        else:
            print("⚠️ No URLs file found. Usage: python youtube_audio_downloader.py <url>|--from-file <path>")
            return
                
    if args[0] == '--from-file' and len(args) >= 2:
        file_path = args[1]
        if not os.path.exists(file_path):
            print("❌ URLs file not found")
            sys.exit(1)
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip().startswith('http')]
        print(f"📋 Batch download from: {file_path} ({len(urls)} URLs)")
        for idx, url in enumerate(urls, start=1):
            print(f"\n===== [{idx}/{len(urls)}] {url} =====")
            _run_single(url, idx)
        print("\n🎉 Batch download completed")
        return
                
    for i, url in enumerate(args, start=1):
        _run_single(url, i)

if __name__ == "__main__":
    main()

