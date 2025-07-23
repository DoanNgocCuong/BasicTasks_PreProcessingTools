# YouTube Children's Voice Crawler

AI-powered system for collecting YouTube videos with Vietnamese children's voices using ML-based audio analysis.

## Setup

### Prerequisites

- Python 3.8+ (check with `python --version`)
- Git (for cloning)
- Internet connection (for model downloads)

### 1. Clone and navigate

```bash
git clone "https://github.com/DoanNgocCuong/BasicTasks_PreProcessingTools.git"
cd BasicTasks_PreProcessingTools/Crawl_YoutubeWithChildrenVoice
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Get YouTube Data API key

- Go to [Google Cloud Console](https://console.cloud.google.com/)
- Create new project or select existing one
- Enable "YouTube Data API v3" in APIs & Services
- Create credentials → API key
- Copy the API key

### 4. Set environment variable

```bash
# Windows PowerShell
$env:YOUTUBE_API_KEY="your_api_key_here"

# Windows Command Prompt
set YOUTUBE_API_KEY=your_api_key_here

# Linux/Mac
export YOUTUBE_API_KEY="your_api_key_here"
```

### 5. Install FFmpeg

**Windows:**

- Download from [FFmpeg.org](https://ffmpeg.org/download.html)
- Extract to folder (e.g., `C:\ffmpeg`)
- Add `C:\ffmpeg\bin` to system PATH

**Linux (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install ffmpeg
```

**Mac:**

```bash
brew install ffmpeg
```

### 6. Verify installation

```bash
# Test FFmpeg
ffmpeg -version

# Test environment variable
echo $YOUTUBE_API_KEY    # Linux/Mac
echo %YOUTUBE_API_KEY%   # Windows CMD
$env:YOUTUBE_API_KEY     # Windows PowerShell

# Test Python imports
python -c "import torch, transformers, whisper; print('ML dependencies OK')"
```

### 7. Create required directories (automatic)

The script will automatically create:

- `youtube_url_outputs/` - For collection results
- `youtube_audio_outputs/` - For temporary audio files

## Usage

```bash
# Main collection (interactive mode)
python youtube_video_crawler.py

# Validate URLs
python youtube_output_validator.py

# Test audio classifier
python youtube_audio_classifier.py
```

## How It Works

1. **Search**: YouTube API searches with configurable queries
2. **Download**: Convert videos to WAV using yt-dlp + FFmpeg
3. **Analyze**: ML models detect children's voice + Vietnamese language
4. **Explore**: Find similar content in promising channels
5. **Report**: Generate statistics and cleaned datasets

## Core Components

- `youtube_video_crawler.py` - Main orchestrator
- `youtube_audio_classifier.py` - ML audio analysis (wav2vec2 + Whisper)
- `youtube_audio_downloader.py` - YouTube to WAV conversion
- `youtube_output_analyzer.py` - Statistics and reporting
- `youtube_output_validator.py` - URL validation and deduplication

## Output Files

```
youtube_url_outputs/
├── collected_video_urls.txt           # Final URL list
├── detailed_collection_results.json   # Complete metadata
├── query_efficiency_statistics.json   # Performance metrics
└── backup_TIMESTAMP_*.txt             # Timestamped backups
```

## Configuration Examples

**Vietnamese search queries:**

```
bé giới thiệu bản thân    # Children introducing themselves
bé tập nói tiếng Việt     # Children learning Vietnamese
trẻ em kể chuyện          # Children telling stories
```

**Recommended settings:**

- Videos per query: 10-50
- Total target: 50-200
- Enable debug mode for detailed logging

## Key Dependencies

```
google-api-python-client  # YouTube API
yt-dlp                   # Video downloading
ffmpeg-python            # Audio conversion
torch + transformers     # ML models
openai-whisper          # Language detection
```

## Troubleshooting

- **API errors**: Check `echo $YOUTUBE_API_KEY` and Google Console quotas
- **FFmpeg errors**: Test with `ffmpeg -version`
- **Model issues**: Use `AudioClassifier.clear_model_cache()`

## Algorithm

1. Load existing URLs (prevent duplicates)
2. For each query: search → analyze audio → explore channels
3. Filter: Vietnamese language + children's voice
4. Track: reviewed channels, statistics, progress
5. Output: URLs + comprehensive reports
