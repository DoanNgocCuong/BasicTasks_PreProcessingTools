#!/usr/bin/env python3
"""
Mock Audio Classifier for Testing

This is a simple mock version of the audio classifier that doesn't require torch.
It randomly classifies audio files for testing purposes.

Author: Generated for testing
"""

import random
import time
import logging

logger = logging.getLogger(__name__)

class AudioClassifier:
    """Mock audio classifier for testing purposes."""
    
    def __init__(self):
        """Initialize mock classifier."""
        logger.info("Mock AudioClassifier initialized")
        random.seed(42)  # For consistent test results
    
    def is_child_audio(self, audio_file_path: str) -> bool:
        """
        Mock children's voice detection.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Random boolean result (seeded for consistency)
        """
        # Simulate processing time (increased for testing concurrency)
        time.sleep(1.0)  # 1 second delay to make concurrency visible
        
        # Return deterministic "random" result based on file path
        # This ensures consistent results for testing
        hash_val = hash(audio_file_path) % 100
        result = hash_val < 30  # 30% chance of having children's voice
        
        logger.debug(f"Mock classification for {audio_file_path}: {result}")
        return result