# YouTube Video Crawler - Configuration Guide

The YouTube Video Crawler now supports automated operation through a JSON configuration file, eliminating the need for manual input during runtime. It also includes enhanced cookie support for better YouTube access.

## Configuration File

The script automatically looks for `crawler_config.json` in the same directory as the script. If the file doesn't exist, it will be created with default values on the first run.

### Configuration File Structure

```json
{
  "debug_mode": false,
  "target_videos_per_query": 20,
  "max_recommended_per_query": 100,
  "min_target_count": 1,
  "download_method": "api_assisted",
  "cookie_settings": {
    "enabled": false,
    "method": "browser",
    "browser_name": "chrome",
    "cookies_file_path": "cookies.txt",
    "description": "Cookie configuration for YouTube access. Set enabled to true to use cookies. Method can be 'browser' (uses browser cookies) or 'file' (uses cookies.txt file). For browser method, specify browser_name (chrome, firefox, safari, edge, opera, brave). For file method, specify cookies_file_path."
  },
  "description": "Configuration file for YouTube Video Crawler. Set debug_mode to true for detailed logging, adjust target_videos_per_query for collection size, set download_method to 'api_assisted' (recommended) or 'yt_dlp_only', and configure cookie_settings for enhanced access to YouTube content. Search queries are loaded from queries.txt file."
}
```

### Configuration Parameters

| Parameter                   | Type    | Description                                           | Default                  |
| --------------------------- | ------- | ----------------------------------------------------- | ------------------------ |
| `debug_mode`                | boolean | Enable detailed debug logging                         | `false`                  |
| `target_videos_per_query`   | integer | Number of videos to collect per search query          | `20`                     |
| `max_recommended_per_query` | integer | Maximum recommended videos per query (for validation) | `100`                    |
| `min_target_count`          | integer | Minimum target count validation                       | `1`                      |
| `download_method`           | string  | Download method: "api_assisted" or "yt_dlp_only"      | `"api_assisted"`         |
| `cookie_settings`           | object  | Cookie configuration for YouTube access               | See cookie section below |

### Cookie Configuration

The `cookie_settings` object allows you to configure YouTube access using cookies, which can help bypass age restrictions and reduce bot detection:

```json
"cookie_settings": {
  "enabled": false,
  "method": "browser",
  "browser_name": "chrome",
  "cookies_file_path": "cookies.txt"
}
```

#### Cookie Settings Parameters

| Parameter           | Type    | Description                        | Default         |
| ------------------- | ------- | ---------------------------------- | --------------- |
| `enabled`           | boolean | Enable cookie support              | `false`         |
| `method`            | string  | Cookie method: "browser" or "file" | `"browser"`     |
| `browser_name`      | string  | Browser name for cookie extraction | `"chrome"`      |
| `cookies_file_path` | string  | Path to cookies.txt file           | `"cookies.txt"` |

#### Supported Browsers

When using the "browser" method, the following browsers are supported:

- `chrome`
- `firefox`
- `safari`
- `edge`
- `opera`
- `brave`

## Cookie Setup Guide

### Method 1: Browser Cookies (Recommended)

This method automatically extracts cookies from your browser:

1. **Log into YouTube** in your preferred browser
2. **Configure the crawler** to use browser cookies:

```json
"cookie_settings": {
  "enabled": true,
  "method": "browser",
  "browser_name": "chrome"
}
```

3. **Run the crawler** - it will automatically extract cookies from your browser

### Method 2: Cookies File

This method uses a Netscape format cookies file:

1. **Install a browser extension** to export cookies:

   - **Chrome/Firefox**: "Get cookies.txt" extension
   - **Firefox**: "Cookie Quick Manager" extension
   - **Chrome**: "EditThisCookie" extension

2. **Export cookies from YouTube**:

   - Go to YouTube and log in
   - Use the extension to export cookies
   - Save as `cookies.txt` in your project directory

3. **Configure the crawler**:

```json
"cookie_settings": {
  "enabled": true,
  "method": "file",
  "cookies_file_path": "cookies.txt"
}
```

### Creating Cookies File Manually

If you prefer to create the cookies file manually:

1. **Log into YouTube** in your browser
2. **Open Developer Tools** (F12)
3. **Go to Application/Storage tab** → Cookies → youtube.com
4. **Copy the cookie values** and create a file with this format:

```
# Netscape HTTP Cookie File
# https://curl.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.

.youtube.com	TRUE	/	TRUE	1735689600	VISITOR_INFO1_LIVE	your_cookie_value_here
.youtube.com	TRUE	/	TRUE	1735689600	LOGIN_INFO	your_cookie_value_here
.youtube.com	TRUE	/	TRUE	1735689600	SID	your_cookie_value_here
.youtube.com	TRUE	/	TRUE	1735689600	HSID	your_cookie_value_here
.youtube.com	TRUE	/	TRUE	1735689600	SSID	your_cookie_value_here
.youtube.com	TRUE	/	TRUE	1735689600	APISID	your_cookie_value_here
.youtube.com	TRUE	/	TRUE	1735689600	SAPISID	your_cookie_value_here
.youtube.com	TRUE	/	TRUE	1735689600	__Secure-1PSID	your_cookie_value_here
.youtube.com	TRUE	/	TRUE	1735689600	__Secure-3PSID	your_cookie_value_here
.youtube.com	TRUE	/	TRUE	1735689600	__Secure-1PAPISID	your_cookie_value_here
.youtube.com	TRUE	/	TRUE	1735689600	__Secure-3PAPISID	your_cookie_value_here
```

### Cookie Configuration Examples

#### Using Chrome Browser Cookies

```json
"cookie_settings": {
  "enabled": true,
  "method": "browser",
  "browser_name": "chrome"
}
```

#### Using Firefox Browser Cookies

```json
"cookie_settings": {
  "enabled": true,
  "method": "browser",
  "browser_name": "firefox"
}
```

#### Using Cookies File

```json
"cookie_settings": {
  "enabled": true,
  "method": "file",
  "cookies_file_path": "my_cookies.txt"
}
```

#### Disabling Cookies

```json
"cookie_settings": {
  "enabled": false
}
```

## Using Cookies with Other Scripts

### YouTube Audio Downloader

```bash
# Using browser cookies
python youtube_audio_downloader.py --cookies-browser chrome https://youtube.com/watch?v=...

# Using cookies file
python youtube_audio_downloader.py --cookies-file cookies.txt https://youtube.com/watch?v=...
```

### YouTube Audio Classifier

```bash
# Using browser cookies
python youtube_audio_classifier.py --cookies-browser chrome

# Using cookies file
python youtube_audio_classifier.py --cookies-file cookies.txt
```

### Environment Variables

You can also set environment variables:

```bash
# For cookies file
export YOUTUBE_COOKIES_FILE="cookies.txt"

# For browser cookies
export YOUTUBE_COOKIES_BROWSER="chrome"
```

## Benefits of Using Cookies

- **Bypass Age Restrictions**: Access age-restricted content
- **Reduce Bot Detection**: More reliable downloads with authenticated requests
- **Access Private Content**: Download from private/unlisted videos (if you have access)
- **Better Success Rate**: More reliable downloads with proper authentication
- **Avoid Rate Limiting**: Reduce the likelihood of being blocked by YouTube

## Security Considerations

- **Keep cookies secure**: Don't share your cookies file publicly
- **Regular updates**: Cookies expire, so update them periodically
- **Browser security**: Only use cookies from browsers you trust
- **File permissions**: Ensure cookies.txt has appropriate file permissions

## Troubleshooting

### Common Cookie Issues

1. **"Cookies not found" error**:

   - Ensure you're logged into YouTube in the specified browser
   - Check that the browser name is correct
   - Try using a different browser

2. **"Invalid cookies file" error**:

   - Ensure the cookies file is in Netscape format
   - Check that the file path is correct
   - Verify the file contains valid YouTube cookies

3. **"Bot detection still triggered" error**:
   - Try using a different browser for cookies
   - Update your cookies (they may have expired)
   - Consider using a cookies file instead of browser extraction

### Cookie File Format Validation

A valid cookies.txt file should:

- Start with a comment line: `# Netscape HTTP Cookie File`
- Contain tab-separated fields
- Include YouTube domain cookies
- Have valid expiration dates

## Required Parameters

The following parameters are required and must be present in the configuration file:

- `debug_mode`
- `target_videos_per_query`

Optional parameters will use default values if not specified. Search queries are loaded from the `queries.txt` file in the project root.

## Running the Script

### Automated Mode (No User Input)

Simply run the script without any arguments:

```bash
python src/main.py
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

### High-Volume Collection with Cookies

```json
{
  "debug_mode": false,
  "target_videos_per_query": 50,
  "cookie_settings": {
    "enabled": true,
    "method": "browser",
    "browser_name": "chrome"
  }
}
```

### Debug Mode for Development

```json
{
  "debug_mode": true,
  "target_videos_per_query": 5,
  "cookie_settings": {
    "enabled": true,
    "method": "file",
    "cookies_file_path": "cookies.txt"
  }
}
```

### Custom Search Queries

Search queries are loaded from the `queries.txt` file in the project root directory. Each line in the file represents one search query. To modify the search queries:

1. Open `queries.txt` in a text editor
2. Add or modify queries (one per line)
3. Save the file
4. Restart the crawler

Example `queries.txt` content:

```
trẻ em học tiếng Anh
bé học đếm số
con nít học chữ cái
em bé hát đồng dao
trẻ con kể chuyện cổ tích
bé giới thiệu bản thân
bé tập nói tiếng Việt
```

**Note**: Empty lines and lines starting with `#` are ignored. The system will automatically load queries from this file when it starts.

## Background Execution

Since the script no longer requires user input, it can be run in the background:

### Windows (PowerShell)

```powershell
Start-Process python -ArgumentList "src/main.py" -WindowStyle Hidden
```

### Linux/Mac

```bash
nohup python src/main.py > crawler.log 2>&1 &
```

## Output Files

The script generates timestamped output files in the `output/url_outputs/` directory:

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
- Non-positive target video count
- Invalid cookie configuration
- Missing or empty `queries.txt` file

## Migration from Interactive Mode

If you previously used the interactive mode, simply create a configuration file with your preferred settings. The new system provides the same functionality without requiring manual input during execution.
