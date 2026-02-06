

# YouTube Video Fetcher API

This API provides functionality to fetch videos from YouTube playlists and channels using RapidAPI.

## Core Functions

### 1. `get_youtube_playlist_videos(request)`
Main HTTP endpoint function that handles playlist video requests.

**Input:**
```
GET /?url={playlist_url}
```
**Supported URL formats:**
- `https://www.youtube.com/playlist?list=PLxxxxxx`
- `https://www.youtube.com/watch?v=VIDEO_ID&list=PLxxxxxx`
- `https://youtu.be/VIDEO_ID?list=PLxxxxxx`

**Example:**
```bash
curl -X GET "https://your-function-url/?url=https://www.youtube.com/playlist?list=PLxxxxxx"
```

**Response:**
```
https://www.youtube.com/watch?v=video1
https://www.youtube.com/watch?v=video2
...
```

### 2. `extract_playlist_id(url)`
Helper function that extracts playlist ID from various YouTube URL formats.

**Input:** YouTube URL string
**Output:** Playlist ID or None

**Supported URL patterns:**
```python
patterns = [
    r'[?&]list=([A-Za-z0-9_-]{2,34})',  # Standard watch URL
    r'youtube\.com/playlist\?list=([A-Za-z0-9_-]{2,34})',  # Playlist URL
    r'youtu\.be/[A-Za-z0-9_-]+\?list=([A-Za-z0-9_-]{2,34})',  # Short URL
    # ... other patterns
]
```

**Example usage:**
```python
url = "https://www.youtube.com/playlist?list=PLxxxxxx"
playlist_id = extract_playlist_id(url)  # Returns: "PLxxxxxx"
```

### 3. `get_playlist_videos(playlist_id)`
RapidAPI handler that fetches actual video data.

**Input:** Playlist ID string
**Output:** List of video URLs

**Example:**
```python
playlist_id = "PLxxxxxx"
videos = get_playlist_videos(playlist_id)
# Returns: ["https://www.youtube.com/watch?v=video1", ...]
```

## Setup

### Prerequisites
- Python 3.7+
- Google Cloud Functions environment
- RapidAPI account and key

### Environment Variables
```bash
RAPID_API_KEY=your_api_key_here
```

### Dependencies
```
functions-framework==3.*
flask==2.*
requests==2.*
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-repo/youtube-video-fetcher.git
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export RAPID_API_KEY=your_api_key_here
```

## Usage Examples

### Getting Playlist Videos
```python
# Using curl
curl -X GET "https://your-function-url/?url=https://www.youtube.com/playlist?list=PLxxxxxx"

# Using Python requests
import requests

url = "https://your-function-url/"
params = {
    "url": "https://www.youtube.com/playlist?list=PLxxxxxx"
}
response = requests.get(url, params=params)
videos = response.text.split('\n')
```

### Error Handling
The API returns different status codes based on the situation:
- 200: Success
- 400: Invalid input
- 404: No videos found
- 405: Method not allowed
- 500: Server error

Example error response:
```json
{
    "error": "Invalid playlist URL",
    "status": 400
}
```

## Limitations
- RapidAPI rate limits apply
- Maximum number of videos per playlist may be limited
- Some private or restricted videos might not be accessible

## Contributing
Feel free to submit issues and enhancement requests!

1. Fork the repo
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License
[MIT License](LICENSE)

## Contact
Your Name - your.email@example.com
Project Link: [https://github.com/your-repo/youtube-video-fetcher](https://github.com/your-repo/youtube-video-fetcher)

## Acknowledgments
- YouTube Data API
- RapidAPI
- Google Cloud Functions

===================

Phân biệt 2 hàm: `get_youtube_playlist_videos` và `get_playlist_videos`

Tôi sẽ giải thích sự khác nhau giữa các hàm này bằng tiếng Việt:

1. `get_youtube_playlist_videos`:
- Đây là hàm xử lý HTTP chính (được đánh dấu bằng `@functions_framework.http`)
- Xử lý toàn bộ quy trình request/response HTTP
- Xử lý tham số URL và xử lý lỗi
- **Gọi** hai hàm phụ trợ bên trong: `extract_playlist_id` và `get_playlist_videos`

```python
@functions_framework.http
def get_youtube_playlist_videos(request: Request):
    # Xử lý request HTTP
    # Kiểm tra đầu vào
    # Lấy URL playlist từ request
    playlist_id = extract_playlist_id(url)  # Gọi hàm phụ trợ 1
    video_urls = get_playlist_videos(playlist_id)  # Gọi hàm phụ trợ 2
    # Trả về response HTTP
```

2. `get_playlist_videos`:
- Đây là hàm phụ trợ
- Chỉ xử lý việc gọi API đến RapidAPI
- Nhận vào playlist ID và trả về danh sách URL video
- Không xử lý HTTP request trực tiếp

```python
def get_playlist_videos(playlist_id):
    # Gọi API đến RapidAPI
    # Xử lý response
    # Trả về danh sách URL video
```

Luồng dữ liệu:
```
Request HTTP 
    → get_youtube_playlist_videos (như người phục vụ)
        → extract_playlist_id (lấy ID từ URL)
            → get_playlist_videos (lấy videos dùng ID)
                → Trả về danh sách video
```

Ví dụ sử dụng:
```python
# Sử dụng qua HTTP endpoint:
curl "https://your-function/get_youtube_playlist_videos?url=https://youtube.com/playlist?list=PLxxxx"

# Sử dụng get_playlist_videos trực tiếp trong code:
playlist_id = "PLxxxx"
videos = get_playlist_videos(playlist_id)
```

Để dễ hiểu, hãy tưởng tượng như một nhà hàng:
- `get_youtube_playlist_videos` giống như người phục vụ (tiếp nhận yêu cầu từ khách)
- `get_playlist_videos` giống như đầu bếp (thực hiện công việc chính)
- Người phục vụ nhận order từ khách và chuyển cho đầu bếp
- Đầu bếp nấu món ăn và đưa lại cho người phục vụ
- Người phục vụ mang món ăn ra cho khách

Tóm lại:
1. `get_youtube_playlist_videos`: Là "người phục vụ" - xử lý yêu cầu từ người dùng
2. `get_playlist_videos`: Là "đầu bếp" - thực hiện công việc chính (lấy video từ API)

Hai hàm này làm việc cùng nhau để hoàn thành một quy trình hoàn chỉnh từ khi nhận yêu cầu đến khi trả kết quả cho người dùng.
