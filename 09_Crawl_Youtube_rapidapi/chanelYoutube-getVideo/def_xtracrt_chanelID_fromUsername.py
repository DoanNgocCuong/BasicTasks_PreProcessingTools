import re
import requests
from bs4 import BeautifulSoup
import logging
import json
from typing import Optional

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class YouTubeChannelExtractor:
    """Class để xử lý việc trích xuất Channel ID từ các định dạng URL YouTube khác nhau."""
    
    PATTERNS = {
        'channel': r'youtube\.com/channel/([A-Za-z0-9_-]{24})',
        'custom': r'youtube\.com/c/([A-Za-z0-9_-]+)',
        'user': r'youtube\.com/user/([A-Za-z0-9_-]+)',
        'handle': r'youtube\.com/@([A-Za-z0-9_-]+)'
    }

    @staticmethod
    def extract_channel_id(url: str) -> Optional[str]:
        """
        Trích xuất Channel ID từ URL YouTube.
        Args:
            url (str): URL của kênh YouTube
        Returns:
            Optional[str]: Channel ID nếu tìm thấy, None nếu không
        """
        try:
            logger.debug(f"Processing URL: {url}")
            
            if not url or not isinstance(url, str):
                logger.error("Invalid URL provided")
                return None
                
            url = url.strip()
            
            # Check if URL is already a channel ID
            if YouTubeChannelExtractor._is_channel_id(url):
                logger.debug(f"Direct channel ID detected: {url}")
                return url

            # Try all patterns
            for pattern_type, pattern in YouTubeChannelExtractor.PATTERNS.items():
                if channel_id := YouTubeChannelExtractor._try_pattern(url, pattern, pattern_type):
                    return channel_id

            logger.error(f"No matching pattern found for URL: {url}")
            return None

        except Exception as e:
            logger.exception(f"Error in extract_channel_id: {str(e)}")
            return None

    @staticmethod
    def _is_channel_id(text: str) -> bool:
        """Check if text is a valid channel ID."""
        return (len(text) >= 24 and 
                all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in text))

    @staticmethod
    def _try_pattern(url: str, pattern: str, pattern_type: str) -> Optional[str]:
        """Try to extract channel ID using a specific pattern."""
        try:
            match = re.search(pattern, url)
            if not match:
                return None
                
            value = match.group(1)
            logger.debug(f"Found {pattern_type}: {value}")
            
            if pattern_type == 'channel':
                return value
            return YouTubeChannelExtractor._get_channel_id_from_handle(value)
            
        except Exception as e:
            logger.error(f"Error trying pattern {pattern_type}: {e}")
            return None

    @staticmethod
    def _get_channel_id_from_handle(username: str) -> Optional[str]:
        """Get channel ID from username/handle using YouTube's about page."""
        try:
            about_url = f"https://www.youtube.com/@{username}/about"
            logger.debug(f"Fetching about page: {about_url}")
            
            response = requests.get(about_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Search for channel ID in script tags
            for script in soup.find_all('script'):
                script_text = str(script)
                if 'channelId' not in script_text:
                    continue
                    
                match = re.search(r'"channelId":"(UC[A-Za-z0-9_-]{22})"', script_text)
                if match:
                    channel_id = match.group(1)
                    logger.debug(f"Found channel ID: {channel_id}")
                    return channel_id
                    
            logger.error(f"Could not find channel ID for username: {username}")
            return None
            
        except requests.RequestException as e:
            logger.error(f"Network error getting channel ID: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting channel ID from handle: {e}")
            return None
