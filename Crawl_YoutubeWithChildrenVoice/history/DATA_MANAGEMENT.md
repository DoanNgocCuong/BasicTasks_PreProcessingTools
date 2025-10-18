# Data Management Guide

This guide documents the current data organization and management structure of the YouTube Children's Voice Crawler system.

## Directory Structure

The system uses a clean, modular directory structure for organizing all data:

```
output/
├── url_outputs/           # URL output files and manifests
│   └── backups/           # Backup files for URL outputs
├── audio_outputs/         # Downloaded audio files
│   └── backups/           # Backup files for audio outputs
└── final_audio/           # Final processed audio files
    ├── manifest.json      # Main manifest file
    └── backups/           # Backup directory for all final_audio files
```

## Directory Descriptions

### URL Outputs (`output/url_outputs/`)

Contains all URL-related data and manifests:

- **Main files**: Video URLs, search results, and metadata
- **Manifests**: JSON files tracking collected video information
- **Backups**: Automatic backups of manifests and important URL data

### Audio Outputs (`output/audio_outputs/`)

Contains downloaded audio files:

- **Audio files**: Downloaded MP3/WAV files from YouTube videos
- **Metadata**: Associated metadata for downloaded audio
- **Backups**: Backup copies of audio files and metadata

### Final Audio (`output/final_audio/`)

Contains processed and finalized audio data:

- **Manifest**: `manifest.json` - Main manifest tracking all processed audio
- **Audio files**: Final processed audio files ready for use
- **Backups**: Backup directory containing all backup files for manifests and audio

## Backup System

The system automatically maintains separate backup directories for each data type:

### Automatic Backup Creation

- **Triggers**: Backups are created automatically when files are saved or updated
- **Naming**: `{filename}_backup_{timestamp}.{extension}`
- **Organization**: Each output directory has its own backup subdirectory
- **Retention**: Backups accumulate over time; old backups can be cleaned manually

### Backup Locations

- **URL data**: `output/url_outputs/backups/`
- **Audio downloads**: `output/audio_outputs/backups/`
- **Final audio**: `output/final_audio/backups/`

## Data Flow

### 1. Discovery Phase
- Search results saved to `output/url_outputs/`
- Manifests track discovered videos
- Automatic backups created for manifests

### 2. Download Phase
- Audio files downloaded to `output/audio_outputs/`
- Metadata and download logs maintained
- Backup copies created automatically

### 3. Processing Phase
- Final audio files stored in `output/final_audio/`
- Main manifest updated with processing results
- All changes backed up automatically

## File Management

### Automatic Directory Creation

The system automatically creates all necessary directories when initialized:

```python
config = CrawlerConfig()
config.create_output_dirs()  # Creates all output and backup directories
```

### Backup Management

Backups are created automatically by the file management system:

```python
fm = get_file_manager()
fm.save_json(manifest_path, data)  # Automatically creates backup if file exists
```

### Cleanup

Old backup files can be cleaned manually or through automated scripts. The system provides utilities for:

- Removing old backup files based on age
- Consolidating duplicate backups
- Freeing up disk space

## Configuration

### Output Directories

Output directories are configured in `config.py`:

```python
@dataclass
class OutputConfig:
    base_dir: Path = field(default_factory=lambda: Path("output"))
    url_outputs_dir: Path = field(default_factory=lambda: Path("output/url_outputs"))
    audio_outputs_dir: Path = field(default_factory=lambda: Path("output/audio_outputs"))
    final_audio_dir: Path = field(default_factory=lambda: Path("output/final_audio"))
    # Backup directories
    url_backups_dir: Path = field(default_factory=lambda: Path("output/url_outputs/backups"))
    audio_backups_dir: Path = field(default_factory=lambda: Path("output/audio_outputs/backups"))
    final_audio_backups_dir: Path = field(default_factory=lambda: Path("output/final_audio/backups"))
```

### Environment Variables

Output locations can be customized via environment variables:

```bash
export YOUTUBE_OUTPUT_DIR="/custom/path"
```

## Benefits of Current Structure

1. **Clean Organization**: Related files grouped by function and phase
2. **Modular Design**: Each processing phase has its own dedicated space
3. **Automatic Backups**: Built-in backup system prevents data loss
4. **Easy Maintenance**: Clear separation makes troubleshooting simple
5. **Scalable**: Structure supports future expansion and new features
6. **Standard Layout**: Follows common project organization patterns

## Monitoring and Maintenance

### Directory Monitoring

Regular checks should be performed on output directories:

```bash
# Check directory sizes
du -sh output/*/

# Check backup file counts
find output/ -name "*backup*" | wc -l

# Verify manifest integrity
python -c "import json; json.load(open('output/final_audio/manifest.json'))"
```

### Backup Maintenance

Regular backup maintenance helps manage disk usage:

```bash
# Remove backups older than 30 days
find output/ -name "*backup*" -mtime +30 -delete

# List backup files by size
find output/ -name "*backup*" -ls | sort -k7 -nr
```

This structure ensures reliable data management with automatic backups and clear organization throughout the YouTube Children's Voice Crawler system.
