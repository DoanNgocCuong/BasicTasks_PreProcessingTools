import functions_framework
from flask import jsonify, Request
import re
import requests
import os

@functions_framework.http
def get_youtube_playlist_videos(request: Request):
    """Hàm này xử lý yêu cầu HTTP để lấy danh sách video từ một playlist YouTube.
    
    Tham số:
    request: Đối tượng yêu cầu HTTP chứa thông tin về yêu cầu từ client.

    Trả về:
    - Nếu thành công, trả về danh sách URL video trong playlist.
    - Nếu có lỗi, trả về mã lỗi và thông báo lỗi.
    
    Hàm này gọi 2 hàm phụ trợ bên trong:
    - extract_playlist_id: Trích xuất ID của playlist từ URL
    - get_playlist_videos: Lấy danh sách video từ API
    """
    headers = {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, X-Requested-With',
        'Content-Type': 'text/plain'
    }

    if request.method == 'OPTIONS':
        return ('', 204, headers)

    if request.method != 'GET':
        return ('Method not allowed', 405, headers)

    # Lấy URL từ query parameter và xử lý
    try:
        playlist_url = request.args.get('url', '').strip()
        if not playlist_url:
            return ('Missing playlist URL\nPlease provide a YouTube playlist URL in the url parameter', 400, headers)

        # Xử lý URL đặc biệt khi gọi từ browser
        if '&list=' in request.url:
            # Trường hợp URL bị cắt do & trong query parameter
            full_url = request.url
            playlist_url = full_url[full_url.index('url=') + 4:]
            
        print(f"Processing URL: {playlist_url}")  # Debug log
        
        playlist_id = extract_playlist_id(playlist_url)
        if not playlist_id:
            return ('Invalid playlist URL\nCould not extract a valid playlist ID from the provided URL', 400, headers)

        video_urls = get_playlist_videos(playlist_id)
        if not video_urls:
            return ('No videos found\nThe playlist exists but no videos were found or the playlist is empty', 404, headers)

        return ('\n'.join(video_urls), 200, headers)

    except Exception as e:
        print(f"Error: {str(e)}")  # Debug log
        return (f'Error processing request: {str(e)}', 500, headers)

def extract_playlist_id(url):
    """Hàm này trích xuất ID của playlist từ các định dạng URL YouTube khác nhau.
    
    Tham số:
    url: Chuỗi URL của playlist YouTube.

    Trả về:
    - ID của playlist nếu tìm thấy.
    - None nếu không tìm thấy hoặc URL không hợp lệ.
    """
    try:
        # Xử lý input trống hoặc không hợp lệ
        if not url or not isinstance(url, str):
            print("Invalid input: URL is empty or not a string")
            return None
            
        # Loại bỏ khoảng trắng đầu cuối
        url = url.strip()
        
        # Decode URL nếu nó đã được encode (có thể encode nhiều lần)
        try:
            while '%' in url:
                decoded_url = requests.utils.unquote(url)
                if decoded_url == url:  # Nếu không còn gì để decode
                    break
                url = decoded_url
        except Exception as e:
            print(f"Warning: Error during URL decode: {e}")
            # Tiếp tục với URL gốc nếu decode thất bại
            
        print(f"Processing URL: {url}")  # Debug log
        
        # Chuẩn hóa URL
        if url.startswith(('youtube.com', 'www.youtube.com', 'm.youtube.com', 'youtu.be')):
            url = 'https://' + url
        elif url.startswith('//'):
            url = 'https:' + url
        elif not url.startswith(('http://', 'https://')):
            if not any(domain in url for domain in ['youtube.com', 'youtu.be']):
                print("Invalid URL: Not a YouTube URL")
                return None
            url = 'https://' + url
            
        # Chuyển đổi mobile/short URLs
        url = url.replace('m.youtube.com', 'www.youtube.com')
        url = url.replace('youtu.be/', 'www.youtube.com/watch?v=')
        
        # Method 1: Parse query parameters
        try:
            if '?' in url:
                base_url, query = url.split('?', 1)
                params = {}
                for param in query.split('&'):
                    if '=' in param:
                        key, value = param.split('=', 1)
                        # Decode key và value một lần nữa để đảm bảo
                        try:
                            key = requests.utils.unquote(key)
                            value = requests.utils.unquote(value)
                        except:
                            pass
                        params[key] = value
                
                if 'list' in params:
                    playlist_id = params['list']
                    if re.match(r'^[A-Za-z0-9_-]{2,34}$', playlist_id):
                        print(f"Found playlist ID from params: {playlist_id}")
                        return playlist_id
        except Exception as e:
            print(f"Warning: Error parsing URL parameters: {e}")
        
        # Method 2: Regular expressions
        patterns = [
            r'[?&]list=([A-Za-z0-9_-]{2,34})',  # Standard watch URL with list
            r'youtube\.com/playlist\?list=([A-Za-z0-9_-]{2,34})',  # Playlist URL
            r'youtube\.com/watch\?.*list=([A-Za-z0-9_-]{2,34})',  # Watch URL with list
            r'youtu\.be/[A-Za-z0-9_-]+\?list=([A-Za-z0-9_-]{2,34})',  # Short URL
            r'youtube\.com/embed/[A-Za-z0-9_-]+\?list=([A-Za-z0-9_-]{2,34})',  # Embed URL
            r'/playlist/([A-Za-z0-9_-]{2,34})',  # Another playlist format
            r'youtube\.com/.*[?&]list=([A-Za-z0-9_-]{2,34})'  # Catch other variations
        ]
        
        for pattern in patterns:
            try:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    playlist_id = match.group(1)
                    if re.match(r'^[A-Za-z0-9_-]{2,34}$', playlist_id):
                        print(f"Found playlist ID from regex: {playlist_id}")
                        return playlist_id
            except Exception as e:
                print(f"Warning: Error with regex pattern {pattern}: {e}")
                continue
        
        print(f"No valid playlist ID found in URL: {url}")
        return None
        
    except Exception as e:
        print(f"Error extracting playlist ID: {e}")
        return None

def get_playlist_videos(playlist_id):
    """Hàm này lấy danh sách video từ một playlist YouTube thông qua API.
    
    Tham số:
    playlist_id: ID của playlist YouTube.

    Trả về:
    - Danh sách URL video trong playlist.
    - Danh sách rỗng nếu không có video nào được tìm thấy.
    """
    url = "https://youtube-media-downloader.p.rapidapi.com/v2/playlist/details"
    
    api_key = os.getenv(RAPID_API_KEY)
    
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "youtube-media-downloader.p.rapidapi.com"
    }
    
    params = {
        "playlistId": playlist_id
    }
    
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    if not data.get("status"):
        return []
    
    videos = data.get("videos", {}).get("items", [])
    return [
        f"https://www.youtube.com/watch?v={video['id']}"
        for video in videos
        if video.get("id")
    ] 