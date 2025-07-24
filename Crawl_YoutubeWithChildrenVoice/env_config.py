#!/usr/bin/env python3
"""
Environment Configuration Module

This module handles loading environment variables from .env files and provides
a centralized configuration system for the YouTube audio crawler project.

Features:
    - Automatic .env file loading
    - Type conversion (string, int, float, bool)
    - Default value support
    - Validation for required variables
    - Environment-specific configurations

Usage:
    from env_config import config
    
    # Access configuration values
    api_key = config.YOUTUBE_API_KEY
    max_workers = config.MAX_WORKERS
    debug_mode = config.DEBUG_MODE

Author: Generated for YouTube Audio Crawler
Version: 1.0
"""

import os
from pathlib import Path
from typing import Union, Optional, Any, TypeVar
from dotenv import load_dotenv

T = TypeVar('T', str, int, float, bool)


class EnvironmentConfig:
    """Configuration class that loads and validates environment variables."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration by loading .env file.
        
        Args:
            env_file (str, optional): Path to .env file. Defaults to '.env' in current directory.
        """
        # Determine .env file path
        if env_file is None:
            env_file = str(Path(__file__).parent / '.env')
        
        # Load .env file if it exists
        if Path(env_file).exists():
            load_dotenv(env_file)
            print(f"✅ Loaded environment variables from: {env_file}")
        else:
            print(f"⚠️ No .env file found at: {env_file}")
            print("Using system environment variables only")
    
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
    
    # YouTube API Configuration
    @property
    def YOUTUBE_API_KEY(self) -> str:
        """YouTube Data API v3 key (required)."""
        return self.get_env('YOUTUBE_API_KEY', required=True)
    
    # Audio Processing Configuration
    @property
    def MAX_AUDIO_DURATION_SECONDS(self) -> int:
        """Maximum audio duration to process in seconds."""
        return self.get_env('MAX_AUDIO_DURATION_SECONDS', default=300, var_type=int)
    
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
        return self.get_env('OUTPUT_DIR', default='./youtube_url_outputs')
    
    @property
    def TEMP_AUDIO_DIR(self) -> str:
        """Temporary directory for audio files."""
        return self.get_env('TEMP_AUDIO_DIR', default='./temp_audio')
    
    def validate_configuration(self) -> None:
        """Validate all configuration values."""
        print("🔍 Validating configuration...")
        
        # Validate API key format (basic check)
        api_key = self.YOUTUBE_API_KEY
        if not api_key.startswith('AIza'):
            print("⚠️ YouTube API key format may be incorrect (should start with 'AIza')")
        
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
        
        print("✅ Configuration validation completed")
    
    def print_configuration(self) -> None:
        """Print current configuration (hiding sensitive values)."""
        print("\n🔧 Current Configuration:")
        print("=" * 50)
        print(f"YouTube API Key: {'*' * 20}...{self.YOUTUBE_API_KEY[-4:]}")
        print(f"Max Audio Duration: {self.MAX_AUDIO_DURATION_SECONDS}s")
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
        print(f"⚠️ Configuration warning: {e}")
