"""
Constants for YouTube Children's Voice Crawler

This module contains all hardcoded configuration values that can be easily adjusted.
"""

# Batch processing
BATCH_PROCESSING_INTERVAL = 20  # URLs collected before triggering batch processing

# Search configuration
DEFAULT_TARGET_VIDEOS_PER_QUERY = 500
DEFAULT_MAX_RECOMMENDED_PER_QUERY = 100
DEFAULT_MIN_TARGET_COUNT = 1
DEFAULT_MAX_SIMILAR_VIDEOS_PER_CHANNEL = 10

# Download configuration
DEFAULT_DOWNLOAD_BATCH_SIZE = 1
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 4
DEFAULT_MAX_FILENAME_LENGTH = 40  # Maximum length for camelCase filenames

# Upload configuration
DEFAULT_MAX_CONCURRENT_UPLOADS = 5  # Maximum concurrent upload workers

# Analysis configuration
DEFAULT_MAX_CHUNK_DURATION_SECONDS = 1200  # 20 minutes
DEFAULT_CHUNK_OVERLAP_SECONDS = 5
DEFAULT_MAX_CONSECUTIVE_NO_CHILDREN = 3
DEFAULT_CHILD_VOICE_THRESHOLD = 0.5
DEFAULT_LANGUAGE_CONFIDENCE_THRESHOLD = 0.8

# API configuration
DEFAULT_POLL_INTERVAL_SECONDS = 300
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT_SECONDS = 300
DEFAULT_MIN_REQUEST_INTERVAL = 0.1

# Retry delays (in seconds)
DEFAULT_RETRY_DELAYS = [1, 2, 4]