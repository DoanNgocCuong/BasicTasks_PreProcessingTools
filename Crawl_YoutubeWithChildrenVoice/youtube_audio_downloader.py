#!/usr/bin/env python3
"""
YouTube Audio Downloader - Cleaned and Debuggable Version

Simplified version with enhanced debugging and cleaner code structure.
Preserves all original functionality while improving readability.

Author: Le Hoang Minh
"""

import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Union
from urllib.parse import urlparse, parse_qs

import ffmpeg
import googleapiclient.discovery
import yt_dlp

# Import language classifier
from youtube_language_classifier import YouTubeLanguageClassifier

# PyTube imports with fallback
try:
    from pytubefix import YouTube  # type: ignore
    print("[SUCCESS] Using pytubefix (maintained fork)")
except ImportError:
    try:
        from pytube import YouTube  # type: ignore
        print("[INFO] Falling back to pytube")
    except ImportError:
        print("[ERROR] Neither pytubefix nor pytube available")
        sys.exit(1)

# =================================================================
# CONSTANTS
# =================================================================

DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0'
DEFAULT_SLEEP_INTERVAL = 8
DEFAULT_MAX_SLEEP_INTERVAL = 15
DEFAULT_RETRIES = 3
YTDLP_DOWNLOAD_WAIT_SECONDS = 180

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
]

UNAVAILABLE_VIDEO_PATTERNS = [
    'video unavailable', 'removed by the uploader', 'private video', 'copyright'
]

BOT_DETECTION_PATTERNS = [
    'sign in', 'bot', 'automated', 'captcha', 'blocked'
]

# =================================================================
# UTILITY FUNCTIONS
# =================================================================

def debug_print(message: str, level: str = "DEBUG"):
    """Centralized debug printing with consistent formatting."""
    emoji_map = {
        "DEBUG": "🔧",
        "SUCCESS": "✅", 
        "ERROR": "❌",
        "WARNING": "⚠️",
        "INFO": "📋",
        "PROCESS": "🎯"
    }
    emoji = emoji_map.get(level, "📝")
    print(f"{emoji} [DEBUG] {message}")

def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    try:
        parsed = urlparse(url)
        if 'youtube.com' in parsed.netloc:
            return parse_qs(parsed.query).get('v', [None])[0]
        elif 'youtu.be' in parsed.netloc:
            return parsed.path[1:]
    except Exception:
        pass
    return None

def get_video_title(url: str) -> Optional[str]:
    """Get video title using available methods."""
    try:
        return YouTube(url).title
    except Exception:
        return None

def to_camel_case(text: str, max_len: int = 40) -> str:
    """Convert text to camelCase."""
    try:
        words = re.split(r'[^a-z0-9]+', (text or '').lower())
        words = [w for w in words if w]
        camel = ''.join(w.capitalize() for w in words)
        return camel[:max_len] if camel else 'NoTitle'
    except Exception:
        return 'NoTitle'

def build_filename(index: int, url: str, extension: str = "wav") -> str:
    """Build consistent filename with video info."""
    try:
        vid = extract_video_id(url)
        title = get_video_title(url)
        camel_title = to_camel_case(title) if title else 'NoTitle'
        short_id = (vid or 'noid')[:8]
        return f"{index:04d}_{short_id}_{camel_title}.{extension}"
    except Exception:
        return f"{index:04d}_unknown.{extension}"

def convert_to_wav(input_path: str, output_path: str) -> bool:
    """Convert audio file to WAV format using ffmpeg."""
    try:
        stream = ffmpeg.input(input_path)
        stream = ffmpeg.output(
            stream, 
            output_path,
            acodec='pcm_s16le',  # WAV PCM format
            ar=16000,  # 16kHz sample rate
            ac=1  # Mono
        )
        ffmpeg.run(stream, quiet=True, overwrite_output=True)
        return Path(output_path).exists()
    except Exception as e:
        debug_print(f"FFmpeg conversion failed: {e}", "ERROR")
        return False

def is_error_pattern(error_message: str, patterns: List[str]) -> bool:
    """Check if error message contains any of the specified patterns."""
    error_msg_lower = error_message.lower()
    return any(pattern in error_msg_lower for pattern in patterns)

def cleanup_file(file_path: Optional[Path], description: str = "temp file") -> None:
    """Safely clean up a file."""
    try:
        if file_path and file_path.exists():
            file_path.unlink()
            debug_print(f"Cleaned up {description}")
    except Exception as e:
        debug_print(f"Could not clean up {description}: {e}", "WARNING")

# =================================================================
# CONFIGURATION CLASS
# =================================================================

class Config:
    """Enhanced configuration class with dual manifest support."""
    
    def __init__(self, user_agent=None, output_dir=None, manifest_path=None, original_manifest_path=None, enable_duplicate_check=True):
        debug_print("Initializing Config...")
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = output_dir or os.path.join(self.base_dir, 'youtube_audio_outputs')
        self.manifest_path = manifest_path
        self.original_manifest_path = original_manifest_path
        self.enable_duplicate_check = enable_duplicate_check
        
        # Initialize language classifier
        self.language_classifier = YouTubeLanguageClassifier()
        
        # Cache for language detection results
        self._language_cache = {}
        
        # Load user agent settings
        default_user_agent = user_agent or self._load_user_agent() or DEFAULT_USER_AGENT
        
        # Basic yt-dlp options
        self.ydl_opts = {
            'format': 'bestaudio/best',
            'user_agent': default_user_agent,
            'sleep_interval': DEFAULT_SLEEP_INTERVAL,
            'max_sleep_interval': DEFAULT_MAX_SLEEP_INTERVAL,
            'retries': DEFAULT_RETRIES,
            'fragment_retries': DEFAULT_RETRIES,
            'geo_bypass': True,
            'extractor_retries': DEFAULT_RETRIES,
        }
        
        os.makedirs(self.output_dir, exist_ok=True)
        debug_print(f"Config initialized: {self.output_dir}", "SUCCESS")
    
    def _load_user_agent(self):
        """Load user agent from crawler config."""
        try:
            config_file = os.path.join(self.base_dir, 'crawler_config.json')
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    return config_data.get('user_agent_settings', {}).get('default_user_agent')
        except Exception as e:
            debug_print(f"Error loading user agent: {e}", "WARNING")
        return None
    
    def get_output_path(self, filename):
        """Get full path for output file."""
        return os.path.join(self.output_dir, filename)
    
    def get_language_output_dir(self, url):
        """Get language-specific output directory using transcript-based detection."""
        # Check cache first
        if url in self._language_cache:
            language_folder = self._language_cache[url]
            debug_print(f"Using cached language for {url}: {language_folder}")
        else:
            try:
                # Use language classifier to detect language
                detection_result = self.language_classifier.detect_language_from_url(url)
                
                if detection_result['error']:
                    debug_print(f"Language detection failed for {url}: {detection_result['error']}", "WARNING")
                    language_folder = 'unknown'
                else:
                    detected_lang = detection_result['detected_language']
                    # Map common language codes to folder names
                    language_mapping = {
                        'vi': 'vietnamese',
                        'en': 'english', 
                        'zh': 'chinese',
                        'es': 'spanish',
                        'fr': 'french',
                        'de': 'german',
                        'ja': 'japanese',
                        'ko': 'korean'
                    }
                    language_folder = language_mapping.get(detected_lang, detected_lang or 'unknown')
                    debug_print(f"Detected language for {url}: {detected_lang} -> {language_folder}")
                    
            except Exception as e:
                debug_print(f"Language detection error for {url}: {e}", "ERROR")
                language_folder = 'unknown'
            
            # Cache the result
            self._language_cache[url] = language_folder
            
        language_dir = os.path.join(self.output_dir, language_folder)
        os.makedirs(language_dir, exist_ok=True)
        return language_dir
    
    def get_m4a_filename(self, index):
        """Get M4A filename."""
        custom_base = getattr(self, '_current_basename', None)
        return f'{custom_base}.m4a' if custom_base else f'output_{index}.m4a'
    
    def get_wav_filename(self, index):
        """Get WAV filename."""
        custom_base = getattr(self, '_current_basename', None)
        return f'{custom_base}.wav' if custom_base else f'output_{index}.wav'

# =================================================================
# MAIN DOWNLOADER CLASS
# =================================================================

class YoutubeAudioDownloader:
    """Simplified YouTube Audio Downloader."""
    
    def __init__(self, config, cookies_file=None, cookies_from_browser=None):
        debug_print("Initializing YoutubeAudioDownloader...")
        
        self.config = config
        self.last_request_time = 0
        self.request_count = 0
        self.disable_rate_limit = False
        self._current_basename: Optional[str] = None
        
        self.cookies_file = cookies_file
        self.cookies_from_browser = cookies_from_browser
        
        self.youtube_api_key = None
        self.youtube_service = None
        
        # Initialize unified manifest index for duplicate detection
        self.unified_index = {}
        
        self._init_youtube_api()
        self._ensure_cookies_available()
        self._load_unified_manifest_index()
        
        debug_print("YoutubeAudioDownloader initialized", "SUCCESS")
    
    def _init_youtube_api(self):
        """Initialize YouTube API if available."""
        debug_print("Initializing YouTube API...")
        
        self.youtube_api_key = self._get_youtube_api_key()
        
        if self.youtube_api_key and self.youtube_api_key.strip():
            try:
                self.youtube_service = googleapiclient.discovery.build(
                    "youtube", "v3", developerKey=self.youtube_api_key
                )
                debug_print("YouTube API initialized", "SUCCESS")
            except Exception as e:
                debug_print(f"YouTube API failed: {e}", "WARNING")
                self.youtube_service = None
        else:
            debug_print("No YouTube API key found", "WARNING")
            self.youtube_service = None
    
    def _get_youtube_api_key(self):
        """Get YouTube API key from various sources."""
        # Try env_config first
        try:
            from env_config import config as env_config
            api_keys = env_config.YOUTUBE_API_KEYS
            if api_keys:
                debug_print(f"Found {len(api_keys)} API keys in env_config")
                return api_keys[0]
        except Exception:
            pass
        
        # Try environment variables
        api_key = (
            os.getenv('YOUTUBE_API_KEY') or 
            os.getenv('YOUTUBE_API_KEY_1') or 
            (os.getenv('YOUTUBE_API_KEYS', '').split(',')[0].strip() if os.getenv('YOUTUBE_API_KEYS') else None)
        )
        
        if api_key:
            debug_print("Found API key in environment")
        
        return api_key
    
    def _ensure_cookies_available(self):
        """Check cookie availability."""
        if self.cookies_file and os.path.exists(self.cookies_file):
            debug_print(f"Using cookies file: {self.cookies_file}")
        elif self.cookies_from_browser:
            debug_print(f"Using browser cookies: {self.cookies_from_browser}")
        else:
            debug_print("No cookies configured", "WARNING")
    
    def _extract_video_id(self, url):
        """Extract video ID from YouTube URL."""
        return extract_video_id(url)
    
    def _load_unified_manifest_index(self):
        """Load unified index from both manifests for duplicate detection."""
        debug_print("Loading unified manifest index for duplicate detection...")
        
        self.unified_index = {}
        
        # Load primary manifest (where we write) if specified
        if hasattr(self.config, 'manifest_path') and self.config.manifest_path:
            try:
                if os.path.exists(self.config.manifest_path):
                    debug_print(f"Loading primary manifest: {self.config.manifest_path}")
                    primary_data = self._load_manifest(self.config.manifest_path)
                    for record in primary_data.get('records', []):
                        video_id = record.get('video_id')
                        url = record.get('url')
                        if video_id:
                            self.unified_index[video_id] = {'source': 'primary', 'record': record}
                        if url:
                            self.unified_index[f"url_{url}"] = {'source': 'primary', 'record': record}
            except Exception as e:
                debug_print(f"Error loading primary manifest: {e}", "WARNING")
        
        # Load original manifest (read-only for duplicate checking) if specified
        if hasattr(self.config, 'original_manifest_path') and self.config.original_manifest_path:
            try:
                if os.path.exists(self.config.original_manifest_path):
                    debug_print(f"Loading original manifest for duplicate check: {self.config.original_manifest_path}")
                    original_data = self._load_manifest(self.config.original_manifest_path)
                    for record in original_data.get('records', []):
                        video_id = record.get('video_id')
                        url = record.get('url')
                        # Only add if not already present (primary manifest takes precedence)
                        if video_id and video_id not in self.unified_index:
                            self.unified_index[video_id] = {'source': 'original', 'record': record}
                        if url and f"url_{url}" not in self.unified_index:
                            self.unified_index[f"url_{url}"] = {'source': 'original', 'record': record}
            except Exception as e:
                debug_print(f"Error loading original manifest: {e}", "WARNING")
        
        total_records = len([k for k in self.unified_index.keys() if not k.startswith('url_')])
        debug_print(f"Unified index loaded: {total_records} records for duplicate detection")
    
    def _load_manifest(self, manifest_path):
        """Load manifest data from file."""
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {'total_duration_seconds': 0.0, 'records': []}
    
    def _is_duplicate(self, video_id, url):
        """Enhanced duplicate checking across both manifests."""
        if not hasattr(self.config, 'enable_duplicate_check') or not self.config.enable_duplicate_check:
            return False
        
        if video_id and video_id in self.unified_index:
            source = self.unified_index[video_id]['source']
            debug_print(f"Duplicate found by video_id {video_id} in {source} manifest", "WARNING")
            return True
        if url and f"url_{url}" in self.unified_index:
            source = self.unified_index[f"url_{url}"]['source']
            debug_print(f"Duplicate found by URL in {source} manifest", "WARNING")
            return True
        return False
    
    def _is_video_unavailable(self, error_message):
        """Check if error indicates unavailable video."""
        return is_error_pattern(error_message, UNAVAILABLE_VIDEO_PATTERNS)
    
    def _is_bot_detection_error(self, error_message):
        """Check if error indicates bot detection."""
        return is_error_pattern(error_message, BOT_DETECTION_PATTERNS)
    
    def _organize_language_folder(self, wav_path, url):
        """Handle language-based file organization using transcript detection."""
        try:
            # Check if file is already in a language-specific directory
            current_dir = os.path.dirname(wav_path)
            if any(lang in current_dir for lang in ['vietnamese', 'english', 'chinese', 'spanish', 'french', 'german', 'japanese', 'korean', 'unknown']):
                debug_print(f"File already in language folder: {os.path.basename(current_dir)}")
                return wav_path
                
            # Get language-specific output directory
            language_dir = self.config.get_language_output_dir(url)
            target_filename = os.path.basename(wav_path)
            target_path = os.path.join(language_dir, target_filename)
            
            # Check if file needs to be moved
            current_dir = os.path.normpath(os.path.dirname(wav_path))
            target_dir = os.path.normpath(language_dir)
            
            if current_dir != target_dir:
                try:
                    # Extract language folder name from path
                    language_folder = os.path.basename(language_dir)
                    debug_print(f"Moving to language folder ({language_folder}): {current_dir} → {target_dir}")
                    os.makedirs(language_dir, exist_ok=True)
                    shutil.move(wav_path, target_path)
                    debug_print(f"File moved successfully: {target_path}", "SUCCESS")
                    return target_path
                except Exception as move_error:
                    debug_print(f"Could not move file: {move_error}", "WARNING")
                    return wav_path
            else:
                language_folder = os.path.basename(language_dir)
                debug_print(f"File already in correct language folder: {language_folder}")
                return wav_path
                
        except Exception as e:
            debug_print(f"Error in language organization: {e}", "ERROR")
            return wav_path
    
    def get_audio_length_from_file(self, audio_file_path):
        """Get audio length using ffprobe."""
        try:
            probe = ffmpeg.probe(audio_file_path)
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e:
            debug_print(f"Error getting audio length: {e}", "WARNING")
            return None
    
    # =================================================================
    # METADATA METHODS
    # =================================================================
    
    def get_video_info_via_api(self, video_id):
        """Get video info via YouTube Data API."""
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
                
                duration_seconds = self._parse_iso_duration(content_details['duration'])
                
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
            print(f"⚠️ [DEBUG] YouTube API error: {e}")
        
        return None
    
    def _parse_iso_duration(self, duration_iso):
        """Parse ISO 8601 duration to seconds."""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return hours * 3600 + minutes * 60 + seconds
        return None
    
    def get_video_info_with_duration(self, url):
        """Get video info prioritizing API over yt-dlp."""
        # Try API first
        video_id = self._extract_video_id(url)
        if video_id and self.youtube_service:
            api_info = self.get_video_info_via_api(video_id)
            if api_info:
                print(f"📡 [DEBUG] Retrieved metadata via API")
                return api_info
        
        # Fallback to yt-dlp
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'user_agent': self.config.ydl_opts['user_agent'],
            'retries': 1,
            'fragment_retries': 1,
            'extractor_args': {'youtube': {'player_client': ['android']}},
            'noplaylist': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if info:
                print(f"🔧 [DEBUG] Retrieved metadata via yt-dlp")
                duration_value = info.get('duration', 0)
                try:
                    duration = float(duration_value) if duration_value is not None else 0.0
                except (ValueError, TypeError):
                    duration = 0.0
                
                return {
                    'duration': duration,
                    'title': info.get('title', ''),
                    'uploader': info.get('uploader', ''),
                    'upload_date': info.get('upload_date', ''),
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'description': info.get('description', '')
                }
        except Exception as e:
            if self._is_video_unavailable(str(e)):
                print(f"⏭️ [DEBUG] Video unavailable: {e}")
                return None
            print(f"⚠️ [DEBUG] Metadata error: {e}")
        return None
    
    def _generate_output_filename(self, index: int, prefix: str = "yt") -> Path:
        """Generate output filename for downloads."""
        output_dir = Path(self.config.output_dir)
        if hasattr(self, '_current_basename') and self._current_basename:
            return output_dir / f"{self._current_basename}.wav"
        timestamp = int(time.time() * 1000)
        return output_dir / f"{prefix}_{index}_{timestamp}.wav"
    
    def download_audio_pytube(self, url: str, index: int = 0) -> Optional[Tuple[str, float]]:
        """Download and convert audio using pytube."""
        debug_print("=" * 50)
        debug_print("PYTUBE METHOD ACTIVATED")
        debug_print("=" * 50)
        debug_print(f"Starting pytube download for video {index}")
        
        wav_file = self._generate_output_filename(index, "yt")
        temp_audio_file = None
        
        try:
            # Download using pytube
            debug_print("Creating YouTube object...")
            yt = YouTube(url)
            
            debug_print(f"Video: {yt.title[:50]}...")
            debug_print(f"Duration: {yt.length//60}m {yt.length%60}s")
            
            # Get best audio stream
            debug_print("Getting audio streams...")
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            
            if not audio_stream:
                debug_print("No audio streams available", "ERROR")
                debug_print(f"DOWNLOAD FAILED: No audio streams for {yt.title[:50]}...", "ERROR")
                return None
            
            debug_print(f"Selected: {audio_stream.mime_type} - {audio_stream.abr}")
            
            # Download audio
            debug_print("Downloading audio...")
            temp_filename = f"tmp_{index}.{audio_stream.subtype}"
            temp_audio_file = wav_file.parent / temp_filename
            
            audio_stream.download(output_path=str(wav_file.parent), filename=temp_filename)
            
            if not temp_audio_file.exists():
                debug_print("Download failed - file not created", "ERROR")
                debug_print(f"DOWNLOAD FAILED: File not created for {yt.title[:50]}...", "ERROR")
                return None
            
            debug_print(f"Downloaded: {temp_audio_file.stat().st_size} bytes", "SUCCESS")
            debug_print(f"Video successfully downloaded: {yt.title[:50]}...", "SUCCESS")
            
            # Convert to WAV
            debug_print("Converting to WAV format...")
            if convert_to_wav(str(temp_audio_file), str(wav_file)):
                audio_duration = float(yt.length)
                debug_print(f"Final audio duration: {audio_duration//60:.0f}m {audio_duration%60:.0f}s")
                debug_print("=" * 50, "SUCCESS")
                debug_print("PYTUBE METHOD SUCCESSFUL!", "SUCCESS")
                debug_print("=" * 50, "SUCCESS")
                debug_print(f"WAV file created: {wav_file}", "SUCCESS")
                return str(wav_file), audio_duration
            else:
                debug_print("WAV conversion failed", "ERROR")
                debug_print(f"CONVERSION FAILED: WAV file not created for {yt.title[:50]}...", "ERROR")
                return None
                
        except Exception as e:
            debug_print(f"Pytube download error: {e}", "ERROR")
            debug_print(f"PYTUBE FAILED: General download error for URL: {url[:50]}...", "ERROR")
            return None
        finally:
            cleanup_file(temp_audio_file, "temporary audio file")
    
    def download_audio_yt_dlp_fallback(self, url: str, index: int = 0) -> Optional[Tuple[str, float]]:
        """Fallback method using yt-dlp with Android client."""
        debug_print("=" * 50)
        debug_print("YT-DLP ANDROID CLIENT METHOD ACTIVATED")
        debug_print("Using reliable Android client to bypass restrictions")
        debug_print("=" * 50)
        debug_print(f"Starting yt-dlp Android client download for video {index}")
        
        wav_file = self._generate_output_filename(index, "ytdlp")
        temp_audio_name = f"{wav_file.stem}_temp"
        
        try:
            debug_print("Downloading with yt-dlp...")
            
            # Build yt-dlp command
            cmd = [
                "yt-dlp",
                "-f", "bestaudio[ext=m4a]/bestaudio/best",
                "--extract-audio", "--audio-format", "wav", "--audio-quality", "5",
                "--extractor-args", "youtube:player_client=android",
                "--no-playlist", "--no-check-certificate",
                "--output", str(wav_file.parent / f"{temp_audio_name}.%(ext)s"),
                url
            ]
            
            debug_print("Using Android client - cookies disabled (Android client doesn't support cookies)")
            debug_print("Android client bypasses restrictions without needing cookies")
            
            # Add random user agent and retry limits
            cmd.extend(["--user-agent", random.choice(USER_AGENTS)])
            cmd.extend(["--progress", "--retries", "1", "--fragment-retries", "1"])
            
            debug_print("Running yt-dlp with Android client...")
            
            # Execute with timeout handling
            result = self._execute_yt_dlp_process(cmd, temp_audio_name)
            if not result:
                return None
                
            # Find downloaded file
            temp_wav_file = self._find_downloaded_file(temp_audio_name, wav_file.parent)
            if not temp_wav_file:
                debug_print("yt-dlp download failed - no output file found", "ERROR")
                self._cleanup_temp_files(temp_audio_name, wav_file.parent)
                return None
            
            debug_print(f"yt-dlp download successful: {temp_wav_file}", "SUCCESS")
            
            # Convert to final WAV format if needed
            if not self._finalize_wav_file(temp_wav_file, wav_file):
                return None
            
            # Get duration and return
            duration = self._get_audio_duration(wav_file)
            
            debug_print("=" * 50, "SUCCESS")
            debug_print("YT-DLP ANDROID CLIENT METHOD SUCCESSFUL!", "SUCCESS")
            debug_print("Downloaded using Android client bypass", "SUCCESS")
            debug_print("=" * 50, "SUCCESS")
            debug_print(f"Successfully downloaded via yt-dlp Android client: {wav_file}", "SUCCESS")
            
            if duration:
                minutes, seconds = int(duration // 60), int(duration % 60)
                debug_print(f"Audio duration: {minutes}:{seconds:02d}")
            
            return str(wav_file), duration or 0.0
            
        except Exception as e:
            debug_print(f"yt-dlp fallback error: {e}", "ERROR")
            self._cleanup_temp_files(temp_audio_name, wav_file.parent)
            return None
    
    def _execute_yt_dlp_process(self, cmd: List[str], temp_audio_name: str) -> bool:
        """Execute yt-dlp process with timeout handling."""
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                stdin=subprocess.PIPE, text=True
            )
            
            if process.stdin:
                process.stdin.close()
            
            debug_print(f"Waiting for yt-dlp download (timeout: {YTDLP_DOWNLOAD_WAIT_SECONDS} seconds)...")
            
            try:
                stdout, stderr = process.communicate(timeout=YTDLP_DOWNLOAD_WAIT_SECONDS)
            except subprocess.TimeoutExpired:
                debug_print("Download taking longer than expected, forcing termination...", "WARNING")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    debug_print("Force killing stuck process...")
                    process.kill()
                    process.wait()
                raise
            
            if process.returncode != 0:
                debug_print(f"yt-dlp failed: {stderr.strip()}", "ERROR")
                return False
                
            return True
            
        except subprocess.TimeoutExpired:
            debug_print("yt-dlp process forced termination due to timeout", "ERROR")
            return False
    
    def _find_downloaded_file(self, temp_audio_name: str, output_dir: Path) -> Optional[Path]:
        """Find the downloaded file from yt-dlp."""
        for file in output_dir.glob(f"{temp_audio_name}.*"):
            if file.suffix.lower() in ['.wav', '.m4a', '.mp3', '.webm']:
                return file
        return None
    
    def _finalize_wav_file(self, temp_wav_file: Path, wav_file: Path) -> bool:
        """Convert downloaded file to final WAV format."""
        if temp_wav_file.suffix.lower() != '.wav':
            debug_print("Converting to WAV format...")
            if convert_to_wav(str(temp_wav_file), str(wav_file)):
                cleanup_file(temp_wav_file, "temporary file")
                return True
            return False
        else:
            temp_wav_file.rename(wav_file)
            return wav_file.exists()
    
    def _get_audio_duration(self, wav_file: Path) -> Optional[float]:
        """Get audio duration using ffprobe."""
        try:
            probe = ffmpeg.probe(str(wav_file))
            return float(probe['streams'][0]['duration'])
        except Exception:
            return None
    
    def _cleanup_temp_files(self, temp_audio_name: Optional[str] = None, output_dir: Optional[Path] = None) -> None:
        """Clean up temporary and partial files."""
        try:
            if not output_dir:
                output_dir = Path(self.config.output_dir)
            
            if temp_audio_name:
                pattern_files = list(output_dir.glob(f"{temp_audio_name}.*"))
                for temp_file in pattern_files:
                    cleanup_file(temp_file, f"temp file: {temp_file.name}")
            
            # Clean up orphaned .part files
            part_files = list(output_dir.glob("*.part"))
            if part_files:
                debug_print(f"Found {len(part_files)} orphaned .part files to clean up")
                current_time = time.time()
                
                for part_file in part_files:
                    file_age = current_time - part_file.stat().st_mtime
                    if file_age > 300:  # 5 minutes
                        cleanup_file(part_file, f"orphaned file: {part_file.name}")
                    else:
                        debug_print(f"Skipping recent file: {part_file.name}")
        except Exception as e:
            debug_print(f"Error during temp file cleanup: {e}", "WARNING")
    
    def cleanup_all_temp_files(self) -> None:
        """Public method to clean up all temporary files."""
        debug_print("Starting comprehensive temp file cleanup...")
        self._cleanup_temp_files()
        debug_print("Temp file cleanup completed", "SUCCESS")

    def download_audio_from_yturl(self, url, index=0):
        """Download audio using both yt-dlp and PyTube fallback."""
        debug_print(f"Starting download for video {index}: {url[:80]}...")
        
        try:
            # Set custom basename
            custom_base = getattr(self.config, '_current_basename', None)
            if custom_base:
                debug_print(f"Setting custom basename: {custom_base}")
                self._current_basename = custom_base
            
            # Try yt-dlp Android client first
            debug_print("Attempting yt-dlp Android client download...", "INFO")
            result = self.download_audio_yt_dlp_fallback(url, index)
            
            # If yt-dlp fails, try PyTube fallback
            if not result or not result[0]:
                debug_print("yt-dlp failed, trying PyTube fallback...", "WARNING")
                result = self.download_audio_pytube(url, index)
            
            # Clean up
            if hasattr(self, '_current_basename'):
                self._current_basename = None
            
            if result and result[0]:
                wav_path, duration = result
                debug_print(f"Download successful: {wav_path}", "SUCCESS")
                
                # Handle language organization
                wav_path = self._organize_language_folder(wav_path, url)
                return wav_path, duration
            else:
                debug_print("All download methods failed", "ERROR")
                return None, None
                
        except Exception as e:
            debug_print(f"Download error: {e}", "ERROR")
            return None, None

# =================================================================
# HELPER FUNCTIONS
# =================================================================

def _setup_environment():
    """Setup directories and downloader."""
    debug_print("Setting up environment...")
    
    config = Config()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    final_output_dir = os.path.join(base_dir, 'final_audio_files')
    
    # Create directories
    os.makedirs(final_output_dir, exist_ok=True)
    for lang_folder in ['vietnamese', 'unknown']:
        os.makedirs(os.path.join(final_output_dir, lang_folder), exist_ok=True)
    
    config.output_dir = final_output_dir
    
    # Initialize downloader
    downloader = YoutubeAudioDownloader(config)
    # Set batch processing flags
    downloader.disable_rate_limit = True
    
    debug_print("Environment setup complete", "SUCCESS")
    return config, downloader, final_output_dir

def _load_manifest(manifest_path):
    """Load and validate manifest file."""
    try:
        if os.path.exists(manifest_path):
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    records = data
                    total = sum(float(r.get('duration_seconds', 0) or 0) for r in records)
                    data = {'total_duration_seconds': total, 'records': records}
                elif isinstance(data, dict):
                    records = data.get('records', [])
                    if 'total_duration_seconds' not in data:
                        data['total_duration_seconds'] = sum(float(r.get('duration_seconds', 0) or 0) for r in records)
        else:
            data = {'total_duration_seconds': 0.0, 'records': []}
    except Exception as e:
        debug_print(f"Error loading manifest: {e}", "WARNING")
        data = {'total_duration_seconds': 0.0, 'records': []}
    
    # Create index
    index = {r.get('video_id'): r for r in data.get('records', []) if r.get('video_id')}
    return data, index

def _save_manifest(manifest_path, manifest_data):
    """Save manifest to file."""
    try:
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        debug_print(f"Unable to save manifest: {e}", "WARNING")

def _backfill_missing_titles(downloader, manifest_data, manifest_path):
    """Backfill missing titles in manifest."""
    records = manifest_data.get('records', [])
    missing_titles = [r for r in records if r.get('status') == 'success' and not r.get('title')]
    
    if not missing_titles:
        debug_print("All records have titles", "SUCCESS")
        return
    
    debug_print(f"Backfilling {len(missing_titles)} missing titles...")
    updated_count = 0
    
    for idx, rec in enumerate(missing_titles, 1):
        url = rec.get('url')
        if not url and rec.get('video_id'):
            url = f"https://www.youtube.com/watch?v={rec['video_id']}"
        
        if url:
            debug_print(f"[{idx}/{len(missing_titles)}] Getting title...")
            try:
                video_info = downloader.get_video_info_with_duration(url)
                if video_info and video_info.get('title'):
                    rec['title'] = video_info['title']
                    updated_count += 1
                    debug_print(f"Updated: {video_info['title'][:40]}...", "SUCCESS")
            except Exception as e:
                debug_print(f"Failed: {e}", "ERROR")
    
    if updated_count > 0:
        _save_manifest(manifest_path, manifest_data)
        debug_print(f"Backfilled {updated_count} titles", "SUCCESS")

def _run_single_download(downloader, config, final_output_dir, manifest_data, manifest_index, 
                        manifest_path, url, index):
    """Download single URL with proper directory handling and enhanced duplicate detection."""
    debug_print(f"Processing URL {index}: {url}", "PROCESS")
    
    # Extract video ID for duplicate checking
    vid = downloader._extract_video_id(url)
    
    # Enhanced duplicate checking using unified index
    if downloader._is_duplicate(vid, url):
        debug_print("Skipping duplicate URL", "WARNING")
        return
    
    # Legacy duplicate check in current manifest index
    if vid and vid in manifest_index and manifest_index[vid].get('status') == 'success':
        debug_print("Already downloaded in current manifest")
        return
    
    # Language classification will be done automatically by the config
    language_output_dir = config.get_language_output_dir(url)
    language_folder = os.path.basename(language_output_dir)
    
    debug_print(f"Language: {language_folder}")
    
    # Update directories
    original_config_output_dir = config.output_dir
    config.output_dir = language_output_dir
    
    try:
        # Set basename
        basename = build_filename(index, url).replace('.wav', '')
        downloader._current_basename = basename
        
        # Download
        result = downloader.download_audio_from_yturl(url, index=index)
        
        # Clean up
        downloader._current_basename = None
        
        if isinstance(result, tuple) and result[0]:
            wav_path, duration = result
            debug_print(f"Success: {wav_path} ({duration}s)", "SUCCESS")
            
            # Update manifest
            record = {
                'video_id': vid or '',
                'url': url,
                'output_path': wav_path,
                'status': 'success',
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'duration_seconds': duration,
                'title': get_video_title(url),
                'language_folder': language_folder,
                'download_index': index,
                'classified': False  # New entries need to be classified
            }
            
            if vid:
                manifest_index[vid] = record
                # Update unified index with new record
                if hasattr(downloader, 'unified_index'):
                    downloader.unified_index[vid] = {'source': 'primary', 'record': record}
                    downloader.unified_index[f"url_{url}"] = {'source': 'primary', 'record': record}
            manifest_data.setdefault('records', []).append(record)
            manifest_data['total_duration_seconds'] = sum(r.get('duration_seconds', 0) for r in manifest_data['records'])
            _save_manifest(manifest_path, manifest_data)
            debug_print(f"Manifest updated: {len(manifest_data['records'])} files", "INFO")
        else:
            debug_print("Download failed", "ERROR")
            
    finally:
        # Restore directories
        config.output_dir = original_config_output_dir

def _process_urls_from_file(downloader, config, final_output_dir, manifest_data, manifest_index, 
                           manifest_path, urls_file):
    """Process URLs from file."""
    if not os.path.exists(urls_file):
        debug_print(f"File not found: {urls_file}", "WARNING")
        return
    
    with open(urls_file, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip().startswith('http')]
    
    debug_print(f"Processing {len(urls)} URLs", "INFO")
    
    # Filter already downloaded
    urls_to_process = []
    for url in urls:
        vid = downloader._extract_video_id(url)
        if not (vid and vid in manifest_index and manifest_index[vid].get('status') == 'success'):
            urls_to_process.append(url)
    
    debug_print(f"{len(urls_to_process)} URLs to process", "INFO")
    
    if urls_to_process:
        next_index = len(manifest_data.get('records', [])) + 1
        for idx, url in enumerate(urls_to_process):
            current_index = next_index + idx
            print(f"\n===== [{current_index}] =====")
            _run_single_download(downloader, config, final_output_dir, manifest_data, manifest_index, 
                               manifest_path, url, current_index)
        debug_print("Batch completed", "SUCCESS")
    else:
        debug_print("All URLs processed", "SUCCESS")

# =================================================================
# MAIN FUNCTION
# =================================================================

def main():
    """Simplified main function."""
    try:
        debug_print("Starting YouTube Audio Downloader...", "SUCCESS")
        
        # Setup
        config, downloader, final_output_dir = _setup_environment()
        
        # Load manifest
        manifest_path = os.path.join(final_output_dir, 'manifest.json')
        manifest_data, manifest_index = _load_manifest(manifest_path)
        
        # Backfill titles
        _backfill_missing_titles(downloader, manifest_data, manifest_path)
        
        # Process command line
        args = sys.argv[1:]
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_urls_file = os.path.join(base_dir, 'youtube_url_outputs', 'collected_video_urls.txt')
        
        if not args:
            # Default: process from collected URLs
            _process_urls_from_file(downloader, config, final_output_dir, manifest_data, manifest_index, 
                                   manifest_path, default_urls_file)
        elif args[0] == '--from-file' and len(args) >= 2:
            # Process from specified file
            file_path = args[1]
            if not os.path.exists(file_path):
                debug_print("File not found", "ERROR")
                sys.exit(1)
            _process_urls_from_file(downloader, config, final_output_dir, manifest_data, manifest_index, 
                                   manifest_path, file_path)
        else:
            # Process individual URLs
            for i, url in enumerate(args, start=1):
                print(f"\n===== [{i}] =====")
                _run_single_download(downloader, config, final_output_dir, manifest_data, manifest_index, 
                                   manifest_path, url, i)
    except KeyboardInterrupt:
        debug_print("Download interrupted by user", "WARNING")
        sys.exit(1)
    except Exception as e:
        debug_print(f"Fatal error: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()