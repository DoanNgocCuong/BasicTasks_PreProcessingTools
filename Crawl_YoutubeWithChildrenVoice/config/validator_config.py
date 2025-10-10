"""
Validator Configuration

Configuration for the YouTube URL validator module including file paths,
regex patterns, and validation settings.

Author: Refactoring Assistant
"""

import re
from pathlib import Path
from typing import List
from .base_config import BaseConfig


class ValidatorConfig(BaseConfig):
    """Configuration for the URL validator."""
    
    def __init__(self):
        super().__init__()
        
        # Default file paths
        self.default_input_file = self.output_dir / "collected_video_urls.txt"
        self.default_output_dir = self.output_dir
        
        # Output file names
        self.duplicates_report_file = self.default_output_dir / "duplicates_report.txt"
        self.cleaned_urls_file = self.default_output_dir / "cleaned_video_urls.txt"
        self.validation_stats_file = self.default_output_dir / "validation_statistics.txt"
        
        # YouTube URL patterns
        self.youtube_patterns = [
            r'https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'https://youtu\.be/([a-zA-Z0-9_-]{11})',
            r'https://m\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        ]
        
        # Compiled regex patterns
        self.compiled_patterns = [re.compile(pattern) for pattern in self.youtube_patterns]
    
    def get_compiled_patterns(self) -> List[re.Pattern]:
        """Get compiled regex patterns for URL validation."""
        return self.compiled_patterns
    
    def add_custom_pattern(self, pattern: str):
        """Add a custom URL pattern."""
        self.youtube_patterns.append(pattern)
        self.compiled_patterns.append(re.compile(pattern))