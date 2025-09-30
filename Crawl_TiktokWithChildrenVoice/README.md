# TikTok Children's Voice Crawler

## Overview

AI-powered crawler that automatically searches, downloads, and analyzes TikTok videos to collect URLs of videos containing Vietnamese children's voices using machine learning models. Based on the proven architecture of the YouTube Children's Voice Crawler.

**Key Features:**

- **TikTok RapidAPI Integration** - Official API for fast, reliable video discovery and metadata
- **Advanced Audio Classification** - Vietnamese language + children's voice detection using ML models
- **Automated Configuration** - JSON-based configuration file for seamless operation
- **Comprehensive Logging** - Detailed logging of all operations with timestamps
- **Anti-Detection Measures** - Advanced techniques to avoid platform bot detection
- **Enhanced Error Handling** - Robust retry mechanisms and graceful degradation
- **Intelligent Processing** - Chunked audio analysis with early exit optimization

## Quick Start

### Prerequisites

- Python 3.8+
- Internet connection
- TikTok RapidAPI key (required)
- FFmpeg installed

### 1. Setup Environment

**Get TikTok RapidAPI Key:**

1. Go to [RapidAPI TikTok API](https://rapidapi.com/Sonjoy/api/tiktok-api23)
2. Subscribe to the API plan that fits your needs
3. Copy your API key

**Configure environment:**

1. Copy the example environment file:

   ```powershell
   # Windows PowerShell
   Copy-Item .env.example .env
   ```

2. Edit `.env` file and replace `your_tiktok_api_key_here` with your actual API key:

   ```
   TIKTOK_API_KEY=your_actual_api_key_here
   ```

3. Optional: Adjust other settings in `.env` as needed:
   - `MAX_WORKERS=4` (parallel processing threads)
   - `WHISPER_MODEL_SIZE=tiny` (tiny/base/small/medium/large)
   - `CHILD_THRESHOLD=0.5` (confidence threshold for children's voice)
   - `DEBUG_MODE=false` (enable detailed logging)

### 2. Install Dependencies

**Python packages:**

```powershell
# Windows/Mac/Linux
pip install -r requirements.txt
```

**Install FFmpeg:**

**Windows:**

```powershell
# Download from https://ffmpeg.org/download.html
# Extract to C:\ffmpeg and add C:\ffmpeg\bin to system PATH
```

**Mac:**

```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt update && sudo apt install ffmpeg
```

### 3. Verify Setup

```powershell
# Windows PowerShell
ffmpeg -version
Get-Content .env | Select-String "TIKTOK_API_KEY"
python -c "import torch, transformers, whisper; print('Dependencies OK')"
```

### 4. Run the Crawler

```powershell
# Windows PowerShell
python tiktok_video_crawler.py
```

The crawler will automatically:

- Load configuration from `crawler_config.json` (created on first run)
- Search TikTok using configured queries and usernames
- Download and analyze audio from each video
- Detect Vietnamese language and children's voices using ML
- Generate comprehensive reports and statistics
- Log all operations with timestamps for debugging

## Architecture

This crawler uses the same proven ML pipeline as the YouTube crawler:

```
TikTok RapidAPI → Video Discovery → Audio Download → Language Detection → Children's Voice Analysis → Results
```

**Core Components:**

1. **TikTok API Client** - Handles video discovery and metadata retrieval
2. **Audio Classifier** - ML-based age/gender classification (Wav2Vec2 + Whisper)
3. **Language Detector** - Vietnamese language detection
4. **Configuration Manager** - JSON-based automated configuration
5. **Output Manager** - Comprehensive reporting and statistics

## Configuration

The crawler uses a JSON configuration file (`crawler_config.json`) for automated operation. Key settings include:

- **Search Queries** - TikTok usernames and keywords to search
- **Target Video Count** - Number of videos to analyze per query
- **Classification Thresholds** - Confidence levels for children's voice detection
- **Debug Settings** - Logging verbosity and diagnostic options

## Enhanced Features

### 🔧 TikTok RapidAPI Integration

The crawler uses TikTok RapidAPI for reliable metadata retrieval:

- **Fast metadata access** - API provides structured data quickly
- **Rich video information** - Duration, statistics, download URLs
- **User profile support** - Can crawl specific TikTok accounts
- **Keyword search** - Flexible content discovery

### 📝 Comprehensive Logging

All operations are logged with detailed information:

- **Timestamped entries** - Every operation includes precise timestamps
- **Progress tracking** - Real-time progress updates during collection
- **Error reporting** - Detailed error messages with context
- **Performance metrics** - Timing and efficiency statistics

### 🛡️ Anti-Detection Features

Enhanced processing with multiple anti-detection measures:

- **User Agent Rotation** - Cycles through realistic browser user agents
- **Intelligent Rate Limiting** - Adaptive delays based on request patterns
- **Retry Logic** - Exponential backoff with random delays
- **Error Recovery** - Graceful handling of temporary failures

### 📁 Output Files

The crawler generates timestamped files:

```
tiktok_url_outputs/
├── YYYYMMDD_HHMMSS_collection_report.txt    # Video collection report
├── YYYYMMDD_HHMMSS_multi_query_collected_video_urls.txt
├── YYYYMMDD_HHMMSS_detailed_collection_results.json
├── YYYYMMDD_HHMMSS_query_efficiency_statistics.json
└── YYYYMMDD_HHMMSS_backup_collected_videos.txt
```

## Troubleshooting

### TikTok API Issues

If you encounter API issues:

1. **Check API key** - Ensure TIKTOK_API_KEY is set correctly
2. **Verify quota** - Check your RapidAPI dashboard for remaining requests
3. **Rate limiting** - Increase delays between requests if needed

### Audio Processing Issues

For audio processing problems:

1. **Check FFmpeg** - Ensure FFmpeg is properly installed
2. **Memory usage** - Reduce MAX_WORKERS if running out of memory
3. **Model loading** - First run downloads ML models (may take time)

### Configuration Issues

If the crawler fails to start:

1. **Check .env file** - Ensure TIKTOK_API_KEY is set correctly
2. **Verify config file** - Check `crawler_config.json` syntax
3. **File permissions** - Ensure write access to output directory
4. **Dependencies** - Verify all packages are installed correctly

## Performance Tips

1. **Use multiple API keys** - Set up multiple RapidAPI accounts for higher quota
2. **Optimize model size** - Use 'tiny' Whisper model for faster processing
3. **Adjust workers** - Tune MAX_WORKERS based on your hardware
4. **Filter content** - Use specific users/keywords to reduce processing load

## Security Considerations

1. **API Key Protection** - Keep TikTok API key secure and private
2. **Rate Limiting** - Respect TikTok's and RapidAPI's terms of service
3. **User Agent Honesty** - Use realistic, non-deceptive user agents
4. **Data Privacy** - Handle video metadata responsibly

## Comparison with YouTube Crawler

| Feature            | YouTube Crawler     | TikTok Crawler       |
| ------------------ | ------------------- | -------------------- |
| API Source         | YouTube Data API v3 | TikTok RapidAPI      |
| Audio Analysis     | Wav2Vec2 + Whisper  | Wav2Vec2 + Whisper   |
| Language Detection | YouTube Transcripts | Audio-based          |
| Content Discovery  | Search queries      | Keywords + Users     |
| Video Length       | Variable (chunking) | Short-form optimized |

## Background Execution

The crawler can run in the background with automated configuration:

### Windows (PowerShell)

```powershell
Start-Process python -ArgumentList "tiktok_video_crawler.py" -WindowStyle Hidden
```

### Linux/Mac

```bash
nohup python tiktok_video_crawler.py > crawler.log 2>&1 &
```

---

**Note**: This crawler is designed for research and educational purposes. Always comply with TikTok's Terms of Service and applicable laws regarding content crawling and analysis.
