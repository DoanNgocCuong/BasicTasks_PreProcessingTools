import requests
import logging
from typing import Dict, Optional
import os
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
from datetime import timedelta
import json

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class YouTubeTranscriptFetcher:
    """Class để lấy transcript từ video YouTube."""

    def __init__(self):
        self.api_key = os.getenv('RAPID_API_KEY')
        # Print 5 ký tự đầu của API key
        logger.info(f"Using RapidAPI Key: {self.api_key[:5]}...")
        
        self.headers = {
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'youtube-media-downloader.p.rapidapi.com'
        }

    def get_transcript(self, video_id: str) -> Optional[Dict]:
        """
        Lấy transcript cho một video YouTube.
        
        Args:
            video_id (str): ID của video YouTube
            
        Returns:
            Optional[Dict]: Transcript của video hoặc None nếu có lỗi
        """
        try:
            # Bước 1: Lấy thông tin video từ RapidAPI
            url = "https://youtube-media-downloader.p.rapidapi.com/v2/video/details"
            params = {"videoId": video_id}

            logger.debug(f"Gọi API để lấy thông tin video ID: {video_id}")
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            # Log response để debug
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response content: {response.text[:200]}...")  # Log 200 ký tự đầu
            
            video_data = response.json()
            if not video_data.get("status"):
                logger.error(f"API trả về lỗi: {video_data.get('errorId', 'Unknown error')}")
                return None

            # Bước 2: Lấy URL subtitle từ response
            subtitles_items = video_data.get("subtitles", {}).get("items", [])
            if not subtitles_items:
                logger.error(f"Không tìm thấy subtitle cho video {video_id}")
                return None

            subtitle_url = subtitles_items[0].get("url", "")
            if not subtitle_url:
                logger.error(f"Không tìm thấy URL subtitle cho video {video_id}")
                return None

            # Bước 3: Lấy và xử lý transcript từ URL subtitle
            logger.debug(f"Lấy transcript từ URL: {subtitle_url}")
            subtitle_response = requests.get(subtitle_url)
            if subtitle_response.status_code != 200:
                logger.error(f"Lỗi khi lấy subtitle: {subtitle_response.status_code}")
                return None

            # Bước 4: Parse XML và format transcript
            content = subtitle_response.content
            root = ET.fromstring(content)
            
            transcript_lines = []
            for elem in root.iter('text'):
                start = elem.get('start')
                text = elem.text
                if start and text:
                    start_seconds = float(start)
                    start_time = str(timedelta(seconds=start_seconds))
                    hh_mm_ss = start_time.split('.')[0]
                    transcript_lines.append(f"[{hh_mm_ss}] {text}")

            if not transcript_lines:
                logger.error("Không tìm thấy nội dung transcript")
                return None

            # Nối các dòng transcript và lưu full không cắt
            transcript_text = '\n'.join(transcript_lines)

            return {
                'transcript': transcript_text,
                'status': 'success'
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return None
        except Exception as e:
            logger.exception(f"Lỗi không xác định: {str(e)}")
            return None

if __name__ == "__main__":
    # Test trực tiếp với API key
    api_key = "ea64b08711msha22c57711b460f4p1f7931jsnd2ac889bd9d8"  # Thay bằng API key của bạn
    
    # Khởi tạo fetcher với API key
    fetcher = YouTubeTranscriptFetcher()
    fetcher.api_key = api_key
    fetcher.headers = {
        'X-RapidAPI-Key': api_key,
        'X-RapidAPI-Host': 'youtube-media-downloader.p.rapidapi.com'
    }
    
    # Test với một video ID
    video_id = "csgAUqG75ZE"  # ID video test
    print(f"\nTesting with video ID: {video_id}")
    print(f"Using API Key: {api_key[:5]}...")
    
    result = fetcher.get_transcript(video_id)
    if result:
        print("Success!")
        print(f"First 200 chars of transcript: {result['transcript']}")
    else:
        print("Failed to get transcript")
