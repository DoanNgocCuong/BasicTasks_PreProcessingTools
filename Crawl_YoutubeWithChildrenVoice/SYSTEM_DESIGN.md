# YouTube Children's Voice Crawler - System Design

**The Complete Bible for Understanding the System**

This document provides the authoritative technical specification for the YouTube Children's Voice Crawler. It explains the **why**, **how**, and **what** of every component in the system and how they work together.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Purpose and Goals](#system-purpose-and-goals)
3. [Architecture Overview](#architecture-overview)
4. [Core Workflow](#core-workflow)
5. [Module Directory Structure](#module-directory-structure)
6. [Data Models and Structures](#data-models-and-structures)
7. [Configuration System](#configuration-system)
8. [Error Handling and Resilience](#error-handling-and-resilience)
9. [Performance Characteristics](#performance-characteristics)
10. [Running the System](#running-the-system)

---

## Executive Summary

The YouTube Children's Voice Crawler is a modular, asynchronous Python system designed to:

- **Discover** thousands of YouTube videos matching search queries
- **Download** audio from these videos as MP3 files
- **Analyze** audio using machine learning to identify children's voices
- **Filter** audio based on voice classification and language detection
- **Organize** and upload classified content to a remote server

The system processes content through **5 interconnected phases** orchestrated by a central workflow engine, with comprehensive error recovery, data integrity protection, and progress tracking.

---

## System Purpose and Goals

### Primary Objective

Automatically collect, process, and curate high-quality children's voice audio from YouTube with minimal manual intervention while maintaining data integrity and operational reliability.

### Design Goals

1. **Modularity**: Each phase is independent and replaceable
2. **Resilience**: System continues operating despite component failures
3. **Efficiency**: Asynchronous operations for throughput optimization
4. **Reliability**: Atomic operations and comprehensive backups prevent data loss
5. **Observability**: Rich logging and progress tracking for monitoring
6. **Scalability**: Can process thousands of videos efficiently
7. **Maintainability**: Clear separation of concerns with minimal cross-module dependencies

---

## Architecture Overview

### High-Level System Design

```
┌─────────────────────────────────────────────────────────┐
│                    Workflow Orchestrator                │
│                    (src/main.py)                        │
├─────────────────────────────────────────────────────────┤
│   Phase 0: Manifest Cleaning                            │
│   ↓                                                      │
│   Phase 1: Video Discovery (URLs)  ←─────────┐          │
│   ↓                                           │          │
│   ┌─ Batch Processing ────────────────────────┤          │
│   ├─ Phase 2: Audio Download                 │          │
│   ├─ Phase 3: Audio Analysis                 │          │
│   ├─ Phase 4: Content Filtering               │          │
│   ├─ Phase 5: File Upload                    │          │
│   └────────────────────────────────────────┐  │          │
│   Repeat for each batch of ~20 URLs ◄─────┴──┘          │
└─────────────────────────────────────────────────────────┘
```

### Layered Architecture

```
┌──────────────────────────────────────────────┐
│        Application Layer (Phases 0-5)        │
│  (Cleaner, Crawler, Downloader, Analyzer,    │
│   Filterer, Uploader)                        │
├──────────────────────────────────────────────┤
│         Orchestration Layer                  │
│  (Main workflow, config loading, lifecycle)  │
├──────────────────────────────────────────────┤
│       Foundation Layer                       │
│  (Models, Config, Constants, Utilities)      │
├──────────────────────────────────────────────┤
│     Third-Party Services & APIs              │
│  (YouTube API, yt-dlp, librosa, torch)      │
└──────────────────────────────────────────────┘
```

---

## Core Workflow

### Workflow Execution Pattern

The system follows a **state machine pattern** with automatic recovery and graceful shutdown support:

#### Phase 0: Manifest Cleaning

**When**: At startup and after each processing phase (1-5)
**Purpose**: Ensure data integrity and consistency throughout the workflow
**Actions**:

- Remove duplicate URLs from discovered URLs file
- Validate manifest.json structure and integrity
- Clean up malformed records
- Consolidate duplicate manifest entries
- Prepare manifest for next phase

**Why**: Maintains data integrity and prevents corruption from accumulating during processing

#### Phase 1: Video Discovery (Discovery Phase)

**When**: After manifest cleaning
**Purpose**: Discover and collect YouTube video URLs
**Key Points**:

- Executes multiple search queries sequentially
- Each query targets 500 videos (configurable)
- Collects video metadata from YouTube Data API v3
- **Batch Processing Trigger**: Every 20 URLs collected automatically triggers phases 2-5

**Algorithm**:

```
FOR each search query:
  FOR each page of results:
    Extract video_id from result
    IF video_id not in existing_urls:
      Add URL to discovered_urls.txt
      Add metadata to discovered_videos.json
      IF collected_urls % 20 == 0:
        Trigger batch_callback() → Process phases 2-5
```

**Why Batch Processing?**

- Prevents memory buildup from thousands of URLs
- Enables streaming content processing
- Provides progress checkpoints
- Allows resumable operations

#### Phase 2: Audio Download (Extraction Phase)

**When**: When batch_callback is triggered (every ~20 URLs) or at end of discovery
**Purpose**: Extract audio from YouTube videos as MP3 files
**Actions**:

1. Read all unprocessed URLs from discovered_urls.txt
2. Download audio using yt-dlp (primary) or YouTube API (fallback)
3. Convert to MP3 with quality settings
4. Update manifest.json with download status and file paths
5. Handle errors: Skip failed downloads, continue processing

**Key Features**:

- **Concurrent Downloads**: Up to 4 simultaneous downloads (configurable)
- **Format Handling**: Converts audio to MP3 with standardized bitrate
- **Fallback Mechanism**: Uses API-assisted approach if yt-dlp fails
- **Error Recovery**: Failed downloads logged but don't stop workflow

#### Phase 3: Audio Analysis (Analysis Phase)

**When**: After download phase completes
**Purpose**: Analyze audio to identify children's voices and language
**Actions**:

1. For each downloaded audio file:
   - Extract MFCC and spectral features using librosa
   - Run through PyTorch-based voice classifier
   - Obtain confidence score for "children's voice" classification
2. Run language detection model (Vietnamese, English, Other)
3. Update manifest with analysis results

**ML Models Used**:

- **Voice Classifier**: PyTorch model identifying children's voices vs adults
- **Language Detector**: Acoustic language model for Vietnamese/English/Other

**Data Stored**:

```json
{
  "containing_children_voice": true/false,
  "voice_analysis_confidence": 0.0-1.0,
  "detected_language": "vi/en/other",
  "language_confidence": 0.0-1.0
}
```

#### Phase 4: Content Filtering (Filtering Phase)

**When**: After analysis phase completes
**Purpose**: Organize files by classification and remove unsuitable content
**Actions**:

1. Iterate through manifest records
2. For files with `containing_children_voice == true`:
   - If `detected_language == "vi"`: Move to `final_audio/vi/`
   - If `detected_language == "en"`: Move to `final_audio/en/`
   - Otherwise: Move to `final_audio/unknown/`
   - Mark as `classified: true`
3. For files with `containing_children_voice == false`:
   - Move to `final_audio/unclassified/`
   - Mark as `classified: true`
4. Remove duplicate entries from manifest
5. Verify file availability and update `file_available` flag

**Filtering Logic**:

```
IF file missing from disk:
  Set file_available = false
ELSE IF containing_children_voice:
  IF detected_language == "vi":
    Move to final_audio/vi/
  ELSE IF detected_language == "en":
    Move to final_audio/en/
  ELSE:
    Move to final_audio/unknown/
  Set classified = true
ELSE:
  Move to final_audio/unclassified/
  Set classified = true
```

#### Phase 5: File Upload (Upload Phase)

**When**: After filtering phase completes
**Purpose**: Upload classified children's voice files to remote server
**Actions**:

1. Identify uploadable files (classified, contains children's voice, not yet uploaded)
2. Organize into batches based on language
3. Create upload session on server
4. Upload files with progress tracking
5. Update manifest with upload status

**Requirements for Upload**:

- `classified == true`
- `containing_children_voice == true`
- `file_available == true`
- `uploaded == false`

### Batch Processing Cycle

The system uses an iterative batch processing model:

1. Phase 1 collects URLs in batches of 20
2. Each batch triggers phases 2-5, with manifest cleaning after each phase
3. After each batch, manifest is updated, backed up, and cleaned
4. At the end of Phase 1, a final batch processes any remaining URLs
5. Final manifest cleaning occurs after all processing completes

**Benefit**: Allows processing of large URL collections without memory explosion while maintaining data integrity

---

## Module Directory Structure

### Top-Level Files

```
src/
├── main.py              # Workflow orchestrator and entry point
├── config.py            # Configuration system
├── constants.py         # Global constants
├── models/              # Data structures
├── crawler/             # Phase 1: Video Discovery
├── downloader/          # Phase 2: Audio Download
├── analyzer/            # Phase 3: Analysis
├── filterer/            # Phase 4: Filtering
├── uploader/            # Phase 5: Upload
├── cleaner/             # Phase 0: Manifest Cleaning
└── utils/               # Shared utilities
```

### Module Breakdown

#### 1. **Crawler Module** (`src/crawler/`)

**Responsibility**: Video discovery from YouTube

**Components**:

- `search_engine.py`: Orchestrates multi-query search
- `youtube_api.py`: YouTube Data API v3 client
- `search_phases.py`: Phase 1 implementation
- `run_discovery_phase.py`: Phase 1 entry point

**Key Algorithm - Search Engine**:

```python
FOR each query in config.search.queries:
  GET video results from YouTube API
  FOR each result:
    IF not in existing_urls:
      Add to discovered_urls.txt
      IF collected_count % 20 == 0:
        Trigger batch processing
```

**API Key Management**:

- Rotates through multiple API keys to distribute quota usage
- Implements exponential backoff for quota exceeded errors
- Tracks quota usage per key

#### 2. **Downloader Module** (`src/downloader/`)

**Responsibility**: Extract audio from videos

**Components**:

- `audio_downloader.py`: Download orchestration
- `download_phases.py`: Phase 2 implementation
- `run_download_phase.py`: Phase 2 entry point

**Download Strategy**:

1. **Primary Method**: yt-dlp for reliable audio extraction
2. **Fallback Method**: YouTube API assisted download if yt-dlp fails
3. **Format**: MP3 with standard bitrate (128-192 kbps)
4. **Metadata**: Preserves title and channel information

**Concurrency Model**:

- Uses asyncio for concurrent downloads
- Configurable max concurrent downloads (default: 4)
- Semaphore-based concurrency control

#### 3. **Analyzer Module** (`src/analyzer/`)

**Responsibility**: ML-based audio analysis

**Components**:

- `voice_classifier.py`: Children's voice detection model
- `language_detector.py`: Language identification
- `analysis_phases.py`: Phase 3 implementation
- `run_analysis_phase.py`: Phase 3 entry point

**Voice Classifier**:

- **Input**: Audio file (MP3)
- **Process**:
  - Chunk audio into 30-second segments (with 5-second overlap)
  - Extract MFCC features for each chunk
  - Run through PyTorch classification model
  - Average predictions across chunks
- **Output**: Confidence score (0.0-1.0) for children's voice
- **Threshold**: Default 0.5 (configurable)

**Language Detector**:

- **Languages Supported**: Vietnamese (vi), English (en), Other
- **Method**: Acoustic features + neural network
- **Output**: Language with confidence score

#### 4. **Filterer Module** (`src/filterer/`)

**Responsibility**: Content organization and quality filtering

**Components**:

- `filtering_phases.py`: Phase 4 implementation
- `run_filtering_phase.py`: Phase 4 entry point

**Filtering Operations**:

1. Move files to language-specific directories
   - `final_audio/vi/` for Vietnamese children's voice
   - `final_audio/en/` for English children's voice
   - `final_audio/unknown/` for children's voice with unknown language
   - `final_audio/unclassified/` for non-children's voice
2. Remove duplicate manifest entries
3. Verify file availability on disk
4. Update manifest classifications

**File Organization**:

```
final_audio/
├── vi/               # Vietnamese children's voice
├── en/               # English children's voice
├── unknown/          # Unknown language
└── unclassified/     # Non-children's voice or failed analysis
```

#### 5. **Uploader Module** (`src/uploader/`)

**Responsibility**: Upload classified files to server

**Components**:

- `upload_phases.py`: Phase 5 implementation
- `client.py`: Server communication client
- `server.py`: Mock server for testing
- `add_uploaded_false_manifest.py`, `add_uploaded_true_manifest.py`: Utilities

**Upload Process**:

1. Identify files meeting upload criteria
2. Create upload session on server
3. Send files in configurable batches
4. Update manifest with upload results

#### 6. **Cleaner Module** (`src/cleaner/`)

**Responsibility**: Manifest validation and cleanup

**Components**:

- `clean_phases.py`: Phase 0 implementation
- `clean_manifest.py`: Manifest validation and repair

**Cleaning Operations**:

1. Remove duplicate URLs
2. Validate manifest JSON structure
3. Repair corrupted records if possible
4. Consolidate duplicate manifest entries

#### 7. **Utils Module** (`src/utils/`)

**Responsibility**: Shared utilities across modules

**Components**:

- `output_manager.py`: Centralized logging
- `file_manager.py`: File system operations
- `progress_tracker.py`: Progress tracking

**Output Manager**:

- Multi-level logging (DEBUG, INFO, SUCCESS, WARNING, ERROR)
- Emoji-enhanced messages for clarity
- Optional file logging with timestamps
- Centralized singleton instance

**File Manager**:

- Cross-platform path handling
- Atomic file writes (prevents corruption)
- Automatic backup creation
- Directory creation with error handling

**Progress Tracker**:

- Multi-level progress (phases, batches, items)
- Performance metrics (success rate, timing)
- ETA calculation

---

## Data Models and Structures

### Core Data Models (`src/models/models.py`)

#### VideoMetadata

```python
@dataclass
class VideoMetadata:
    video_id: str                          # YouTube video ID
    title: str                             # Video title
    channel_id: str                        # Creator's channel ID
    channel_title: str                     # Creator's channel name
    description: str                       # Video description
    published_at: Optional[datetime]       # Publication date
    duration_seconds: Optional[float]      # Duration in seconds
    view_count: int                        # View count
    like_count: int                        # Like count
    comment_count: int                     # Comment count
    thumbnail_url: Optional[str]           # Thumbnail URL
    tags: List[str]                        # Video tags
    source: VideoSource                    # Source (API, scraping, manual)
```

**Purpose**: Represents immutable YouTube video metadata
**Usage**: Created from YouTube API responses, serialized to JSON

#### Manifest Record Structure

```json
{
  "video_id": "dQw4w9WgXcQ",
  "title": "Example Video",
  "channel_id": "UCxxxxxx",
  "channel_title": "Example Channel",
  "audio_file_path": "output/final_audio/vi/exampleVideo.mp3",
  "downloaded": true,
  "download_timestamp": "2025-10-18T10:30:00Z",
  "download_error": null,
  "containing_children_voice": true,
  "voice_analysis_confidence": 0.87,
  "detected_language": "vi",
  "language_confidence": 0.92,
  "classified": true,
  "file_available": true,
  "uploaded": false,
  "upload_timestamp": null,
  "analysis_status": "completed"
}
```

**Manifest File**: `output/final_audio/manifest.json`
**Purpose**: Central record of all processed videos and their state

---

## Configuration System

### Configuration Architecture

The system uses a **hierarchical priority configuration model**:

```
1. Command-Line Arguments    (Highest Priority)
   ↓
2. JSON Configuration File
   ↓
3. Environment Variables
   ↓
4. Hardcoded Defaults       (Lowest Priority)
```

### Configuration Loading

```python
# In src/config.py
config = load_config(
    config_file="crawler_config.json",
    env_file=".env",
    cli_overrides={
        "queries": args.queries,
        "verbose": args.verbose
    }
)
```

### Configuration Classes

#### YouTubeAPIConfig

```python
api_keys: List[str]                    # API keys (rotated during use)
poll_interval_seconds: int = 300       # Polling delay
max_retries: int = 3                   # Retry attempts
retry_delays: List[int] = [1, 2, 4]    # Backoff delays (seconds)
min_request_interval: float = 0.1      # Min delay between requests
```

#### SearchConfig

```python
queries: List[str]                     # Search queries (from queries.txt)
target_videos_per_query: int = 500     # Videos per query
max_recommended_per_query: int = 100   # Max recommended
min_target_count: int = 1              # Min count
enable_channel_exploration: bool = True
max_similar_videos_per_channel: int = 10
```

#### DownloadConfig

```python
method: str = "api_assisted"           # "api_assisted" or "yt_dlp_only"
max_concurrent_downloads: int = 4      # Parallel downloads
timeout_seconds: int = 300             # Download timeout
batch_size: int = 1                    # Batch processing size
```

#### AnalysisConfig

```python
enabled: bool = True
child_voice_threshold: float = 0.5     # Classification threshold
language_confidence_threshold: float = 0.8
max_chunk_duration_seconds: int = 30   # Chunk size for analysis
chunk_overlap_seconds: int = 5         # Chunk overlap
```

#### FilteringConfig

```python
enabled: bool = True
remove_unclassified: bool = False      # Delete non-children files
```

#### CleaningConfig

```python
enabled: bool = True
remove_duplicates: bool = True         # Remove duplicate URLs
```

#### OutputConfig

```python
base_dir: Path = Path("output")
url_outputs_dir: Path = Path("output/url_outputs")
audio_outputs_dir: Path = Path("output/audio_outputs")
final_audio_dir: Path = Path("output/final_audio")
# + backup directories
```

### Queries File

**Location**: `queries.txt` in project root

**Format**: One query per line, UTF-8 encoded

**Default Queries** (if file doesn't exist):

```
bé giới thiệu bản thân
bé tập nói tiếng Việt
trẻ em kể chuyện
bé hát ca dao
em bé học nói
trẻ con nói chuyện
bé đọc thơ
```

---

## Error Handling and Resilience

### Error Recovery Strategy

#### 1. Circuit Breaker Pattern

When a component fails repeatedly:

```python
IF consecutive_failures > max_retries:
  Disable component
  Log error with context
  Continue processing with fallback
ELSE:
  Retry with exponential backoff
```

#### 2. Exponential Backoff

For transient failures (network, API quota):

```python
delay = base_delay * (2 ^ retry_count) + random_jitter
wait(delay)
retry()
```

Default retry delays: [1s, 2s, 4s]

#### 3. Partial Success Handling

When processing batches:

```python
FOR each item in batch:
  TRY:
    Process item
  CATCH Exception:
    Log error with item context
    Continue with next item
Continue with successful items
```

#### 4. State Persistence

Progress is saved after each phase:

```
After Phase 0: Manifest cleaned and validated
After Phase 1: URLs saved to file, manifest cleaned
After Phase 2: Manifest updated with download status, manifest cleaned
After Phase 3: Manifest updated with analysis results, manifest cleaned
After Phase 4: Files organized, manifest updated, manifest cleaned
After Phase 5: Upload status recorded, manifest cleaned
```

Enables resumable operations even after system crashes.

#### 5. Data Integrity

**Atomic File Operations**:

```python
def atomic_write_json(path, data):
  temp_file = tempfile.NamedTemporaryFile(...)
  json.dump(data, temp_file)
  temp_file.replace(path)  # Atomic on most filesystems
```

**Automatic Backups**:

- Before overwriting files, backup is created
- Format: `{filename}_backup_{timestamp}.{ext}`
- Stored in parallel `backups/` directory

**Validation Checks**:

- JSON files validated before use
- Corrupted files trigger recovery from backups
- Manifest records validated on load

### Failure Scenarios and Recovery

| Scenario             | Recovery                                    | Result                                   |
| -------------------- | ------------------------------------------- | ---------------------------------------- |
| API quota exceeded   | Rotate to next API key, exponential backoff | Continues processing                     |
| Download fails       | Logs error, continues with next URL         | File marked as unavailable               |
| Analysis model fails | Falls back to heuristic classification      | Continue with fallback scores            |
| Network timeout      | Retry with exponential backoff              | Eventually skips if max retries exceeded |
| Manifest corrupted   | Restore from backup                         | Resume from last valid state             |
| Upload failure       | Retry with backoff, mark for re-upload      | File remains unuploaded                  |

---

## Performance Characteristics

### Throughput

| Phase     | Throughput             | Bottleneck                    | Notes                       |
| --------- | ---------------------- | ----------------------------- | --------------------------- |
| Discovery | ~5-10 searches/minute  | API quota                     | Depends on API key limits   |
| Download  | 4 concurrent (default) | Bandwidth/YouTube rate limits | Configurable concurrency    |
| Analysis  | 1 file/30-60s          | ML model inference            | Depends on audio duration   |
| Filtering | 1000+ files/minute     | Disk I/O                      | Mostly in-memory operations |
| Upload    | 4 concurrent (default) | Network/Server bandwidth      | Configurable concurrency    |

### Memory Usage

- **Idle**: ~50-100 MB
- **During Phase 1**: +10-50 MB (URL buffer)
- **During Phase 2**: +200-500 MB (concurrent downloads)
- **During Phase 3**: +500-1000 MB (audio processing + ML models)
- **During Phase 4**: +100-200 MB (manifest in memory)

**Optimization**: Audio chunks processed in 30-second segments to limit memory during analysis

### Disk Usage

| Directory        | Size Growth         | Notes                           |
| ---------------- | ------------------- | ------------------------------- |
| `url_outputs/`   | ~1 MB per 1000 URLs | Metadata stored                 |
| `audio_outputs/` | ~5-10 MB per video  | Raw downloaded audio            |
| `final_audio/`   | ~3-8 MB per video   | Processed audio (lower quality) |
| `backups/`       | ~2x of originals    | Automatic backup storage        |

---

## Running the System

### Entry Point

The system can be run using either of these commands:

```bash
python -m src.main [OPTIONS]
# or
python src/main.py [OPTIONS]
```

### Command-Line Options

```
--config FILE              Configuration file (JSON)
--env-file FILE           Environment file (.env)
--queries QUERY [QUERY...] Override search queries
--max-videos N            Maximum videos to process
--output-dir PATH         Output directory
--verbose, -v             Enable verbose logging
--dry-run                 Validate config without running
--max-processed-urls N    Max URLs for phases 2-5
```

### Typical Execution

```bash
# Default configuration
python -m src.main

# Custom queries
python -m src.main --queries "toddler learning" "baby singing"

# Limit processing
python -m src.main --max-videos 100

# Validate config only
python -m src.main --dry-run
```

### Workflow Execution Example

```
Starting crawler with 7 queries

Phase 0: Manifest Cleaning
✅ Manifest cleaned and validated

Phase 1: Video Discovery
Processing query 1/7: "bé giới thiệu bản thân"
  Found 87 videos...
  [Batch 1] 20 URLs collected → Trigger phases 2-5
  [Batch 2] 40 URLs collected → Trigger phases 2-5
  ...continuing discovery...
Processing query 2/7: "bé tập nói tiếng Việt"
  ...

Phase 1 Complete: 3500 total URLs discovered

Final Batch Processing
Phase 2: Audio Download
  Downloaded 3487/3500 (99.6% success)

Phase 3: Audio Analysis
  Analyzed 3487 files
  Children's voice detected: 2156 files (61.8%)

Phase 4: Content Filtering
  Organized into:
    - Vietnamese: 1087
    - English: 234
    - Unknown: 835
    - Unclassified: 1166

Phase 5: File Upload
  Uploaded 1321 files to server

✅ Workflow Complete: 1321 children's voice files collected
```

---

## Key Design Principles

1. **Modular Independence**: Each phase can be tested/run independently
2. **Resilience First**: Failures don't cascade; partial success is acceptable
3. **Data Integrity**: Atomic operations and backups prevent data loss
4. **Async-First**: Non-blocking I/O for efficiency
5. **Configurability**: All key parameters can be tuned via config
6. **Observability**: Rich logging at every critical point
7. **Progressive Processing**: Batch-based streaming prevents resource exhaustion

---

## Troubleshooting Guide

### Common Issues

**"Cannot import modules"**

- Ensure running as module: `python -m src.main` or directly: `python src/main.py`
- Check PYTHONPATH includes project root

**"YouTube API quota exceeded"**

- Add more API keys to configuration
- Reduce `target_videos_per_query`
- Restart later (quota resets daily)

**"Files not downloading"**

- Check internet connection
- Verify YouTube can be accessed
- Try enabling cookies in configuration

**"Manifest corrupted"**

- System will automatically restore from backup
- Check `output/final_audio/backups/` for recovery options

**"Uploads failing"**

- Verify server is running and accessible
- Check network connectivity to upload server
- Ensure uploaded/ directory has write permissions

---

## Integration Points

### External Services

1. **YouTube Data API v3**: Video discovery and metadata
2. **yt-dlp**: Audio extraction
3. **librosa**: Audio feature extraction
4. **PyTorch**: ML model inference
5. **Upload Server**: File upload destination

### File Formats

- **URLs**: Plain text, one per line
- **Metadata**: JSON format
- **Manifests**: JSON with structured records
- **Audio**: MP3 format
- **Configuration**: JSON format

---

This document is the single source of truth for understanding the YouTube Children's Voice Crawler system. All functionality, architecture, and design decisions are documented here.
