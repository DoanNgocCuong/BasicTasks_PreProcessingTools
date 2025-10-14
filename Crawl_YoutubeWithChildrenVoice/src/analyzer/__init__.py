# analyzer package

"""
Analyzer Package - Audio analysis and classification

This package handles voice classification, language detection,
and other audio analysis tasks for children's voice content.
"""

from .voice_classifier import VoiceClassifier, VoiceClassificationResult
from .language_detector import LanguageDetector, LanguageDetectionResultLocal

__all__ = [
    "VoiceClassifier",
    "VoiceClassificationResult",
    "LanguageDetector",
    "LanguageDetectionResultLocal"
]