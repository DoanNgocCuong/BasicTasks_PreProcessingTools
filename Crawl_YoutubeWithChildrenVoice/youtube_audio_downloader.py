#!/usr/bin/env python3
"""
YouTube Audio Downloader and Converter with Video Length Tracking

This module provides functionality for downloading audio from YouTube videos and converting
them to WAV format for further audio analysis. It uses yt-dlp for video downloading and
FFmpeg for audio format conversion, with enhanced capabilities for video duration tracking.

Author: Le Hoang Minh
"""

from __future__ import unicode_literals
import yt_dlp
import ffmpeg
import sys
import os
import json
import time
import random
import googleapiclient.discovery
from urllib.parse import urlparse, parse_qs


class Config:
    """Configuration class to store paths and settings."""
    
    def __init__(self):
        # Determine the parent directory of the script
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        # Store audio in youtube_audio_outputs relative to the parent directory
        self.output_dir = os.path.join(self.base_dir, 'youtube_audio_outputs')
        
        # Enhanced Audio format settings with anti-detection
        self.ydl_opts = {
            'format': 'bestaudio/best',
            # Add user agent rotation
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Add headers to mimic browser behavior
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            },
            # Rate limiting - much longer intervals to prevent detection
            'sleep_interval': 8,  # Sleep 8 seconds between downloads (increased from 2)
            'max_sleep_interval': 15,  # Increased from 5
            # Retry settings
            'retries': 3,
            'fragment_retries': 3,
            # Bypass geo-blocking
            'geo_bypass': True,
            # Extractor settings
            'extractor_retries': 3,
        }
        
        # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_output_path(self, filename):
        """Get the full path for an output file."""
        return os.path.join(self.output_dir, filename)
    
    def get_m4a_filename(self, index):
        """Get the m4a filename for a given index."""
        return f'output_{index}.m4a'
    
    def get_wav_filename(self, index):
        """Get the wav filename for a given index."""
        return f'output_{index}.wav'


class YoutubeAudioDownloader:
    """Class to handle YouTube audio downloading and conversion."""
    
    def __init__(self, config, cookies_file=None, cookies_from_browser=None):
        self.config = config
        self.last_request_time = 0
        self.request_count = 0
        self.youtube_api_key = None
        self.youtube_service = None
        
        # Cookie settings
        self.cookies_file = cookies_file
        self.cookies_from_browser = cookies_from_browser
        
        # Try to initialize YouTube Data API
        self._init_youtube_api()
        
        # Check cookie availability
        self._ensure_cookies_available()
    
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
    
    def _add_anti_detection_headers(self, ydl_opts):
        """Add additional anti-detection headers to prevent bot detection"""
        if 'http_headers' not in ydl_opts:
            ydl_opts['http_headers'] = {}
        
        # Add more browser-like headers
        ydl_opts['http_headers'].update({
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-GPC': '1',
            'Cache-Control': 'max-age=0',
            'TE': 'trailers',
        })
        
        return ydl_opts
    
    def _get_dynamic_ydl_opts(self):
        """Get yt-dlp options with dynamic user agent rotation and cookie support"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        
        opts = self.config.ydl_opts.copy()
        opts['user_agent'] = random.choice(user_agents)
        
        # Add additional anti-detection measures
        opts['sleep_interval'] = random.uniform(8, 15)  # Random sleep between 8-15 seconds
        opts['max_sleep_interval'] = 20  # Maximum sleep interval
        
        # Add anti-detection headers
        opts = self._add_anti_detection_headers(opts)
        
        # Add cookie support
        if self.cookies_file and os.path.exists(self.cookies_file):
            opts['cookiefile'] = self.cookies_file
            print(f"🍪 Using cookies from file: {self.cookies_file}")
        elif self.cookies_from_browser:
            opts['cookiesfrombrowser'] = (self.cookies_from_browser,)
            print(f"🍪 Using cookies from browser: {self.cookies_from_browser}")
        
        return opts
    
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
        """Consistently apply cookies to yt-dlp options to prevent detection"""
        # Validate cookies before applying
        if not self._validate_cookies():
            print("⚠️ Cookie validation failed - proceeding without cookies (may trigger detection)")
            return ydl_opts
        
        if self.cookies_file and os.path.exists(self.cookies_file):
            ydl_opts['cookiefile'] = self.cookies_file
        elif self.cookies_from_browser:
            ydl_opts['cookiesfrombrowser'] = (self.cookies_from_browser,)
        
        return ydl_opts
    
    def _extract_video_id(self, url):
        """Extract video ID from YouTube URL."""
        parsed_url = urlparse(url)
        if 'youtube.com' in parsed_url.netloc:
            query_params = parse_qs(parsed_url.query)
            return query_params.get('v', [None])[0]
        elif 'youtu.be' in parsed_url.netloc:
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
            'sleep_interval': random.uniform(3, 8),  # Increased sleep interval
            'retries': 5,
            'fragment_retries': 5,
        }
        
        # Apply cookies consistently
        ydl_opts = self._apply_cookies_to_opts(ydl_opts)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info is not None:
                        duration_raw = info.get('duration')
                        print(f"🔧 Retrieved metadata via yt-dlp (attempt {attempt + 1})")
                        return {
                            'duration': float(duration_raw) if duration_raw is not None else None,
                            'title': info.get('title', ''),
                            'uploader': info.get('uploader', ''),
                            'upload_date': info.get('upload_date', ''),
                            'view_count': info.get('view_count', 0),
                            'like_count': info.get('like_count', 0),
                            'description': info.get('description', '')
                        }
                    return None
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"⚠️ Error getting video info after {max_retries} attempts: {e}")
                    return None
                else:
                    wait_time = (5 ** (attempt + 1)) + random.uniform(10, 20)  # Much longer waits: 35-45s, 135-145s, 635-645s
                    print(f"⚠️ Attempt {attempt + 1} failed, retrying in {wait_time:.1f}s: {e}")
                    time.sleep(wait_time)

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
            'sleep_interval': random.uniform(3, 8),  # Increased sleep interval
        }
        
        # Apply cookies consistently
        ydl_opts = self._apply_cookies_to_opts(ydl_opts)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info is not None:
                        duration = info.get('duration')
                        return float(duration) if duration is not None else None
                    return None
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"⚠️ Error getting video duration after {max_retries} attempts: {e}")
                    return None
                else:
                    wait_time = (5 ** (attempt + 1)) + random.uniform(10, 20)  # Much longer waits: 35-45s, 135-145s, 635-645s
                    print(f"⚠️ Duration attempt {attempt + 1} failed, retrying in {wait_time:.1f}s")
                    time.sleep(wait_time)
    
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
        self._rate_limit_delay()
        
        # Get video duration first
        video_duration = self.get_video_duration(url)
        
        # Ensure output directory exists (thread-safe)
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # Clean up any existing files with the same index to prevent conflicts
        m4a_file = self.config.get_output_path(self.config.get_m4a_filename(index))
        wav_file = self.config.get_output_path(self.config.get_wav_filename(index))
        part_file = m4a_file + '.part'
        
        # Remove existing files that might cause conflicts
        for file_path in [m4a_file, wav_file, part_file]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass  # File might be in use by another process
        
        # Configure dynamic options with anti-detection
        ydl_opts = self._get_dynamic_ydl_opts()
        ydl_opts = self._apply_cookies_to_opts(ydl_opts) # Apply cookies here
        ydl_opts['outtmpl'] = m4a_file
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Add exponential backoff between retries
                if attempt > 0:
                    wait_time = (5 ** attempt) + random.uniform(10, 20)  # Much longer waits: 35-45s, 135-145s, 635-645s
                    print(f"⏳ Waiting {wait_time:.1f}s before retry attempt {attempt + 1}...")
                    time.sleep(wait_time)
                
                print(f"🔄 Download attempt {attempt + 1}/{max_retries} for URL: {url}")
                
                # Download audio
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                
                # Convert to WAV and get actual audio length
                wav_path, audio_length = self._convert_to_wav_with_duration(index)
                
                # Use actual audio length if available, otherwise fall back to video duration
                final_duration = audio_length if audio_length is not None else video_duration
                
                print(f"✅ Successfully downloaded and converted audio")
                return wav_path, final_duration
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check for specific YouTube blocking errors
                if any(keyword in error_msg for keyword in ['sign in', 'bot', 'automated', 'captcha', 'blocked']):
                    print(f"🚫 Bot detection triggered: {e}")
                    if attempt == max_retries - 1:
                        print("❌ All attempts exhausted due to bot detection")
                        return None, None
                    else:
                        # Longer wait for bot detection
                        wait_time = 60 + random.uniform(30, 60)  # 90-120 seconds
                        print(f"⏳ Bot detected, waiting {wait_time:.1f}s before retry...")
                        time.sleep(wait_time)
                        # Reset request counter to get fresh delays
                        self._reset_request_counter()
                else:
                    print(f"⚠️ Download error (attempt {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        print("❌ All download attempts failed")
                        return None, None
                
                # Clean up any partial files on error
                for file_path in [m4a_file, wav_file, part_file]:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except OSError:
                            pass
        
        return None, None
    
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
        if not self.youtube_service:
            print("⚠️ YouTube API not available, falling back to yt-dlp")
            return self.download_audio_from_yturl(url, index)
        
        try:
            # Extract video ID
            video_id = self._extract_video_id(url)
            if not video_id:
                print("⚠️ Could not extract video ID, falling back to yt-dlp")
                return self.download_audio_from_yturl(url, index)
            
            # Get video info via API
            video_info = self.get_video_info_via_api(video_id)
            if not video_info:
                print("⚠️ Could not get video info via API, falling back to yt-dlp")
                return self.download_audio_from_yturl(url, index)
            
            # Use yt-dlp with API-provided metadata to reduce scraping
            return self._download_with_api_metadata(url, video_info, index)
            
        except Exception as e:
            print(f"⚠️ API download failed: {e}, falling back to yt-dlp")
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
        
        for file_path in [m4a_file, wav_file, part_file]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
        
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
                error_msg = str(e).lower()
                
                if any(keyword in error_msg for keyword in ['sign in', 'bot', 'automated', 'captcha', 'blocked']):
                    print(f"🚫 Bot detection still triggered, trying alternative method...")
                    # Try with different yt-dlp options
                    return self._try_alternative_download_method(url, index, attempt)
                else:
                    print(f"⚠️ Download error (attempt {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        print("❌ All download attempts failed")
                        return None, None
                
                # Clean up partial files
                for file_path in [m4a_file, wav_file, part_file]:
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except OSError:
                            pass
        
        return None, None
    
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
            print(f"⚠️ Alternative method failed: {e}")
            return None, None
    
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
            
            # Convert using ffmpeg
            stream = ffmpeg.input(input_file)
            stream = ffmpeg.output(stream, output_file)
            ffmpeg.run(stream, quiet=True, overwrite_output=True)
            
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
            
            return output_file, audio_duration
                
        except Exception as e:
            print(f"⚠️ Error converting to WAV: {e}")
            # Clean up both intermediate and output files on error
            for file_path in [input_file, output_file]:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
            return None, None
    
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
        supported_browsers = ['chrome', 'firefox', 'safari', 'edge', 'opera', 'brave']
        if browser_name.lower() in supported_browsers:
            self.cookies_from_browser = browser_name.lower()
            self.cookies_file = None
            print(f"🍪 Cookies set from browser: {browser_name}")
        else:
            print(f"⚠️ Unsupported browser: {browser_name}. Supported: {', '.join(supported_browsers)}")
    
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

def main():
    """Main function to handle command line interface."""
    config = Config()
    
    args = sys.argv[1:]
    
    # Parse cookie-related arguments
    cookies_file = None
    cookies_browser = None
    
    # Check for cookie arguments
    if '--cookies-file' in args:
        try:
            cookie_index = args.index('--cookies-file')
            if cookie_index + 1 < len(args):
                cookies_file = args[cookie_index + 1]
                # Remove the argument and its value
                args.pop(cookie_index)  # Remove --cookies-file
                args.pop(cookie_index)  # Remove the file path
        except (ValueError, IndexError):
            print("⚠️ Error: --cookies-file requires a file path")
            exit(1)
    
    if '--cookies-browser' in args:
        try:
            browser_index = args.index('--cookies-browser')
            if browser_index + 1 < len(args):
                cookies_browser = args[browser_index + 1]
                # Remove the argument and its value
                args.pop(browser_index)  # Remove --cookies-browser
                args.pop(browser_index)  # Remove the browser name
        except (ValueError, IndexError):
            print("⚠️ Error: --cookies-browser requires a browser name")
            exit(1)
    
    # Initialize downloader with cookie settings
    downloader = YoutubeAudioDownloader(config, cookies_file, cookies_browser)
    
    if len(args) > 2:
        print("Too many arguments.")
        print("Usage: python youtube_audio_downloader.py [options] <optional link> [--test-duration]")
        print("Options:")
        print("  --cookies-file <path>     Use cookies from Netscape format file")
        print("  --cookies-browser <name>  Use cookies from browser (chrome, firefox, safari, edge, opera, brave)")
        print("  --test-duration          Test video duration extraction without downloading")
        print("")
        print("Examples:")
        print("  python youtube_audio_downloader.py --cookies-file cookies.txt https://youtube.com/watch?v=...")
        print("  python youtube_audio_downloader.py --cookies-browser chrome https://youtube.com/watch?v=...")
        print("  python youtube_audio_downloader.py --cookies-browser firefox --test-duration https://youtube.com/watch?v=...")
        exit()
    
    # Check for test duration flag
    test_duration = False
    if "--test-duration" in args:
        test_duration = True
        args.remove("--test-duration")
    
    # Show cookie status
    cookie_status = downloader.get_cookie_status()
    if cookie_status['cookies_file'] or cookie_status['cookies_from_browser']:
        print(f"🍪 Cookie configuration: {cookie_status}")
    
    if len(args) == 0:
        url = input("Enter Youtube URL: ")
        if test_duration:
            downloader.test_video_duration_extraction(url)
        else:
            result = downloader.download_audio_from_yturl(url)
            if isinstance(result, tuple):
                wav_path, duration = result
                print(f"✅ Audio downloaded to: {wav_path}")
                if duration:
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    print(f"📏 Video duration: {minutes}:{seconds:02d}")
            else:
                # Handle backward compatibility
                print(f"✅ Audio downloaded to: {result}")
    else:
        url = args[0]
        if test_duration:
            downloader.test_video_duration_extraction(url)
        else:
            result = downloader.download_audio_from_yturl(url)
            if isinstance(result, tuple):
                wav_path, duration = result
                print(f"✅ Audio downloaded to: {wav_path}")
                if duration:
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    print(f"📏 Video duration: {minutes}:{seconds:02d}")
            else:
                # Handle backward compatibility
                print(f"✅ Audio downloaded to: {result}")

if __name__ == "__main__":
    main()

