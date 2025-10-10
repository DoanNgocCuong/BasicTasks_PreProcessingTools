"""
Core Domain Models Package

This package contains all the data classes and domain models used throughout
the YouTube crawler system. These models define the contracts for data
exchange between different modules and services.

Author: Refactoring Assistant
"""

from .crawler_models import CrawlerConfig, AnalysisResult
from .validation_models import DuplicateInfo, ValidationResult, ClassificationResult
from .analytics_models import QueryStatistics

__all__ = [
    'CrawlerConfig',
    'AnalysisResult', 
    'DuplicateInfo',
    'ValidationResult',
    'ClassificationResult',
    'QueryStatistics'
]