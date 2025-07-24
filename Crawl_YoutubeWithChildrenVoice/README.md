# YouTube Children's Voice Crawler

## Overview

AI-powered crawler that automatically searches, downloads, and analyzes YouTube videos to collect URLs of videos containing Vietnamese children's voices using machine learning models.

## Instructions

### Prerequisites

- Python 3.8+
- Internet connection
- YouTube Data API v3 key

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

**Output Files:**

- `youtube_url_outputs/TIMESTAMP_multi_query_collected_video_urls.txt` - Final video URLs
- `youtube_url_outputs/detailed_collection_results.json` - Complete statistics
- `youtube_url_outputs/query_efficiency_statistics.json` - Performance metrics

The crawler will automatically:

- Search YouTube using your queries
- Download and analyze audio from each video
- Detect Vietnamese language and children's voices using ML
- Explore channels with promising content
- Generate comprehensive reports and statistics
