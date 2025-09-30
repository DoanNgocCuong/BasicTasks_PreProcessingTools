#!/usr/bin/env python3
"""
Environment Configuration Module for TikTok Children's Voice Crawler

This module handles loading environment variables from .env files and provides
a centralized configuration system for the TikTok audio crawler project.
Based on the YouTube crawler's env_config.py with TikTok-specific adaptations.

Features:
    - Automatic .env file loading
    - Type conversion (string, int, float, bool)
    - Default value support
    - Validation for required variables
    - TikTok API specific configurations

Usage:
    from env_config import config
    
    # Access configuration values
    api_key = config.TIKTOK_API_KEY
    max_workers = config.MAX_WORKERS
    debug_mode = config.DEBUG_MODE

Author: Generated for TikTok Audio Crawler (adapted from YouTube crawler)
Version: 1.0
"""

import os
from pathlib import Path
from typing import Union, Optional, Any, TypeVar, List

# Try to import dotenv, fallback to manual .env parsing if not available
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("⚠️ python-dotenv not available, using manual .env parsing")

T = TypeVar('T', str, int, float, bool)


def manual_load_dotenv(env_file_path: str) -> None:
    """Manual .env file parsing when python-dotenv is not available"""
    if not Path(env_file_path).exists():
        return
    
    print(f"📋 Manually parsing .env file: {env_file_path}")
    try:
        with open(env_file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                # Parse KEY=VALUE format
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Remove quotes if present
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    
                    # Set environment variable
                    os.environ[key] = value
                    print(f"  Set {key}={value}")
                    
    except Exception as e:
        print(f"⚠️ Error parsing .env file: {e}")


class EnvironmentConfig:
    """Configuration class that loads and validates environment variables for TikTok crawler."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration by loading .env file.
        
        Args:
            env_file (str, optional): Path to .env file. Defaults to '.env' in current directory.
        """
        # Determine .env file path(s)
        env_paths = []
        if env_file is not None:
            env_paths.append(Path(env_file))
        else:
            # Prefer module directory .env, then fallback to current working directory .env
            env_paths.append(Path(__file__).parent / '.env')
            cwd_env = Path.cwd() / '.env'
            if cwd_env not in env_paths:
                env_paths.append(cwd_env)
        
        loaded_any = False
        for path in env_paths:
            if path.exists():
                if DOTENV_AVAILABLE:
                    from dotenv import load_dotenv  # Import here to avoid unbound variable warning
                    load_dotenv(str(path), override=False)
                    print(f"✅ Loaded environment variables from: {path}")
                else:
                    manual_load_dotenv(str(path))
                    print(f"✅ Manually loaded environment variables from: {path}")
                loaded_any = True
        
        if not loaded_any:
            print("⚠️ No .env file found in expected locations (module dir or CWD). Using system environment variables only.")
    
    def get_env(self, key: str, default: Any = None, 
                required: bool = False, var_type: type = str) -> Any:
        """
        Get environment variable with type conversion and validation.
        
        Args:
            key (str): Environment variable name
            default: Default value if not found
            required (bool): Whether this variable is required
            var_type (type): Type to convert to (str, int, float, bool)
            
        Returns:
            Converted environment variable value
            
        Raises:
            ValueError: If required variable is missing or conversion fails
        """
        value = os.getenv(key)
        
        # Handle missing required variables
        if required and value is None:
            raise ValueError(f"Required environment variable '{key}' is not set")
        
        # Use default if not found
        if value is None:
            return default
        
        # Type conversion
        try:
            if var_type == bool:
                return value.lower() in ('true', '1', 'yes', 'on')
            elif var_type == int:
                return int(value)
            elif var_type == float:
                return float(value)
            else:
                return str(value).strip('"\'')  # Remove quotes if present
        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot convert environment variable '{key}' to {var_type.__name__}: {e}")
    
    # TikTok API Configuration
    @property
    def TIKTOK_API_KEY(self) -> str:
        """Primary TikTok RapidAPI key (required)."""
        return self.get_env('TIKTOK_API_KEY', required=True)
    
    @property
    def TIKTOK_API_KEYS(self) -> List[str]:
        """List of all available TikTok API keys (supports CSV TIKTOK_API_KEYS and singular TIKTOK_API_KEY)."""
        keys: List[str] = []
        
        # CSV list support
        csv_keys = self.get_env('TIKTOK_API_KEYS', default=None)
        if csv_keys:
            for k in str(csv_keys).split(','):
                k = k.strip()
                if k:
                    keys.append(k)
        
        # Single key support
        single_key = self.get_env('TIKTOK_API_KEY', default=None)
        if single_key:
            keys.append(single_key)
        
        # De-duplicate while preserving order
        seen = set()
        unique_keys: List[str] = []
        for k in keys:
            if k not in seen:
                seen.add(k)
                unique_keys.append(k)
        
        if not unique_keys:
            raise ValueError("No TikTok API keys found. Set TIKTOK_API_KEY or TIKTOK_API_KEYS in .env")
        return unique_keys
    
    @property
    def API_DELAY_MIN(self) -> int:
        """Minimum delay between API requests in milliseconds."""
        return self.get_env('API_DELAY_MIN', default=1000, var_type=int)
    
    @property
    def API_DELAY_MAX(self) -> int:
        """Maximum delay between API requests in milliseconds."""
        return self.get_env('API_DELAY_MAX', default=3000, var_type=int)
    
    # Transcription Services

    # Audio Processing Configuration
    @property
    def MAX_AUDIO_DURATION_SECONDS(self) -> Optional[int]:
        """Maximum audio duration to process in seconds. None means unlimited."""
        value = self.get_env('MAX_AUDIO_DURATION_SECONDS', default=None)
        try:
            if value is None or str(value).strip() == '':
                return None
            return int(value)
        except (ValueError, TypeError):
            return None
    
    @property
    def AUDIO_QUALITY(self) -> str:
        """Audio quality setting (low, medium, high)."""
        return self.get_env('AUDIO_QUALITY', default='medium')
    
    # Model Configuration
    @property
    def WHISPER_MODEL_SIZE(self) -> str:
        """Whisper model size (tiny, base, small, medium, large)."""
        return self.get_env('WHISPER_MODEL_SIZE', default='tiny')
    
    @property
    def WAV2VEC2_MODEL(self) -> str:
        """Wav2Vec2 model name for age/gender classification."""
        return self.get_env('WAV2VEC2_MODEL', default='audeering/wav2vec2-large-robust-24-ft-age-gender')
    
    # Processing Configuration
    @property
    def MAX_WORKERS(self) -> int:
        """Maximum number of parallel workers."""
        return self.get_env('MAX_WORKERS', default=4, var_type=int)
    
    @property
    def CHILD_THRESHOLD(self) -> float:
        """Probability threshold for classifying as child."""
        return self.get_env('CHILD_THRESHOLD', default=0.5, var_type=float)
    
    @property
    def AGE_THRESHOLD(self) -> float:
        """Age threshold for classifying as child (0.3 ~ 30 years)."""
        return self.get_env('AGE_THRESHOLD', default=0.3, var_type=float)
    
    # Debug Configuration
    @property
    def DEBUG_MODE(self) -> bool:
        """Enable debug mode with detailed logging."""
        return self.get_env('DEBUG_MODE', default=False, var_type=bool)
    
    @property
    def LOG_LEVEL(self) -> str:
        """Logging level (DEBUG, INFO, WARNING, ERROR)."""
        return self.get_env('LOG_LEVEL', default='INFO')
    
    # File Paths
    @property
    def OUTPUT_DIR(self) -> str:
        """Output directory for results."""
        return self.get_env('OUTPUT_DIR', default='./tiktok_url_outputs')
    
    @property
    def TEMP_AUDIO_DIR(self) -> str:
        """Temporary directory for audio files."""
        return self.get_env('TEMP_AUDIO_DIR', default='./temp_audio')
    
    # TikTok Specific Settings
    @property
    def DEFAULT_VIDEO_COUNT(self) -> int:
        """Default number of videos to fetch per user/keyword."""
        return self.get_env('DEFAULT_VIDEO_COUNT', default=30, var_type=int)
    
    @property
    def MAX_VIDEO_DURATION(self) -> int:
        """Maximum video duration to process (seconds)."""
        return self.get_env('MAX_VIDEO_DURATION', default=600, var_type=int)
    
    @property
    def DOWNLOAD_TIMEOUT(self) -> int:
        """Download timeout (seconds)."""
        return self.get_env('DOWNLOAD_TIMEOUT', default=120, var_type=int)
    
    def validate_configuration(self) -> None:
        """Validate all configuration values."""
        print("🔍 Validating TikTok crawler configuration...")
        
        # Validate API key format (basic check)
        api_keys = self.TIKTOK_API_KEYS
        for i, api_key in enumerate(api_keys, 1):
            if len(api_key) < 10:  # Basic sanity check
                print(f"⚠️ TikTok API key {i} seems too short (should be longer)")
        
        # Validate numeric ranges
        if not (1 <= self.MAX_WORKERS <= 16):
            print("⚠️ MAX_WORKERS should be between 1 and 16")
        
        if not (0.0 <= self.CHILD_THRESHOLD <= 1.0):
            print("⚠️ CHILD_THRESHOLD should be between 0.0 and 1.0")
        
        if not (0.0 <= self.AGE_THRESHOLD <= 1.0):
            print("⚠️ AGE_THRESHOLD should be between 0.0 and 1.0")
        
        # Validate model size
        valid_whisper_sizes = ['tiny', 'base', 'small', 'medium', 'large']
        if self.WHISPER_MODEL_SIZE not in valid_whisper_sizes:
            print(f"⚠️ WHISPER_MODEL_SIZE should be one of: {valid_whisper_sizes}")
        
        # Validate delays
        if self.API_DELAY_MIN > self.API_DELAY_MAX:
            print("⚠️ API_DELAY_MIN should not be greater than API_DELAY_MAX")
        
        print("✅ Configuration validation completed")
    
    def print_configuration(self) -> None:
        """Print current configuration (hiding sensitive values)."""
        print("\n🔧 Current TikTok Crawler Configuration:")
        print("=" * 50)
        api_keys = self.TIKTOK_API_KEYS
        for i, api_key in enumerate(api_keys, 1):
            print(f"TikTok API Key {i}: {'*' * 10}...{api_key[-4:]}")
        print(f"Total API Keys Available: {len(api_keys)}")
        print(f"API Delay Range: {self.API_DELAY_MIN}-{self.API_DELAY_MAX}ms")
        
        max_dur = self.MAX_AUDIO_DURATION_SECONDS
        print(f"Max Audio Duration: {'unlimited' if max_dur is None else str(max_dur)+'s'}")
        if max_dur:
            print(f"  → Videos >{max_dur}s will be chunked into {max_dur}s segments")
        else:
            print(f"  → All videos processed in full (no chunking)")
            
        print(f"Audio Quality: {self.AUDIO_QUALITY}")
        print(f"Whisper Model: {self.WHISPER_MODEL_SIZE}")
        print(f"Wav2Vec2 Model: {self.WAV2VEC2_MODEL}")
        print(f"Max Workers: {self.MAX_WORKERS}")
        print(f"Child Threshold: {self.CHILD_THRESHOLD}")
        print(f"Age Threshold: {self.AGE_THRESHOLD}")
        print(f"Debug Mode: {self.DEBUG_MODE}")
        print(f"Log Level: {self.LOG_LEVEL}")
        print(f"Output Directory: {self.OUTPUT_DIR}")
        print(f"Temp Audio Directory: {self.TEMP_AUDIO_DIR}")
        
        # TikTok specific settings
        print(f"Default Video Count: {self.DEFAULT_VIDEO_COUNT}")
        print(f"Max Video Duration: {self.MAX_VIDEO_DURATION}s")
        print(f"Download Timeout: {self.DOWNLOAD_TIMEOUT}s")
        
        print("=" * 50)


# Create global configuration instance
config = EnvironmentConfig()

# Validate configuration on import
if __name__ == '__main__':
    config.validate_configuration()
    config.print_configuration()
else:
    # Silent validation when imported
    try:
        config.validate_configuration()
    except Exception as e:
        print(f"⚠️ TikTok crawler configuration warning: {e}")