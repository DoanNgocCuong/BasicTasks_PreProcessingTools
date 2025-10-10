"""
Crawler Domain Models

Data classes and models specific to the YouTube video crawling functionality.
These models define the structure for crawler configuration and analysis results.

Author: Refactoring Assistant
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any


@dataclass
class CrawlerConfig:
    """Data class for crawler configuration loaded from JSON file."""
    debug_mode: bool
    target_videos_per_query: int
    search_queries: List[str]
    max_recommended_per_query: int = 100
    min_target_count: int = 1
    download_method: str = "api_assisted"
    yt_dlp_primary: bool = True
    cookie_settings: Optional[Dict[str, Any]] = None
    enable_language_detection: bool = True
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"


@dataclass
class AnalysisResult:
    """Data class for audio analysis results."""
    is_vietnamese: bool
    detected_language: str
    has_children_voice: Optional[bool]
    confidence: float
    error: Optional[str]
    total_analysis_time: Optional[float] = None
    children_detection_time: Optional[float] = None
    video_length_seconds: Optional[float] = None
    chunks_analyzed: Optional[int] = None
    positive_chunk_index: Optional[int] = None
    was_chunked: bool = False