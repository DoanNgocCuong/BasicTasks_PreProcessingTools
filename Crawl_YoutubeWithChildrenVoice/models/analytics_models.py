"""
Analytics Domain Models

Data classes and models for analytics and reporting functionality.
These models define the structure for query statistics and analysis results.

Author: Refactoring Assistant
"""

from dataclasses import dataclass


@dataclass
class QueryStatistics:
    """Data class for query statistics."""
    query: str
    videos_collected: int
    videos_reviewed: int
    videos_evaluated: int
    videos_with_children_voice: int
    videos_vietnamese: int
    videos_not_vietnamese: int
    efficiency_rate: float
    children_voice_rate: float
    vietnamese_rate: float
    new_channels_found: int