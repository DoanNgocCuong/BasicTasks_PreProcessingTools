

# Báo Cáo: YouTube Transcript & Video Info API

## 1. Tổng Quan
API này cho phép lấy transcript (phụ đề), thông tin video và comments từ video YouTube thông qua Cloud Function.

## 2. Cách Cài Đặt & Chạy

### 2.1 Yêu Cầu Hệ Thống
```bash
# Dependencies chính
functions-framework==3.8.2
flask
requests
```

### 2.2 Cài Đặt
```bash
# Tạo và kích hoạt virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Cài đặt dependencies
pip install functions-framework==3.8.2 flask requests
```

### 2.3 Cấu Hình
```bash
# Thêm RAPID_API_KEY vào environment variables
export RAPID_API_KEY=your_rapid_api_key

# Hoặc tạo file .env
RAPID_API_KEY=090971f6bbmshb3be82863a6621dp1721d4jsn22096fb306a6
```

### 2.4 Chạy API
```bash
functions-framework --target=get_youtube_transcript --port=8080
```

Hoặc chạy trực tiếp bằng Module:
```bash
python -m functions_framework --target=get_youtube_transcript --port=8080
```

## 3. Cấu Trúc Code

### 3.1 Entry Point
```python
@functions_framework.http
def get_youtube_transcript(request):
    """
    Hàm chính xử lý HTTP requests
    - Validate API key
    - Lấy YouTube URL
    - Xử lý và trả về kết quả
    """
```

### 3.2 Các Hàm Chính

#### a) Xử Lý Video
```python
def extract_video_id(youtube_url):
    """Tách video ID từ YouTube URL"""

def get_video_details(video_id):
    """Lấy thông tin video từ RapidAPI"""
```

#### b) Xử Lý Transcript
```python
def get_transcript_from_subtitles(subtitle_url):
    """
    Lấy và xử lý transcript từ subtitle URL
    - Chuyển đổi thời gian
    - Format text
    - Giới hạn độ dài
    """
```

#### c) Xử Lý Comments
```python
def get_video_comments(video_id):
    """
    Lấy comments của video
    - Phân trang
    - Format comments
    - Chia nhỏ nếu quá dài
    """
```

## 4. API Endpoints

### 4.1 Get Video Transcript & Info
```bash
GET http://localhost:8080

Headers:
X-API-Key: yt2024_k8hj3n5m9p2q4w7r

Query Parameters:
youtube_url: URL của video YouTube
```

### 4.2 Response Format
```json
{
    "title": "Video Title",
    "description": "Video Description",
    "username": "Channel Handle",
    "transcript": "Video Transcript",
    "comments_count": 100,
    "comments_1": "Comment text part 1",
    "comments_2": "Comment text part 2"
}
```

## 5. Xử Lý Lỗi

```python
try:
    # Main processing
except ValueError as e:
    # 401 Unauthorized
    return jsonify({'error': str(e)}), 401
except Exception as e:
    # 500 Internal Server Error
    return jsonify({'error': str(e)}), 500
```

## 6. Giới Hạn & Lưu Ý
- Transcript bị cắt nếu quá 95000 ký tự
- Comments được chia thành nhiều phần nếu quá dài
- Cần RAPID_API_KEY hợp lệ
- API key cố định: `yt2024_k8hj3n5m9p2q4w7r`
- Hỗ trợ nhiều định dạng URL YouTube

## 7. Ví Dụ Sử Dụng

```bash
# Test API
curl "http://localhost:8080?youtube_url=https://www.youtube.com/watch?v=VIDEO_ID" \
-H "X-API-Key: yt2024_k8hj3n5m9p2q4w7r"
```

## 8. Security
- API key validation
- CORS headers
- Rate limiting (thông qua RapidAPI)
- Error handling
- Input validation

## 9. Performance
- Retry mechanism cho API calls
- Caching (thông qua RapidAPI)
- Phân trang comments
- Tối ưu độ dài response

## 10. Monitoring
- Debug logging
- Error tracking
- API response monitoring
- Rate limit tracking
