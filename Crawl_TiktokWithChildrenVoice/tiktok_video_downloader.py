#!/usr/bin/env python3
"""
TikTok Video Downloader Module

This module provides functionality to download TikTok videos and convert them to audio
for analysis. Adapted from the existing TikTok RapidAPI downloader with enhancements
for the children's voice detection pipeline.

Features:
    - Direct video download from TikTok URLs
    - Audio extraction and conversion
    - Error handling and retry logic
    - Temporary file management
    - Enhanced API key rotation for better rate limit handling
    - Multiple download methods with API23 fallback
    - Automatic audio conversion with FFmpeg
    - Comprehensive error handling and statistics

Author: Generated fo            # Method 1: Try yt-dlp first (primary method - most reliable)
            tiktok_url = video_info.get('url')
            if tiktok_url and self.has_ytdlp:
                self._log("🐍 Method 1: yt-dlp download (primary method)...")
                download_success = self.download_video_ytdlp(tiktok_url, str(temp_video_path))
            
            # Method 2: Try TikTok API23 fallback
            if not download_success and tiktok_url:
                self._log("🚀 Method 2: TikTok API23 download fallback...")
                download_success = self.download_video_api23(tiktok_url, str(temp_video_path))hildren's Voice Crawler
Version: 1.0
"""

import os
import sys
import time
import requests
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
import urllib.parse as urlparse
import json

# Constants
MIN_FILE_SIZE_BYTES = 1000
DEFAULT_CHUNK_SIZE = 8192
AUDIO_CONVERSION_TIMEOUT = 60
DEPENDENCY_CHECK_TIMEOUT = 10

# TikTok API23 Configuration
TIKTOK_API23_HOST = "tiktok-api23.p.rapidapi.com"
TIKTOK_API23_ENDPOINT = "/api/download/video"

# TikTok-specific request headers for video downloads
TIKTOK_HEADERS_CONFIGS = [
    {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Referer': 'https://www.tiktok.com/',
        'Origin': 'https://www.tiktok.com'
    },
    {
        'User-Agent': 'TikTok 26.2.0 rv:262018 (iPhone; iOS 14.4.2; en_US) Cronet',
        'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://www.tiktok.com/'
    },
    {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_4_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate'
    }
]

# Import environment configuration
try:
    from env_config import config
    USE_ENV_CONFIG = True
except ImportError:
    config = None
    USE_ENV_CONFIG = False


class TikTokVideoDownloader:
    """TikTok video downloader with audio extraction capabilities."""
    
    def __init__(self, output_manager=None):
        """
        Initialize TikTok video downloader.
        
        Args:
            output_manager: Optional output manager for logging
        """
        self.output = output_manager
        
        # Configuration from environment
        if USE_ENV_CONFIG and config:
            self.download_timeout = getattr(config, 'DOWNLOAD_TIMEOUT', 120)
            self.max_video_duration = getattr(config, 'MAX_VIDEO_DURATION', 600)
            self.temp_audio_dir = getattr(config, 'TEMP_AUDIO_DIR', './temp_audio')
        else:
            # Fallback configuration
            self.download_timeout = 120
            self.max_video_duration = 600
            self.temp_audio_dir = "./temp_audio"
        
        # Create temporary directories
        self.temp_dir = Path(tempfile.gettempdir()) / "tiktok_crawler"
        self.temp_audio_path = Path(self.temp_audio_dir)
        
        self.temp_dir.mkdir(exist_ok=True)
        self.temp_audio_path.mkdir(exist_ok=True)
        
        # Download statistics
        self.total_downloads = 0
        self.successful_downloads = 0
        self.failed_downloads = 0
        
        # API key management for API23
        self.api_keys = self._load_api_keys()
        self.current_key_index = 0
        
        # Check dependencies
        self.has_ffmpeg = self._check_ffmpeg()
        self.has_ytdlp = self._check_ytdlp()
        
        self._log("✅ TikTok Video Downloader initialized")
    
    def _load_api_keys(self) -> List[str]:
        """Load and validate API keys from environment configuration."""
        api_keys = []
        
        if USE_ENV_CONFIG and config:
            # Try to get multiple API keys first
            keys_data = getattr(config, 'TIKTOK_API_KEYS', None)
            if keys_data:
                if isinstance(keys_data, list):
                    # Already a list
                    keys = [key.strip() for key in keys_data if key and key.strip()]
                elif isinstance(keys_data, str):
                    # String that needs splitting
                    keys = [key.strip() for key in keys_data.split(',') if key.strip()]
                else:
                    keys = []
                
                api_keys.extend(keys)
                self._log(f"✅ Loaded {len(keys)} API keys from TIKTOK_API_KEYS")
            
            # Also check single key configurations (with error handling)
            single_key_names = ['RAPIDAPI_KEY', 'TIKTOK_RAPIDAPI_KEY', 'TIKTOK_API_KEY']
            
            for key_name in single_key_names:
                try:
                    key = getattr(config, key_name, None)
                    if key and key not in api_keys:
                        api_keys.append(key)
                except (ValueError, AttributeError):
                    # Skip if the key is required but not set
                    continue
        
        # Fallback to hardcoded key if no keys found
        if not api_keys:
            fallback_key = "eaf976b22dmsh29e0ce2fce2c011p1f0438jsn5acabaf9a18d"
            api_keys.append(fallback_key)
            self._log("⚠️ No API keys in config, using fallback key", "warning")
        
        # Mask keys for logging
        masked_keys = [f"{key[:10]}...{key[-4:]}" for key in api_keys]
        self._log(f"🔑 API keys loaded: {masked_keys}")
        
        return api_keys
    
    def _get_next_api_key(self) -> str:
        """Get the next API key in rotation."""
        if not self.api_keys:
            return "eaf976b22dmsh29e0ce2fce2c011p1f0438jsn5acabaf9a18d"  # Fallback
        
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key
    
    def _rotate_api_key(self) -> str:
        """Rotate to the next API key when current one fails."""
        if len(self.api_keys) > 1:
            old_index = (self.current_key_index - 1) % len(self.api_keys)
            new_key = self._get_next_api_key()
            self._log(f"🔄 Rotating API key from index {old_index} to {self.current_key_index}")
            return new_key
        else:
            self._log("⚠️ Only one API key available, cannot rotate", "warning")
            return self.api_keys[0] if self.api_keys else "eaf976b22dmsh29e0ce2fce2c011p1f0438jsn5acabaf9a18d"
    
    def _log(self, message: str, level: str = "info") -> None:
        """Log message through output manager if available."""
        if self.output:
            if level == "error":
                self.output.print_error(message)
            elif level == "warning":
                self.output.print_warning(message)
            else:
                self.output.print_info(message)
        else:
            print(f"[{level.upper()}] {message}")
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=DEPENDENCY_CHECK_TIMEOUT)
            if result.returncode == 0:
                self._log("✅ FFmpeg is available")
                return True
            else:
                self._log("⚠️ FFmpeg not found but command exists", "warning")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._log("❌ FFmpeg not found. Please install FFmpeg for audio conversion.", "error")
            return False
        except Exception as e:
            self._log(f"⚠️ Error checking FFmpeg: {e}", "warning")
            return False
    
    def _check_ytdlp(self) -> bool:
        """Check if yt-dlp is available as primary downloader."""
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=DEPENDENCY_CHECK_TIMEOUT)
            if result.returncode == 0:
                version = result.stdout.strip().split('\n')[0]
                self._log(f"✅ yt-dlp is available ({version})")
                return True
            else:
                self._log("⚠️ yt-dlp command failed", "warning")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self._log("⚠️ yt-dlp not available. Install with: pip install yt-dlp", "warning")
            return False
        except Exception as e:
            self._log(f"⚠️ Error checking yt-dlp: {e}", "warning")
            return False
    
    def extract_tiktok_id(self, url: str) -> Optional[str]:
        """
        Extract TikTok video ID from URL.
        
        Args:
            url (str): TikTok video URL
            
        Returns:
            Optional[str]: Video ID or None if extraction failed
        """
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
            
            # If no pattern matches, try to extract from the last part of the URL
            parsed = urlparse.urlparse(url)
            if 'video' in parsed.path:
                video_id = parsed.path.split('/')[-1]
                if video_id.isdigit():
                    return video_id
            
            self._log(f"⚠️ Could not extract video ID from URL: {url}", "warning")
            return None
            
        except Exception as e:
            self._log(f"❌ Error extracting video ID: {e}", "error")
            return None
    
    def download_video_api23(self, tiktok_url: str, output_path: str) -> bool:
        """
        Download video using TikTok API23 RapidAPI endpoint with key rotation.
        
        Args:
            tiktok_url (str): Original TikTok URL
            output_path (str): Output file path
            
        Returns:
            bool: True if successful, False otherwise
        """
        max_attempts = min(3, len(self.api_keys))  # Try up to 3 keys or all available keys
        
        for attempt in range(max_attempts):
            try:
                self._log(f"🚀 Trying TikTok API23 endpoint (attempt {attempt + 1}/{max_attempts})...")
                
                # Get current API key
                if attempt == 0:
                    api_key = self._get_next_api_key()
                else:
                    api_key = self._rotate_api_key()
                
                # Prepare request
                encoded_url = urlparse.quote(tiktok_url, safe='')
                api_url = f"https://{TIKTOK_API23_HOST}{TIKTOK_API23_ENDPOINT}?url={encoded_url}"
                
                headers = {
                    'x-rapidapi-host': TIKTOK_API23_HOST,
                    'x-rapidapi-key': api_key,
                    'Accept': 'application/json'
                }
                
                self._log(f"📡 Making API request to TikTok API23 (key ending ...{api_key[-4:]})...")
                
                # Make API request
                response = requests.get(api_url, headers=headers, timeout=30)
                response.raise_for_status()
                
                api_data = response.json()
                
                if not api_data.get('success', False):
                    error_msg = api_data.get('message', 'Unknown error')
                    self._log(f"❌ API23 request failed: {error_msg}", "warning")
                    if 'rate' in error_msg.lower() or 'limit' in error_msg.lower():
                        self._log(f"🔄 Rate limit detected, trying next API key...", "warning")
                        continue  # Try next key
                    return False
                
                # Extract download URL from API response
                data = api_data.get('data', {})
                download_url = None
                
                # Try different possible download URL fields
                for url_field in ['download_url', 'downloadUrl', 'play_url', 'playUrl', 'video_url', 'videoUrl']:
                    if data.get(url_field):
                        download_url = data[url_field]
                        break
                
                # Also check if data itself is the download URL
                if not download_url and isinstance(data, str) and data.startswith('http'):
                    download_url = data
                
                if not download_url:
                    self._log(f"❌ No download URL in API23 response", "warning")
                    continue  # Try next key
                
                self._log(f"✅ Got download URL from API23: {download_url[:60]}...")
                
                # Download the video file
                return self._download_from_url(download_url, output_path, "API23")
                
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    self._log(f"❌ API23 Forbidden - invalid/expired key (attempt {attempt + 1})", "warning")
                elif e.response.status_code == 429:
                    self._log(f"❌ API23 rate limited (attempt {attempt + 1})", "warning")
                else:
                    self._log(f"❌ API23 HTTP error {e.response.status_code} (attempt {attempt + 1})", "warning")
                
                # If this is not the last attempt, try next key
                if attempt < max_attempts - 1:
                    self._log(f"🔄 Trying next API key...", "warning")
                    continue
                else:
                    break
                    
            except Exception as e:
                self._log(f"❌ API23 download error (attempt {attempt + 1}): {e}", "warning")
                if attempt < max_attempts - 1:
                    continue
                else:
                    break
        
        self._log(f"❌ All API23 attempts failed with {len(self.api_keys)} available keys", "warning")
        return False
    
    def _download_from_url(self, download_url: str, output_path: str, source_name: str = "Direct") -> bool:
        """
        Helper method to download video from a URL with optimized headers.
        
        Args:
            download_url (str): Direct download URL
            output_path (str): Output file path
            source_name (str): Name of the download source for logging
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self._log(f"📥 {source_name} downloading from: {download_url[:60]}...")
            
            # Use TikTok-optimized headers
            headers = {
                'User-Agent': 'TikTok 26.2.0 rv:262018 (iPhone; iOS 14.4.2; en_US) Cronet',
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate, br',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.tiktok.com/'
            }
            
            response = requests.get(download_url, headers=headers, timeout=self.download_timeout, stream=True)
            response.raise_for_status()
            
            downloaded_bytes = 0
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded_bytes += len(chunk)
            
            # Verify download
            if Path(output_path).exists() and Path(output_path).stat().st_size > MIN_FILE_SIZE_BYTES:
                self._log(f"✅ {source_name} download successful ({downloaded_bytes:,} bytes)")
                return True
            else:
                self._log(f"❌ {source_name} download too small ({downloaded_bytes} bytes)", "warning")
                return False
                
        except Exception as e:
            self._log(f"❌ {source_name} download error: {e}", "warning")
            return False
    
    def download_video_direct(self, download_url: str, output_path: str) -> bool:
        """
        Download video directly from download URL with enhanced headers.
        
        Args:
            download_url (str): Direct download URL
            output_path (str): Output file path
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Try each header configuration
        for i, headers in enumerate(TIKTOK_HEADERS_CONFIGS, 1):
            try:
                self._log(f"🔄 Direct attempt {i}/{len(TIKTOK_HEADERS_CONFIGS)}...")
                
                session = requests.Session()
                session.headers.update(headers)
                
                response = session.get(download_url, timeout=self.download_timeout, stream=True)
                response.raise_for_status()
                
                downloaded_bytes = 0
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
                        if chunk:
                            f.write(chunk)
                            downloaded_bytes += len(chunk)
                
                # Verify download
                if Path(output_path).exists() and Path(output_path).stat().st_size > MIN_FILE_SIZE_BYTES:
                    self._log(f"✅ Direct download successful ({downloaded_bytes:,} bytes)")
                    return True
                else:
                    self._log(f"⚠️ Downloaded file too small (attempt {i})", "warning")
                    continue
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    self._log(f"⚠️ ⚠️ 403 Forbidden (attempt {i}) - trying different headers...", "warning")
                    if i < 3:  # Exponential backoff for 403 errors
                        wait_time = 2 ** i  # 2, 4, 8 seconds
                        time.sleep(wait_time)
                elif e.response.status_code == 429:  # Rate limiting
                    self._log(f"⚠️ Rate limited (attempt {i}) - backing off...", "warning")
                    if i < 3:
                        wait_time = 10 * (2 ** (i-1))  # 10, 20, 40 seconds
                        time.sleep(wait_time)
                else:
                    self._log(f"⚠️ HTTP {e.response.status_code} (attempt {i})", "warning")
                    if i < 3:
                        time.sleep(2)
                continue
            except requests.exceptions.Timeout:
                self._log(f"⚠️ Timeout on attempt {i}", "warning")
                continue
            except Exception as e:
                self._log(f"⚠️ Direct download error (attempt {i}): {e}", "warning")
                continue
        
        self._log("❌ All direct download attempts failed", "warning")
        return False
    
    def download_video_ytdlp(self, tiktok_url: str, output_path: str) -> bool:
        """
        Download video using yt-dlp with multiple execution methods.
        
        Args:
            tiktok_url (str): Original TikTok URL
            output_path (str): Output file path
            
        Returns:
            bool: True if successful, False otherwise
        """
        # Try Python module first, then command line
        if self._download_video_ytdlp_python(tiktok_url, output_path):
            return True
        elif self.has_ytdlp:
            return self._download_video_ytdlp_command(tiktok_url, output_path)
        else:
            self._log("⚠️ yt-dlp not available", "warning")
            return False
    
    def _download_video_ytdlp_python(self, tiktok_url: str, output_path: str) -> bool:
        """Try downloading using yt-dlp Python module with retry logic."""
        try:
            import yt_dlp
            self._log("🐍 Trying yt-dlp Python module...")
            
            # Enhanced options for better TikTok compatibility
            ydl_opts = {
                'format': 'best[ext=mp4][filesize<100M]/best[ext=mp4]/best',
                'outtmpl': output_path,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'referer': 'https://www.tiktok.com/',
                'noplaylist': True,
                'quiet': True,
                'no_warnings': True,
                'retries': 3,
                'fragment_retries': 3,
                'extractor_args': {
                    'tiktok': {
                        'webpage_url_basename': 'video'
                    }
                }
            }
            
            # Try multiple times with exponential backoff
            max_attempts = 2
            for attempt in range(max_attempts):
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([tiktok_url])
                    
                    if Path(output_path).exists() and Path(output_path).stat().st_size > 1000:
                        file_size = Path(output_path).stat().st_size
                        self._log(f"✅ yt-dlp Python module successful ({file_size:,} bytes)")
                        return True
                    
                except Exception as e:
                    if attempt < max_attempts - 1:
                        wait_time = (attempt + 1) * 2  # 2, 4 seconds
                        self._log(f"⏳ yt-dlp attempt {attempt + 1} failed, retrying in {wait_time}s..., error: {str(e)[:100]}")
                        time.sleep(wait_time)
                    else:
                        self._log(f"❌ yt-dlp Python module error: {e}", "warning")
                        return False
            
            self._log("❌ yt-dlp Python module failed - no output file", "warning")
            return False
                
        except ImportError:
            self._log("⚠️ yt-dlp Python module not available", "warning")
            return False
        except Exception as e:
            self._log(f"❌ yt-dlp Python module error: {e}", "warning")
            return False
    
    def _download_video_ytdlp_command(self, tiktok_url: str, output_path: str) -> bool:
        """Try downloading using yt-dlp command line."""
        try:
            self._log("⚡ Trying yt-dlp command line...")
            
            cmd = [
                'yt-dlp',
                '--format', 'best[ext=mp4][filesize<100M]/best[ext=mp4]/best',
                '--output', output_path,
                '--no-playlist',
                '--no-warnings',
                '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                '--referer', 'https://www.tiktok.com/',
                tiktok_url
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.download_timeout
            )
            
            if result.returncode == 0 and Path(output_path).exists() and Path(output_path).stat().st_size > 1000:
                file_size = Path(output_path).stat().st_size
                self._log(f"✅ yt-dlp command successful ({file_size:,} bytes)")
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self._log(f"❌ yt-dlp command failed: {error_msg}", "warning")
                return False
                
        except subprocess.TimeoutExpired:
            self._log("❌ yt-dlp command timeout", "warning")
            return False
        except Exception as e:
            self._log(f"❌ yt-dlp command error: {e}", "warning")
            return False
    
    def convert_to_audio(self, video_path: str, audio_path: str) -> bool:
        """
        Convert video file to audio using FFmpeg.
        
        Args:
            video_path (str): Input video file path
            audio_path (str): Output audio file path
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.has_ffmpeg:
            self._log("❌ FFmpeg not available for audio conversion", "error")
            return False
            
        try:
            self._log("🎵 Converting video to audio...")
            
            # FFmpeg command for high-quality audio extraction
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # Uncompressed WAV
                '-ar', '16000',  # 16kHz sample rate (good for speech recognition)
                '-ac', '1',  # Mono
                '-y',  # Overwrite output file
                audio_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=AUDIO_CONVERSION_TIMEOUT
            )
            
            if result.returncode == 0 and Path(audio_path).exists():
                audio_size = Path(audio_path).stat().st_size
                self._log(f"✅ Audio conversion successful ({audio_size:,} bytes)")
                return True
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                self._log(f"❌ Audio conversion failed: {error_msg}", "error")
                return False
                
        except subprocess.TimeoutExpired:
            self._log("❌ Audio conversion timeout", "error")
            return False
        except Exception as e:
            self._log(f"❌ Audio conversion error: {e}", "error")
            return False
    
    def download_and_convert_audio(self, video_info: Dict, index: Optional[int] = None) -> Tuple[Optional[str], Optional[float]]:
        """
        Download TikTok video and convert to audio with multiple fallback methods.
        
        Priority order:
        1. yt-dlp (primary method - most reliable for long-term use)
        2. TikTok API23 (fallback - API-based but subject to rate limits)
        3. Direct download (last resort)
        
        Args:
            video_info (Dict): Video information containing download URLs and metadata
            index (Optional[int]): Index for unique file naming
            
        Returns:
            Tuple[Optional[str], Optional[float]]: (audio_file_path, duration) or (None, None) if failed
        """
        self.total_downloads += 1
        download_start_time = time.time()
        
        try:
            # Generate unique filenames
            video_id = video_info.get('video_id', f'unknown_{int(time.time())}')
            if index is not None:
                video_id = f"{index:03d}_{video_id}"
            
            # Temporary file paths
            temp_video_path = self.temp_dir / f"{video_id}.mp4"
            temp_audio_path = self.temp_audio_path / f"{video_id}.wav"
            
            # Clean up any existing files
            for path in [temp_video_path, temp_audio_path]:
                if path.exists():
                    path.unlink()
            
            video_title = video_info.get('title', 'Unknown')[:50]
            self._log(f"🎬 Processing: {video_title}...")
            
            download_success = False
            
            # Method 1: Try yt-dlp first (primary method - most reliable)
            tiktok_url = video_info.get('url')
            if tiktok_url and self.has_ytdlp:
                self._log("� Method 1: yt-dlp download (primary method)...")
                download_success = self.download_video_ytdlp(tiktok_url, str(temp_video_path))
            
            # Method 2: Try TikTok API23 fallback
            if not download_success and tiktok_url:
                self._log("� Method 2: TikTok API23 download fallback...")
                download_success = self.download_video_api23(tiktok_url, str(temp_video_path))
            
            # Method 3: Direct download fallback (for when API and yt-dlp fail)
            if not download_success:
                download_url = video_info.get('download_url') or video_info.get('play_url')
                if download_url:
                    self._log("📥 Method 3: Direct download fallback...")
                    download_success = self.download_video_direct(download_url, str(temp_video_path))
            
            # If download failed completely
            if not download_success:
                self._log("❌ ❌ All download methods failed", "error")
                self.failed_downloads += 1
                
                # Implement graceful skip - don't crash the entire process
                self._log("⏭️ Skipping this video and continuing with the next one...", "warning")
                return None, None
            
            # Convert to audio
            if not self.convert_to_audio(str(temp_video_path), str(temp_audio_path)):
                # Clean up and fail
                self._cleanup_file(temp_video_path)
                self.failed_downloads += 1
                return None, None
            
            # Get audio duration and finalize
            duration = self._get_audio_duration(str(temp_audio_path))
            
            # Clean up video file (keep audio)
            self._cleanup_file(temp_video_path)
            
            # Success!
            self.successful_downloads += 1
            total_time = time.time() - download_start_time
            self._log(f"✅ Audio ready: {temp_audio_path.name} ({duration:.2f}s) [Total: {total_time:.1f}s]")
            
            return str(temp_audio_path), duration
            
        except Exception as e:
            self._log(f"❌ Download and conversion failed: {e}", "error")
            self.failed_downloads += 1
            return None, None
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file."""
        try:
            import soundfile as sf
            info = sf.info(audio_path)
            return info.frames / info.samplerate
        except ImportError:
            try:
                import librosa
                return librosa.get_duration(filename=audio_path)
            except Exception:
                return 0.0
        except Exception:
            return 0.0
    
    def _cleanup_file(self, file_path: Path) -> None:
        """Safely clean up a file."""
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            self._log(f"⚠️ Could not clean up {file_path}: {e}", "warning")
    
    def cleanup_audio_file(self, audio_path: str) -> None:
        """
        Clean up temporary audio file.
        
        Args:
            audio_path (str): Path to audio file to delete
        """
        try:
            if audio_path and Path(audio_path).exists():
                Path(audio_path).unlink()
                self._log(f"🧹 Cleaned up: {Path(audio_path).name}")
        except Exception as e:
            self._log(f"⚠️ Could not clean up {audio_path}: {e}", "warning")
    
    def cleanup_temp_files(self) -> None:
        """Clean up all temporary files."""
        try:
            # Clean up temp directory
            if self.temp_dir.exists():
                import shutil
                shutil.rmtree(self.temp_dir, ignore_errors=True)
                self._log("🧹 Cleaned up temporary video files")
            
            # Clean up audio files
            if self.temp_audio_path.exists():
                for audio_file in self.temp_audio_path.glob("*.wav"):
                    audio_file.unlink()
                self._log("🧹 Cleaned up temporary audio files")
                    
        except Exception as e:
            self._log(f"⚠️ Error during cleanup: {e}", "warning")
    
    def get_download_statistics(self) -> Dict[str, Any]:
        """Get download statistics."""
        success_rate = (self.successful_downloads / max(self.total_downloads, 1)) * 100
        return {
            'total_downloads': self.total_downloads,
            'successful_downloads': self.successful_downloads,
            'failed_downloads': self.failed_downloads,
            'success_rate': success_rate,
            'has_ffmpeg': self.has_ffmpeg,
            'has_ytdlp': self.has_ytdlp,
            'api_keys_available': len(self.api_keys),
            'current_key_index': self.current_key_index
        }
    
    def print_download_statistics(self) -> None:
        """Print download statistics."""
        stats = self.get_download_statistics()
        print("\n📊 TikTok Download Statistics:")
        print("=" * 40)
        print(f"Total Downloads: {stats['total_downloads']}")
        print(f"Successful: {stats['successful_downloads']}")
        print(f"Failed: {stats['failed_downloads']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"FFmpeg Available: {stats['has_ffmpeg']}")
        print(f"yt-dlp Available: {stats['has_ytdlp']}")
        print(f"API Keys Available: {stats['api_keys_available']}")
        print(f"Current Key Index: {stats['current_key_index']}")
        print("=" * 40)


# Test function
if __name__ == "__main__":
    print("🧪 Testing TikTok Video Downloader...")
    
    try:
        # Initialize downloader
        downloader = TikTokVideoDownloader()
        downloader.print_download_statistics()
        
        print(f"\n📋 System Check:")
        print(f"  FFmpeg: {'✅' if downloader.has_ffmpeg else '❌'}")
        print(f"  yt-dlp: {'✅' if downloader.has_ytdlp else '❌'}")
        
        print("\n✅ TikTok Video Downloader test completed")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()