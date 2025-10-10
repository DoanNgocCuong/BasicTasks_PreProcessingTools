"""
Base Configuration Classes

Provides base configuration functionality and common patterns
for all configuration classes in the system.

Author: Refactoring Assistant
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any
from env_config import config as env_config


class BaseConfig:
    """Base configuration class with common functionality."""
    
    def __init__(self):
        # Get the base directory for the project
        self.base_dir = Path(__file__).parent.parent
        self.script_dir = self.base_dir  # For backward compatibility
        
        # Common directories
        self.output_dir = self.base_dir / "youtube_url_outputs"
        self.audio_outputs_dir = self.base_dir / "youtube_audio_outputs"
        self.final_audio_dir = self.base_dir / "final_audio_files"
        self.crawler_outputs_dir = self.base_dir / "crawler_outputs"
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Environment configuration access
        self.env = env_config
    
    def _ensure_directories(self):
        """Ensure all required directories exist."""
        directories = [
            self.output_dir,
            self.audio_outputs_dir, 
            self.final_audio_dir,
            self.crawler_outputs_dir
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert relative path to absolute path from base directory."""
        return self.base_dir / relative_path
    
    def get_temp_file(self, prefix: str = "temp", suffix: str = ".tmp") -> Path:
        """Generate a temporary file path."""
        import uuid
        temp_name = f"{prefix}_{uuid.uuid4().hex[:8]}{suffix}"
        return self.base_dir / "temp" / temp_name