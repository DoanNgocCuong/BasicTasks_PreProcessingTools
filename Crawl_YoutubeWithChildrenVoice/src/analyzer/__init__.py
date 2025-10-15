# analyzer package

"""
Analyzer Package - Audio analysis and classification

This package handles voice classification, language detection,
and other audio analysis tasks for children's voice content.
"""

# Lazy import to avoid loading heavy dependencies at package import time
def __getattr__(name):
    if name == "VoiceClassifier":
        try:
            from .voice_classifier import VoiceClassifier
            return VoiceClassifier
        except ImportError as e:
            print(f"Warning: VoiceClassifier not available: {e}")
            return None
    elif name == "VoiceClassificationResult":
        try:
            from .voice_classifier import VoiceClassificationResult
            return VoiceClassificationResult
        except ImportError as e:
            print(f"Warning: VoiceClassificationResult not available: {e}")
            return None
    elif name == "LanguageDetector":
        from .language_detector import LanguageDetector
        return LanguageDetector
    elif name == "LanguageDetectionResultLocal":
        from .language_detector import LanguageDetectionResultLocal
        return LanguageDetectionResultLocal
    elif name == "run_analysis_phase":
        from .analysis_phases import run_analysis_phase
        return run_analysis_phase
    elif name == "run_local_analysis":
        from .analysis_phases import run_local_analysis
        return run_local_analysis
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")