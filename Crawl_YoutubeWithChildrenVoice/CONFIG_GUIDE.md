# YouTube Video Crawler - Configuration Guide

The YouTube Video Crawler now supports automated operation through a JSON configuration file, eliminating the need for manual input during runtime.

## Configuration File

The script automatically looks for `crawler_config.json` in the same directory as the script. If the file doesn't exist, it will be created with default values on the first run.

### Configuration File Structure

```json
{
  "debug_mode": false,
  "target_videos_per_query": 20,
  "search_queries": [
    "bé giới thiệu bản thân",
    "bé tập nói tiếng Việt",
    "trẻ em kể chuyện",
    "bé hát ca dao",
    "em bé học nói",
    "trẻ con nói chuyện",
    "bé đọc thơ",
    "con nít kể chuyện"
  ],
  "max_recommended_per_query": 100,
  "min_target_count": 1,
  "description": "Configuration file for YouTube Video Crawler. Set debug_mode to true for detailed logging, adjust target_videos_per_query for collection size, and modify search_queries array to change what videos to search for."
}
```

### Configuration Parameters

| Parameter                   | Type             | Description                                           | Default                   |
| --------------------------- | ---------------- | ----------------------------------------------------- | ------------------------- |
| `debug_mode`                | boolean          | Enable detailed debug logging                         | `false`                   |
| `target_videos_per_query`   | integer          | Number of videos to collect per search query          | `20`                      |
| `search_queries`            | array of strings | List of YouTube search queries to use                 | See default queries above |
| `max_recommended_per_query` | integer          | Maximum recommended videos per query (for validation) | `100`                     |
| `min_target_count`          | integer          | Minimum target count validation                       | `1`                       |

### Required Parameters

The following parameters are required and must be present in the configuration file:

- `debug_mode`
- `target_videos_per_query`
- `search_queries`

Optional parameters will use default values if not specified.

## Running the Script

### Automated Mode (No User Input)

Simply run the script without any arguments:

```bash
python youtube_video_crawler.py
```

The script will:

1. Load configuration from `crawler_config.json`
2. Display the loaded configuration
3. Start video collection automatically
4. Save results with timestamps

### First Time Setup

If no configuration file exists, the script will:

1. Create a default `crawler_config.json` file
2. Display a message asking you to edit the configuration
3. Exit gracefully

After the file is created, edit it according to your needs and run the script again.

## Configuration Examples

### High-Volume Collection

```json
{
  "debug_mode": false,
  "target_videos_per_query": 50,
  "search_queries": [
    "bé giới thiệu bản thân",
    "trẻ em kể chuyện",
    "bé hát ca dao"
  ]
}
```

### Debug Mode for Development

```json
{
  "debug_mode": true,
  "target_videos_per_query": 5,
  "search_queries": ["bé giới thiệu bản thân"]
}
```

### Custom Search Queries

```json
{
  "debug_mode": false,
  "target_videos_per_query": 25,
  "search_queries": [
    "trẻ em học tiếng Anh",
    "bé học đếm số",
    "con nít học chữ cái",
    "em bé hát đồng dao",
    "trẻ con kể chuyện cổ tích"
  ]
}
```

## Background Execution

Since the script no longer requires user input, it can be run in the background:

### Windows (PowerShell)

```powershell
Start-Process python -ArgumentList "youtube_video_crawler.py" -WindowStyle Hidden
```

### Linux/Mac

```bash
nohup python youtube_video_crawler.py > crawler.log 2>&1 &
```

## Output Files

The script generates timestamped output files in the `youtube_url_outputs/` directory:

- `{timestamp}_multi_query_collected_video_urls.txt` - List of collected video URLs
- Various analysis and validation reports

## Error Handling

If the configuration file is invalid or missing required fields, the script will:

1. Display a clear error message
2. Indicate which fields are missing or invalid
3. Exit gracefully without running the collection

Common configuration errors:

- Missing required fields
- Invalid JSON syntax
- Empty search queries array
- Non-positive target video count

## Migration from Interactive Mode

If you previously used the interactive mode, simply create a configuration file with your preferred settings. The new system provides the same functionality without requiring manual input during execution.
