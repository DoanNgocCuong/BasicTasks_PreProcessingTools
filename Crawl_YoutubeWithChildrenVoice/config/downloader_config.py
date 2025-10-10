"""
Audio Downloader Configuration

Configuration for the YouTube audio downloader module including yt-dlp settings,
file paths, and download parameters.

Author: Refactoring Assistant
"""

import os
from typing import Optional, Dict, Any
from .base_config import BaseConfig
from youtube_language_classifier import YouTubeLanguageClassifier


# Constants from the original module
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


class AudioDownloaderConfig(BaseConfig):
    """Enhanced configuration class for audio downloader with dual manifest support."""
    
    def __init__(self, user_agent=None, output_dir=None, manifest_path=None, original_manifest_path=None, enable_duplicate_check=True):
        super().__init__()
        
        # Override output directory if provided
        if output_dir:
            self.output_dir = self.get_absolute_path(output_dir)
        else:
            self.output_dir = self.audio_outputs_dir
        
        # Store the base output directory to prevent nested language folders
        self.base_output_dir = self.output_dir
        
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
    
    def _load_user_agent(self):
        """Load user agent from environment or return None."""
        return self.env.get_env('USER_AGENT', default=None)
    
    def get_ydl_opts_copy(self) -> Dict[str, Any]:
        """Get a copy of yt-dlp options for safe modification."""
        return self.ydl_opts.copy()
    
    def update_output_dir(self, new_dir: str):
        """Update the output directory and ensure it exists."""
        self.output_dir = self.get_absolute_path(new_dir)
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_language_from_cache(self, video_id: str) -> Optional[str]:
        """Get cached language detection result."""
        return self._language_cache.get(video_id)
    
    def cache_language_result(self, video_id: str, language: str):
        """Cache language detection result."""
        self._language_cache[video_id] = language
    
    def get_output_path(self, filename: str) -> str:
        """Get full path for output file."""
        return str(self.output_dir / filename)
    
    def get_language_output_dir(self, url: str) -> str:
        """Get language-specific output directory using transcript-based detection."""
        from utils.debug_utils import debug_print
        
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
            
        # Always use the base output directory for language folder creation
        # This prevents nested language folders when config.output_dir is already set to a language folder
        base_output_dir = getattr(self, 'base_output_dir', self.output_dir)
        language_dir = base_output_dir / language_folder
        language_dir.mkdir(parents=True, exist_ok=True)
        return str(language_dir)
    
    def get_m4a_filename(self, index: int) -> str:
        """Get M4A filename."""
        custom_base = getattr(self, '_current_basename', None)
        return f'{custom_base}.m4a' if custom_base else f'output_{index}.m4a'
    
    def get_wav_filename(self, index: int) -> str:
        """Get WAV filename."""
        custom_base = getattr(self, '_current_basename', None)
        return f'{custom_base}.wav' if custom_base else f'output_{index}.wav'