# YouTube Video Searcher for Children's Speech Data Collection

This script implements an algorithm to collect YouTube videos containing children's speech using the YouTube Data API v3.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get YouTube Data API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the YouTube Data API v3
4. Create credentials (API Key)
5. Copy your API key

### 3. Set Environment Variable

**Windows (PowerShell):**

```powershell
$env:YOUTUBE_API_KEY="your_api_key_here"
```

**Windows (Command Prompt):**

```cmd
set YOUTUBE_API_KEY=your_api_key_here
```

**Linux/Mac:**

```bash
export YOUTUBE_API_KEY="your_api_key_here"
```

## Usage

### Basic Usage

```python
python youtube-video-searcher.py
```

### Programmatic Usage

```python
from youtube_video_searcher import YouTubeVideoSearcher

# Initialize with your API key
searcher = YouTubeVideoSearcher("your_api_key_here")

# Collect videos
video_urls = searcher.collect_videos()

# Save results
searcher.save_results("output_urls.txt")
searcher.save_detailed_results("detailed_results.json")
```

### Customization

You can modify the following parameters in the `YouTubeVideoSearcher` class:

- `target_video_count`: Number of videos to collect (default: 50)
- `initial_query`: Search query (default: "bé giới thiệu bản thân")

## Algorithm Overview

The script follows this logic:

1. Search YouTube with initial query
2. For each video found:
   - Check if it contains children's voice (currently random for testing)
   - Check if the channel hasn't been reviewed before
   - If both conditions are met:
     - Add the video to collection
     - Search for similar videos in the same channel
     - Add those videos to collection
     - Mark channel as reviewed
3. Continue until target number of videos is collected

## Output Files

- `newly_crawled_youtube_video_urls.txt`: List of video URLs
- `collected_videos_detailed.json`: Detailed information including metadata

## Important Notes

- The `contains_children_voice()` function currently returns random True/False values
- This is marked as TODO and needs to be implemented with proper voice detection
- The script respects YouTube API quotas and includes error handling
- Videos are deduplicated to avoid collecting the same video multiple times

## API Quotas

Be aware of YouTube Data API v3 quotas:

- Default quota: 10,000 units per day
- Search operations cost 100 units each
- Monitor your usage in Google Cloud Console
