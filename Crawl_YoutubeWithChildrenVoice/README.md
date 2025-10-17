# YouTube Children's Voice Crawler - Functionality Overview

## Recent Updates

- **Refactoring (October 2025)**: Improved import handling in main.py to use direct imports from analysis and filtering modules, resolving Pylance type checking issues.
- **Voice Classifier Fixes**: Fixed unbound variable issues in analysis_phases.py by properly handling optional imports and adding null checks.
- **Error Resolution**: Resolved multiple Pylance errors related to awaitable objects and missing function arguments.
- **Analysis-Filtering-Upload Script**: Added `run_analysis_filtering_upload.py` for processing existing audio files through analysis, filtering, and upload phases only.

## Quick Start Scripts

### Analysis-Filtering-Upload Script (`run_analysis_filtering_upload.py`)

A standalone script for processing existing audio files through the analysis, filtering, and upload phases:

```bash
# Run with default configuration
python run_analysis_filtering_upload.py

# Use custom config file
python run_analysis_filtering_upload.py --config custom.json

# Enable verbose logging
python run_analysis_filtering_upload.py --verbose

# Validate configuration without running
python run_analysis_filtering_upload.py --dry-run
```

This script is useful when you have already downloaded audio files and just need to analyze them for children's voices, filter the results, and upload the classified files to your server.

## Core System Functionality

The YouTube Children's Voice Crawler is a comprehensive, modular system designed to automatically discover, analyze, and curate children's voice content from YouTube. The system operates through four interconnected phases: video discovery, audio extraction, content analysis, and quality filtering.

## 🏗️ System Architecture

### Main Orchestrator (`main.py`)

The central coordination module that manages the entire crawling workflow:

- **Workflow Orchestration**: Coordinates the four-phase pipeline (search → download → analyze → filter)
- **Configuration Management**: Loads and validates system configuration from multiple sources
- **Error Handling**: Implements comprehensive error recovery and graceful degradation
- **Progress Tracking**: Provides real-time progress monitoring and detailed statistics
- **CLI Interface**: Supports command-line arguments for configuration overrides and dry-run validation

#### **Core Algorithms**

**Pipeline Orchestration Algorithm:**

- **State Machine Pattern**: Uses async state machine to manage phase transitions
- **Dependency Resolution**: Implements topological sorting for component initialization
- **Resource Allocation**: Dynamic resource pooling with semaphore-based concurrency control
- **Graceful Shutdown**: Implements signal handling with cleanup routines (O(n) cleanup time)

**Configuration Loading Algorithm:**

- **Priority-based Merging**: CLI args > JSON file > Environment variables > Defaults
- **Validation Pipeline**: Multi-stage validation with early termination on critical errors
- **Type Coercion**: Automatic type conversion with fallback mechanisms
- **Schema Validation**: Runtime schema checking against predefined dataclasses

**Error Recovery Algorithm:**

- **Circuit Breaker Pattern**: Automatic component isolation on repeated failures
- **Exponential Backoff**: Progressive delay increases (1s, 2s, 4s, 8s...) with jitter
- **Partial Success Handling**: Continues processing successful items while logging failures
- **Recovery Checkpointing**: Saves progress state for resumable operations

### Configuration System (`config.py`)

Unified configuration management providing:

- **Multi-Source Configuration**: Supports environment variables, JSON files, and CLI overrides
- **Type-Safe Settings**: Strongly typed configuration classes with validation
- **Hierarchical Structure**: Organized configuration for YouTube API, search, download, analysis, and filtering
- **Dynamic Validation**: Runtime configuration validation with detailed error reporting
- **Environment Integration**: Seamless integration with environment variables and configuration files

#### Configuration Management

The system uses a hierarchical configuration system with the following priority:

- Command-line arguments (highest priority)
- JSON configuration file
- Environment variables
- Hardcoded defaults (lowest priority)

Configuration is loaded from multiple sources and merged into a single `CrawlerConfig` dataclass with validation. The system supports loading search queries from a `queries.txt` file with fallback to default Vietnamese children's content queries.

## 🔍 Video Discovery Phase

### Search Engine (`crawler/search_engine.py`)

Video discovery system that:

- **Multi-Query Processing**: Executes searches across multiple queries sequentially
- **API Key Rotation**: Cycles through available YouTube API keys for quota management
- **Duplicate Prevention**: Uses a set to track collected video IDs and prevent duplicates
- **Rate Limiting**: Implements delays between queries to respect API limits
- **Statistics Tracking**: Records search metrics and performance data
- **Progress Monitoring**: Shows progress through query processing

The search engine coordinates with the YouTube API client to discover videos and collect metadata.

### YouTube API Client (`crawler/youtube_api.py`)

YouTube Data API v3 interface providing:

- **Key Management**: Cycles through multiple API keys for quota distribution
- **Error Handling**: Exponential backoff retry logic for API failures
- **Quota Monitoring**: Tracks usage and handles quota exceeded errors
- **Data Parsing**: Converts API responses to structured video metadata
- **Rate Limiting**: Enforces delays between requests to prevent throttling

The client handles search queries and video detail retrieval with robust error recovery.

## 📥 Audio Extraction Phase

### Audio Downloader (`downloader/audio_downloader.py`)

Audio extraction system featuring:

- **Dual Download Methods**: yt-dlp as primary method with API-assisted fallback
- **Concurrent Processing**: Parallel downloads with configurable limits
- **Format Conversion**: Automatic MP3 conversion with quality settings
- **Error Handling**: Comprehensive error classification and retry logic
- **Progress Tracking**: Download progress monitoring and statistics

The downloader handles video-to-audio conversion with robust fallback mechanisms.

## 🧠 Content Analysis Phase

### Voice Classification (`analyzer/voice_classifier.py`)

Machine learning-based voice analysis system that:

- **Feature Extraction**: Computes MFCCs, spectral features, and acoustic characteristics using librosa
- **Children's Voice Detection**: PyTorch model trained to identify children's vocal patterns
- **Confidence Scoring**: Provides probability scores for voice classification decisions
- **Model Caching**: Shared model instances for memory efficiency
- **Fallback Classification**: Heuristic-based classification when model unavailable

The classifier uses a neural network to distinguish children's voices from adults based on acoustic features.

### Language Detection (`analyzer/language_detector.py`)

Language identification system that:

- **Acoustic Language Modeling**: Uses speech acoustics to identify spoken language
- **Vietnamese Focus**: Specialized detection for Vietnamese language patterns
- **Multi-Language Support**: Handles Vietnamese, English, and unknown languages
- **Confidence Assessment**: Provides confidence scores for language identification
- **PyTorch Model**: Neural network-based classification with feature extraction

The detector analyzes acoustic features to determine the language being spoken in audio recordings.

## ✅ Content Filtering Phase

### Filterer (`filterer/filtering_phases.py`)

Content filtering and organization system that:

- **File Validation**: Checks existence and integrity of downloaded audio files
- **Children's Voice Filtering**: Organizes files based on voice classification results
- **Language-based Organization**: Groups files by detected language in subdirectories
- **Duplicate Removal**: Eliminates duplicate entries and files
- **Manifest Management**: Updates JSON manifest with filtering results

The filterer processes the manifest to organize approved content and remove unsuitable files.

## 📊 Data Management

### Type-Safe Data Models (`models/models.py`)

Data structure definitions using Python dataclasses:

- **VideoMetadata**: YouTube video information with ID, title, channel, and source
- **Analysis Results**: Voice and language detection outcomes with confidence scores
- **Download Records**: Audio extraction results and file paths
- **Query Statistics**: Search performance metrics and counts

All models use type hints and validation for data integrity.

## 🛠️ Utility Systems

### Output Management (`utils/output_manager.py`)

Centralized logging and user interface system:

- **Multi-Level Logging**: Debug, info, warning, and error levels
- **Progress Bars**: Visual progress indicators for long operations
- **Emoji-enhanced Messages**: User-friendly status messages
- **File Logging**: Optional logging to files with timestamps

### File Management (`utils/file_manager.py`)

File system operations and path handling:

- **Directory Creation**: Automatic creation of output directories
- **Path Resolution**: Cross-platform path handling
- **File Validation**: Existence and integrity checks

### Progress Tracking (`utils/progress_tracker.py`)

Operation monitoring and statistics:

- **Multi-level Progress**: Tracks progress across different operation levels
- **Performance Metrics**: Timing and success rate statistics
- **ETA Calculation**: Estimated completion time based on current progress

## Performance Optimization

### Asynchronous Processing

The system uses Python's asyncio for concurrent operations:

- **Concurrent Downloads**: Parallel audio extraction with configurable limits
- **Non-blocking I/O**: Efficient API calls and file operations
- **Async Workflow**: Full async/await implementation from search to filtering

### Memory Management

Efficient resource utilization:

- **Streaming Processing**: Audio files processed without full loading in memory
- **Model Caching**: Shared ML model instances to reduce memory usage
- **Garbage Collection**: Explicit cleanup of temporary resources

### Error Resilience

Robust error handling:

- **Graceful Degradation**: Continues processing when components fail
- **Automatic Retries**: Exponential backoff for transient failures
- **State Persistence**: Progress saved to resume interrupted operations

## 🔒 System Reliability

### Data Integrity

Ensures data consistency:

- **Atomic Operations**: File writes and updates are atomic
- **Validation Checks**: Continuous validation of data integrity
- **Backup Creation**: Automatic backups before destructive operations

### Monitoring and Observability

System monitoring:

- **Performance Metrics**: Tracks throughput, latency, and success rates
- **Error Tracking**: Detailed logging with context and stack traces
- **Progress Monitoring**: Real-time visibility into processing status

This modular architecture enables the system to efficiently process thousands of YouTube videos, extracting high-quality children's voice data in Vietnamese while maintaining strict quality standards and operational reliability.
