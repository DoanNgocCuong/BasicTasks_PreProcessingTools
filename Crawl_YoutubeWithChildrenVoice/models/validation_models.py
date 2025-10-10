"""
Validation Domain Models

Data classes and models for URL validation and audio classification results.
These models define the structure for validation processes and their outcomes.

Author: Refactoring Assistant
"""

from dataclasses import dataclass
from typing import List, Dict, Set, Optional


@dataclass
class DuplicateInfo:
    """Data class for duplicate URL information."""
    url: str
    normalized_url: str
    positions: List[int]  # Line positions (0-based) where this URL appears
    count: int


@dataclass
class ValidationResult:
    """Data class for validation results."""
    total_urls: int
    unique_urls: int
    duplicate_count: int
    invalid_urls: int
    duplicates: Dict[str, int]  # Kept for backward compatibility
    invalid_url_list: List[str]
    valid_urls: Set[str]
    duplicate_urls: List[DuplicateInfo]  # Detailed duplicate information with positions


@dataclass
class ClassificationResult:
    """Data class for audio classification results."""
    audio_path: str
    is_children: bool
    confidence: float
    error: Optional[str] = None
    processing_time: float = 0.0