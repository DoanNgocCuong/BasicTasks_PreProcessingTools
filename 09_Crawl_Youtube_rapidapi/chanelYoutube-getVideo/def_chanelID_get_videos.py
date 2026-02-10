import os
import logging
import requests
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class YouTubeVideoFetcher:
    """Class để xử lý việc lấy video từ một channel YouTube."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            'X-RapidAPI-Key': api_key,
            'X-RapidAPI-Host': "youtube-media-downloader.p.rapidapi.com"
        }

    def get_channel_videos(self, channel_id: str) -> List[Dict]:
        """
        Lấy danh sách video từ Channel ID sử dụng API RapidAPI.
        """
        try:
            url = "https://youtube-media-downloader.p.rapidapi.com/v2/channel/videos"
            params = {
                "channelId": channel_id,
                "type": "videos",
                "sortBy": "newest"
            }
            
            logger.debug(f"Gọi API RapidAPI với URL: {url}")
            logger.debug(f"Parameters: {params}")
            logger.debug(f"Headers: {self.headers}")
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response content: {response.text}")

            data = response.json()
            
            # Kiểm tra xem response có thành công không
            if not data.get("status"):
                logger.error(f"API trả về lỗi: {data.get('errorId', 'Unknown error')}")
                return []

            # Lấy danh sách video từ trường items
            items = data.get("items", [])
            logger.debug(f"Tìm thấy {len(items)} video.")

            # Chuyển đổi format dữ liệu
            videos = []
            for item in items:
                if item.get("type") == "video":  # Chỉ lấy các item có type là video
                    video = {
                        'url': f"https://www.youtube.com/watch?v={item.get('id')}",
                        'title': item.get('title', ''),
                        'videoId': item.get('id', '')
                    }
                    videos.append(video)

            logger.info(f"Đã xử lý thành công {len(videos)} video")
            return videos

        except requests.exceptions.RequestException as e:
            logger.exception(f"Lỗi kết nối API: {str(e)}")
            return []
        except Exception as e:
            logger.exception(f"Lỗi không xác định: {str(e)}")
            return []
