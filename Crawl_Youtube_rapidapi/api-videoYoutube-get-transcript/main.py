import functions_framework
from flask import jsonify, abort
import requests
from urllib.parse import urlparse, parse_qs
import json
import xml.etree.ElementTree as ET
from datetime import timedelta
import os
import http.client

from dotenv import load_dotenv
import os
import logging
import sys
import threading
import json
# Set console output encoding to UTF-8 để khi docker compose nó log ra được port 3000
sys.stdout.reconfigure(encoding='utf-8')

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Rapid API key từ environment variable 
load_dotenv()
RAPID_API_KEY = os.environ.get('RAPID_API_KEY')
if not RAPID_API_KEY:
    logger.error("RAPID_API_KEY not found in environment variables")
    raise ValueError("Missing RAPID_API_KEY in environment")

logger.info(f"RAPID_API_KEY loaded: {RAPID_API_KEY[:5]}...")  # Log 5 ký tự đầu để kiểm tra
# API key cố định
ALLOWED_API_KEY = 'yt2024_k8hj3n5m9p2q4w7r'

def validate_api_key(api_key):
    """Validate client API key"""
    if not api_key:
        raise ValueError("Missing API key")
    if api_key != ALLOWED_API_KEY:
        raise ValueError("Invalid API key")

def validate_request(request):
    """Validate request parameters"""
    request_json = request.get_json(silent=True)
    if not request_json:
        abort(400, description="Request must contain JSON body")

    youtube_url = request_json.get('youtube_url')
    api_key = request.headers.get('X-API-Key')
    
    if not youtube_url:
        abort(400, description="Missing required field: youtube_url")
        
    return youtube_url, api_key

def convert_subscriber_count(count_text):
    """Convert subscriber count from text (e.g. '2.19M subscribers') to number"""
    try:
        if not count_text:
            return 0
        count = count_text.replace('subscribers', '').strip()
        multiplier = 1
        if 'K' in count:
            multiplier = 1000
            count = count.replace('K', '')
        elif 'M' in count:
            multiplier = 1000000
            count = count.replace('M', '')
        elif 'B' in count:
            multiplier = 1000000000
            count = count.replace('B', '')
        return int(float(count) * multiplier)
    except (ValueError, AttributeError):
        print(f"Error converting subscriber count: {count_text}")
        return 0

def get_transcript_from_subtitles(subtitle_url, max_retries=3):
    """Get and process transcript from subtitles URL with retries"""
    for attempt in range(max_retries):
        try:
            transcript_lines = []
            subtitle_response = requests.get(subtitle_url)
            
            if subtitle_response.status_code == 200:
                content = subtitle_response.content
                if not content or len(content.strip()) == 0:
                    raise ValueError(f"Empty response content for URL: {subtitle_url}")
                
                root = ET.fromstring(content)
                for elem in root.iter('text'):
                    start = elem.get('start')
                    text = elem.text
                    if start and text:
                        start_seconds = float(start)
                        start_time = str(timedelta(seconds=start_seconds))
                        hh_mm_ss = start_time.split('.')[0]
                        transcript_lines.append(f"[{hh_mm_ss}] {text}")
                
                if transcript_lines:
                    transcript_text = '\n'.join(transcript_lines)
                    if len(transcript_text) > 95000:
                        transcript_text = transcript_text[:95000] + "\n[Transcript bị cắt do quá dài]"
                    return transcript_text
                    
            else:
                print(f"Failed to retrieve subtitle data: {subtitle_response.status_code}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue
                
        except (ET.ParseError, ValueError, requests.exceptions.RequestException) as e:
            print(f"Error processing subtitles (attempt {attempt + 1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
            
    return ""

def extract_video_id(youtube_url):
    """Extract video ID from YouTube URL"""
    try:
        # Xử lý trường hợp URL bắt đầu bằng @
        if youtube_url.startswith('@'):
            youtube_url = youtube_url.lstrip('@')
            
        # Thêm https:// nếu URL không có
        if not youtube_url.startswith(('http://', 'https://')):
            youtube_url = 'https://' + youtube_url
            
        parsed_url = urlparse(youtube_url)
        
        # Kiểm tra hostname hợp lệ
        if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
            if parsed_url.path == '/watch':
                return parse_qs(parsed_url.query)['v'][0]
                
        # Trường hợp URL ngắn youtu.be
        elif parsed_url.hostname == 'youtu.be':
            return parsed_url.path.lstrip('/')
            
        return None
        
    except Exception as e:
        print(f"Error extracting video ID: {str(e)}")
        return None

def get_video_details(video_id):
    """Get video details from API"""
    url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/details"
    
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": "youtube-media-downloader.p.rapidapi.com"
    }
    
    params = {"videoId": video_id}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API call error: {str(e)}")
        return None

def get_video_comments(video_id):
    """Get comments for a YouTube video"""
    try:
        # Tạo connection
        conn = http.client.HTTPSConnection("youtube-media-downloader.p.rapidapi.com")
        
        # Headers chính xác như mẫu
        headers = {
            'X-RapidAPI-Key': os.environ.get('RAPID_API_KEY'),
            'X-RapidAPI-Host': "youtube-media-downloader.p.rapidapi.com"
        }
        
        all_comments = []
        formatted_comments = []
        next_token = None
        
        while True:
            # Build URL
            url = f"/v2/video/comments?videoId={video_id}&sortBy=top"
            if next_token:
                url += f"&nextToken={next_token}"
                
            # Make request
            conn.request("GET", url, headers=headers)
            response = conn.getresponse()
            data = json.loads(response.read().decode("utf-8"))
            
            if not data.get("status"):
                error_id = data.get("errorId", "Unknown error")
                if error_id == "VideoNotFoundOrCommentDisabled":
                    return {
                        "count": 0,
                        "comments": [],
                        "status": "DISABLED: Comments are disabled or video not found"
                    }
                else:
                    raise Exception(error_id)
            
            # Get comments from response
            comments = data.get("items", [])
            
            # Format comments
            for comment in comments:
                user_name = comment.get('channel', {}).get('name', '')
                text = comment.get('contentText', '')
                formatted_comment = f"[{user_name}]\n[{text}]"
                formatted_comments.append(formatted_comment)
            
            # Check for next page
            next_token = data.get("nextToken")
            if not next_token:
                break
                
        # Split comments if needed
        if formatted_comments:
            comment_parts = split_comments(formatted_comments)
            return {
                "count": len(formatted_comments),
                "comments": comment_parts,
                "status": f"SUCCESS: {len(formatted_comments)} comments saved in {len(comment_parts)} parts"
            }
        else:
            return {
                "count": 0,
                "comments": [],
                "status": "NO_COMMENTS: No comments found"
            }
            
    except Exception as e:
        print(f"Error getting comments: {str(e)}")
        return {
            "count": 0,
            "comments": [],
            "status": f"ERROR: {str(e)}"
        }

def split_comments(formatted_comments, max_chars=100000):
    """Split comments list into smaller parts under max_chars"""
    parts = []
    current_part = []
    current_length = 0
    
    for comment in formatted_comments:
        comment_length = len(comment) + 2  # Add 2 for \n\n between comments
        
        if current_length + comment_length > max_chars and current_part:
            parts.append("\n\n".join(current_part))
            current_part = [comment]
            current_length = comment_length
        else:
            current_part.append(comment)
            current_length += comment_length
    
    if current_part:
        parts.append("\n\n".join(current_part))
    
    return parts

def process_video_data(video_data):
    """Process and format video data"""
    # Get subtitles URL safely
    subtitles_items = video_data.get("subtitles", {}).get("items", [])
    subtitles_url = subtitles_items[0].get("url", "") if subtitles_items else ""
    
    # Get transcript if subtitles URL exists
    transcript = ""
    if subtitles_url:
        transcript = get_transcript_from_subtitles(subtitles_url)
    
    # Convert subscriber count
    subscriber_count_text = video_data.get("channel", {}).get("subscriberCountText", "")
    subscriber_count = convert_subscriber_count(subscriber_count_text)
    
    # Format is_live to string
    is_live = "true" if video_data.get("isLive", False) else "false"
    
    # Get video ID for comments
    video_id = video_data.get('id', '')
    comments_data = get_video_comments(video_id)
    
    response = {
        "title": video_data.get("title", ""),
        "description": video_data.get("description", ""),
        "username": video_data.get("channel", {}).get("handle", ""),
        "user_screen_name": video_data.get("channel", {}).get("name", ""),
        "user_id": video_data.get("channel", {}).get("id", ""),
        "user_subscribers": subscriber_count,
        "published_time": video_data.get("publishedTime", ""),
        "viewCount": video_data.get("viewCount", 0),
        "likeCount": video_data.get("likeCount", 0),
        "subtitles_url": subtitles_url,
        "duration": video_data.get("duration", ""),
        "thumbnail_url": video_data.get("thumbnail", [{}])[0].get("url", ""),
        "is_live": is_live,
        "category": video_data.get("category", ""),
        "transcript": transcript,
        "url": f"https://youtube.com/watch?v={video_data.get('id', '')}",
        "comments_count": comments_data["count"],
        "comments_status": comments_data["status"]
    }
    
    # Add comments parts if they exist
    if comments_data["comments"]:
        for i, part in enumerate(comments_data["comments"], 1):
            response[f"comments_{i}"] = part
            
    return response

@functions_framework.http
def get_youtube_transcript(request):
    """Main Cloud Function entry point"""
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET',
            'Access-Control-Allow-Headers': 'X-API-Key',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)

    headers = {
        'Access-Control-Allow-Origin': '*'
    }

    try:
        # Validate API key from header
        api_key = request.headers.get('X-API-Key')
        validate_api_key(api_key)
        
        # Get youtube_url from query parameter
        youtube_url = request.args.get('youtube_url')
        if not youtube_url:
            return jsonify({
                'error': 'Missing youtube_url parameter'
            }), 400, headers
            
        # Extract video ID
        video_id = extract_video_id(youtube_url)
        if not video_id:
            return jsonify({
                'error': 'Invalid YouTube URL'
            }), 400, headers
            
        # Get video details
        video_data = get_video_details(video_id)
        if not video_data:
            return jsonify({
                'error': 'Failed to fetch video details'
            }), 500, headers
            
        # Process video data
        formatted_data = process_video_data(video_data)
        
        return jsonify(formatted_data), 200, headers

    except ValueError as e:
        return jsonify({
            'error': str(e)
        }), 401, headers
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500, headers 