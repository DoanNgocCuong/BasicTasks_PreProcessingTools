# YouTube Children's Voice Crawler

## Overview

AI-powered crawler that automatically searches, downloads, and analyzes YouTube videos to collect URLs of videos containing Vietnamese children's voices using machine learning models.

**Enhanced Features:**

- **YouTube Data API Integration** - Official API for faster, more reliable metadata retrieval
- **Comprehensive Terminal Logging** - Complete timestamped logs of all operations
- **Anti-Detection Measures** - Advanced techniques to avoid YouTube bot detection
- **Enhanced Error Handling** - Robust retry mechanisms and graceful degradation

## Instructions

### Prerequisites

- Python 3.8+
- Internet connection
- YouTube Data API v3 key
- FFmpeg installed

### 1. Setup Environment

**Get YouTube API Key:**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project or select existing one
3. Enable "YouTube Data API v3" in APIs & Services
4. Create credentials → API key
5. Copy the API key

**Configure environment:**

1. Copy the example environment file:

   ```powershell
   # Windows PowerShell
   Copy-Item .env.example .env

   # Mac/Linux
   cp .env.example .env
   ```

2. Edit `.env` file and replace `your_youtube_api_key_here` with your actual API key:

   ```
   YOUTUBE_API_KEY=your_actual_api_key_here
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
# Using Homebrew
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt update
sudo apt install ffmpeg
```

**Linux (CentOS/RHEL):**

```bash
sudo yum install ffmpeg
# or for newer versions:
sudo dnf install ffmpeg
```

### 3. Verify Setup

```powershell
# Windows PowerShell
ffmpeg -version
Get-Content .env | Select-String "YOUTUBE_API_KEY"
python -c "import torch, transformers, whisper; print('Dependencies OK')"
```

```bash
# Mac/Linux
ffmpeg -version
grep "YOUTUBE_API_KEY" .env
python -c "import torch, transformers, whisper; print('Dependencies OK')"
```

### 4. Run the Crawler

```powershell
# Windows PowerShell
python youtube_video_crawler.py
```

```bash
# Mac/Linux
python youtube_video_crawler.py
# or if python3 is required:
python3 youtube_video_crawler.py
```

**Interactive Configuration:**

1. Choose debug mode (y/n)
2. Set target videos per query (recommended: 10-50)
3. Enter search queries (examples: "bé giới thiệu bản thân", "trẻ em kể chuyện")
4. Type "DONE" when finished adding queries

**Advanced Configuration (.env file):**

Modify `.env` file to customize behavior:

- `MAX_WORKERS=4` - Number of parallel processing threads
- `WHISPER_MODEL_SIZE=tiny` - Language detection model (tiny/base/small/medium/large)
- `CHILD_THRESHOLD=0.5` - Confidence threshold for children's voice detection
- `AGE_THRESHOLD=0.3` - Age threshold for classification (0.3 ≈ 30 years)
- `MAX_AUDIO_DURATION_SECONDS=300` - Skip videos longer than 5 minutes
- `DEBUG_MODE=true` - Enable detailed logging
- `AUDIO_QUALITY=medium` - Audio download quality (low/medium/high)

## Enhanced Features

### 🔧 YouTube Data API Integration

The crawler now prioritizes YouTube Data API v3 for metadata retrieval:

- **Faster metadata retrieval** - Official API is more reliable than scraping
- **Higher rate limits** - API has better quota management
- **Structured data** - Consistent, well-formatted metadata
- **Automatic fallback** - Falls back to yt-dlp if API unavailable

### 📝 Comprehensive Terminal Logging

All terminal output is automatically captured and saved:

- **Timestamped entries** - Every line includes precise timestamps
- **Complete capture** - Both stdout and stderr are logged
- **Automatic filename** - Uses format: `YYYYMMDD_HHMMSS_terminal_output.log`
- **Summary reports** - Generates statistics about the logging session

#### Example Log Format

```
[2025-07-29 10:30:45.123] [STDOUT] ✅ Video contains children's voice and channel is new
[2025-07-29 10:30:45.124] [STDOUT] 🔍 Searching for similar videos in channel 'Kids Channel'
[2025-07-29 10:30:45.856] [STDERR] ⚠️ Rate limiting: sleeping for 2.3 seconds...
```

### 🛡️ Anti-Detection Features

Enhanced downloader with multiple anti-detection measures:

- **User Agent Rotation** - Cycles through realistic browser user agents
- **Intelligent Rate Limiting** - Adaptive delays based on request patterns
- **Enhanced HTTP Headers** - Browser-like headers to avoid detection
- **Retry Logic** - Exponential backoff with random delays
- **Bot Detection Recovery** - Extended delays when detection triggered

### 📁 Output Files

The enhanced crawler generates timestamped files:

```
youtube_url_outputs/
├── YYYYMMDD_HHMMSS_terminal_output.log      # Complete terminal log
├── YYYYMMDD_HHMMSS_terminal_log_summary.txt # Log session summary
├── YYYYMMDD_HHMMSS_collection_report.txt    # Video collection report
├── YYYYMMDD_HHMMSS_multi_query_collected_video_urls.txt
├── YYYYMMDD_HHMMSS_detailed_collection_results.json
└── YYYYMMDD_HHMMSS_query_efficiency_statistics.json
```

## Performance Optimizations

### 1. Use YouTube Data API

- Set up API key for 10x faster metadata retrieval
- Reduces load on YouTube's video pages
- More reliable than web scraping

### 2. Batch Processing

- API supports up to 50 video IDs per request
- Reduces total API calls needed
- Faster overall processing

### 3. Intelligent Caching

- Reuses classifier models across videos
- Caches API responses
- Minimizes redundant operations

## Troubleshooting

### YouTube Bot Detection

If you encounter bot detection:

1. **Check delays** - Increase rate limiting intervals
2. **Reduce concurrency** - Lower `MAX_WORKERS` in config
3. **Verify user agents** - Ensure realistic user agent strings
4. **Review patterns** - Check for repetitive behavior

### API Quota Issues

For YouTube Data API quota management:

1. **Monitor usage** - Check Google Cloud Console
2. **Implement caching** - Store metadata to reduce API calls
3. **Batch requests** - Process multiple videos per API call
4. **Fallback gracefully** - Ensure yt-dlp fallback works

### Log File Issues

If logging fails:

1. **Check permissions** - Ensure write access to output directory
2. **Disk space** - Verify sufficient storage for log files
3. **File locks** - Close any open log files
4. **Encoding issues** - Ensure UTF-8 support

## Security Considerations

1. **API Key Protection** - Keep YouTube API key secure
2. **Rate Limiting** - Respect YouTube's terms of service
3. **User Agent Honesty** - Use realistic, non-deceptive user agents
4. **Data Privacy** - Handle video metadata responsibly

The crawler will automatically:

- Search YouTube using your queries
- Download and analyze audio from each video
- Detect Vietnamese language and children's voices using ML
- Explore channels with promising content
- Generate comprehensive reports and statistics
- Log all operations with timestamps for debugging
