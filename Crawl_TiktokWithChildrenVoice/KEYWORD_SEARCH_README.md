# TikTok Keyword Search Implementation

This document describes the implementation of keyword search functionality for the TikTok Children's Voice Crawler project.

## Overview

The keyword search functionality allows the crawler to search for TikTok videos using Vietnamese keywords and phrases related to children's content. This is one of two search methods supported by the crawler:

1. **Channel Queries** - Search by TikTok username
2. **Keyword Queries** - Search by general keywords/phrases (e.g., "trẻ em việt nam")

## Implementation Details

### API Endpoint

The implementation uses TikTok's video search API endpoint:

```
https://tiktok-api23.p.rapidapi.com/api/search/video
```

### Parameters

- `keyword` - The search term (URL encoded)
- `cursor` - Pagination cursor (starts at 0)
- `search_id` - Search session ID (default: 0)

### Code Structure

#### 1. TikTokAPIClient.search_videos_by_keyword()

Located in `tiktok_api_client.py`, this method handles single keyword search requests:

```python
def search_videos_by_keyword(self, keyword: str, count: int = 30, cursor: int = 0, search_id: int = 0) -> List[Dict]:
```

**Features:**

- URL encoding for Vietnamese characters and special characters
- Proper error handling and retry logic
- Response parsing for TikTok's video search format
- Detailed logging for debugging

#### 2. TikTokAPIClient.search_videos_by_keyword_with_pagination()

Enhanced method for collecting larger numbers of videos across multiple API calls:

```python
def search_videos_by_keyword_with_pagination(self, keyword: str, total_count: int = 100) -> List[Dict]:
```

**Features:**

- Automatic pagination to fetch more than 50 videos
- Rate limiting between requests
- Intelligent stopping when no more results are available

#### 3. TikTokVideoCollector.collect_videos_from_keyword()

Located in `tiktok_video_crawler.py`, this method integrates keyword search into the main crawler:

```python
def collect_videos_from_keyword(self, keyword: str, max_videos: int) -> List[Dict]:
```

**Features:**

- Chooses between single request and paginated search based on video count
- Applies video filters (duration, views, content)
- Integrates with the crawler's progress tracking

## Configuration

### Keyword Queries in crawler_config.json

The crawler configuration includes a `keyword_queries` array with Vietnamese keywords:

```json
{
  "keyword_queries": [
    "bé tập đếm",
    "bé tập đọc",
    "trẻ em hát",
    "bé học nói",
    "thiếu nhi việt nam",
    "đồng dao việt nam"
  ]
}
```

### Vietnamese Keywords Categories

The current configuration includes keywords in these categories:

1. **Learning Activities**

   - "bé tập đếm" (baby learning to count)
   - "bé tập đọc" (baby learning to read)
   - "bé học nói" (baby learning to speak)

2. **Musical Content**

   - "trẻ em hát" (children singing)
   - "đồng dao việt nam" (Vietnamese nursery rhymes)

3. **General Children's Content**

   - "thiếu nhi việt nam" (Vietnamese children)
   - "trẻ em việt" (Vietnamese kids)

4. **Educational Content**
   - "bé học abc" (baby learning ABC)
   - "trẻ học chữ" (children learning letters)

## Usage Examples

### Basic Usage

```python
from tiktok_api_client import TikTokAPIClient

# Initialize client
client = TikTokAPIClient()

# Search for videos
videos = client.search_videos_by_keyword("trẻ em việt nam", count=10)

for video in videos:
    print(f"Title: {video['title']}")
    print(f"Author: @{video['author_username']}")
    print(f"URL: {video['url']}")
```

### Paginated Search

```python
# Get more videos with automatic pagination
videos = client.search_videos_by_keyword_with_pagination("thiếu nhi", total_count=100)
print(f"Found {len(videos)} videos total")
```

### Integration with Crawler

```python
from tiktok_video_crawler import TikTokVideoCollector

# Initialize crawler
collector = TikTokVideoCollector()

# Collect videos from keyword (with analysis)
videos = collector.collect_videos_from_keyword("bé học nói", max_videos=50)
print(f"Collected {len(videos)} qualifying videos")
```

## Testing

### Test Script

Run the test script to verify functionality:

```bash
python test_keyword_search.py
```

The test script will:

1. Test basic keyword search with multiple Vietnamese keywords
2. Test pagination functionality
3. Verify API connectivity and configuration
4. Show detailed results and statistics

### Manual Testing

Test individual keywords using the API client directly:

```bash
python tiktok_api_client.py
```

This will run the built-in test suite that includes keyword search tests.

## Error Handling

The implementation includes comprehensive error handling:

1. **Network Errors** - Retry logic with exponential backoff
2. **API Rate Limits** - Automatic rate limiting and retry after rate limit reset
3. **Invalid Keywords** - Graceful handling of keywords that return no results
4. **Quota Exceeded** - API key rotation when available
5. **Malformed Responses** - Proper error logging and fallback behavior

## Performance Considerations

### Rate Limiting

- Minimum 1-3 second delay between API requests
- Configurable in `crawler_config.json` under `rate_limiting`

### Pagination Efficiency

- Requests 50 videos per API call (TikTok's typical maximum)
- Stops automatically when no more results are available
- Avoids unnecessary API calls for small result sets

### Memory Usage

- Videos are processed immediately rather than stored in large batches
- Temporary audio files are cleaned up after analysis
- Results are streamed to output files to avoid memory buildup

## Vietnamese Language Support

### Character Encoding

- Full UTF-8 support for Vietnamese characters
- Proper URL encoding for API requests
- Diacritical marks preserved in search terms

### Keyword Optimization

Keywords are optimized for Vietnamese TikTok content:

- Regional variations (Northern, Central, Southern Vietnamese)
- Common educational terms used by Vietnamese families

## Integration with Audio Analysis

Keyword search results are automatically fed into the audio analysis pipeline:

1. **Language Detection** - Verifies content is Vietnamese
2. **Children's Voice Detection** - Uses ML models to identify children's voices
3. **Quality Filtering** - Applies duration, view count, and content filters
4. **Channel Discovery** - Identifies promising channels for future crawling

## Troubleshooting

### Common Issues

1. **No Results Found**

   - Verify API key is valid and has quota
   - Try broader keywords (e.g., "trẻ em" instead of specific phrases)
   - Check if TikTok API service is accessible

2. **Rate Limit Errors**

   - Increase delay between requests in configuration
   - Verify API key quotas in RapidAPI dashboard
   - Consider using multiple API keys for rotation

3. **Invalid Response Format**
   - Check if TikTok API has updated response format
   - Verify endpoint URL is correct
   - Enable debug mode for detailed response logging

### Debug Mode

Enable debug mode in `crawler_config.json`:

```json
{
  "debug_mode": true
}
```

This will show detailed API requests, responses, and processing steps.

## Future Enhancements

### Planned Improvements

1. **Smart Keyword Expansion** - Automatically generate related keywords
2. **Trending Keywords** - Dynamically identify popular Vietnamese children's content terms
3. **Location-Based Search** - Target specific Vietnamese regions
4. **Semantic Search** - Use AI to find conceptually similar content
5. **Real-time Keyword Monitoring** - Track new trending children's content

### Configuration Improvements

1. **Keyword Categories** - Organize keywords by content type
2. **Priority Levels** - Search high-priority keywords first
3. **Success Rate Tracking** - Automatically remove ineffective keywords
4. **A/B Testing** - Compare keyword performance over time

## API Documentation Reference

For complete API documentation, see:

- [TikTok API23 on RapidAPI](https://rapidapi.com/Lundehund/api/tiktok-api23/)
- [Search Videos Endpoint](https://rapidapi.com/Lundehub/api/tiktok-api23/playground/apiendpoint_f2baa156-0f92-4b32-9314-b8a61b026575)

## Support

For issues or questions about the keyword search implementation:

1. Check the test script output for specific error messages
2. Verify API configuration and connectivity
3. Review the debug logs for detailed error information
4. Ensure Vietnamese keywords are properly encoded
