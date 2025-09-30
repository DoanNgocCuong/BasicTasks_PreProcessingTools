#!/usr/bin/env python3
"""
TikTok API Client Module

This module provides a TikTok API client that integrates with RapidAPI's TikTok API
to search for videos, fetch user content, and retrieve metadata. Designed to mirror
the functionality of YouTube Data API integration but for TikTok content.

Features:
    - User video discovery via username/secUid
    - Keyword-based video search
    - Video metadata retrieval (duration, stats, download URLs)
    - Quota management and rate limiting
    - Error handling and retry logic
    - API key rotation support

Author: Generated for TikTok Children's Voice Crawler
Version: 1.0
"""

import http.client
import json
import time
import random
from typing import List, Dict, Optional, Any
from datetime import datetime
from pathlib import Path

# Constants
DEFAULT_API_DELAY_MIN = 1000
DEFAULT_API_DELAY_MAX = 3000
DEFAULT_MAX_RETRIES = 3
DEFAULT_TIMEOUT = 10
TIKTOK_API_HOST = "tiktok-scraper7.p.rapidapi.com"
MAX_VIDEOS_PER_REQUEST = 100

# Import environment configuration
try:
    from env_config import config
    USE_ENV_CONFIG = True
except ImportError:
    config = None
    USE_ENV_CONFIG = False


class TikTokAPIError(Exception):
    """Custom exception for TikTok API related errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, retry_after: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(self.message)


class TikTokAPIClient:
    """TikTok API client for video discovery and metadata retrieval."""
    
    def __init__(self, output_manager=None):
        """
        Initialize TikTok API client.
        
        Args:
            output_manager: Optional output manager for logging
        """
        self.output = output_manager
        
        # API configuration
        self.base_host = "tiktok-api23.p.rapidapi.com"
        self.base_path = "/api"
        
        # Load API keys from config
        if USE_ENV_CONFIG and config:
            self.api_keys = config.TIKTOK_API_KEYS
            self.api_delay_min = config.API_DELAY_MIN
            self.api_delay_max = config.API_DELAY_MAX
        else:
            # Fallback configuration
            import os
            api_key = os.getenv("TIKTOK_API_KEY")
            if not api_key:
                raise ValueError("No TikTok API key found. Set TIKTOK_API_KEY in environment.")
            self.api_keys = [api_key]
            self.api_delay_min = 1000
            self.api_delay_max = 3000
        
        # Initialize API key rotation
        self.current_api_key_index = 0
        self.api_key = self.api_keys[0]
        
        # Rate limiting and retry configuration
        self.last_request_time = 0
        self.max_retries = 3
        self.base_retry_delay = 2
        
        # Request statistics
        self.requests_made = 0
        self.requests_failed = 0
        self.quota_exceeded_count = 0
        
        print(f"🔧 TikTok API Client initialized with {len(self.api_keys)} API key(s)")
        for i, key in enumerate(self.api_keys, 1):
            print(f"   API Key {i}: {'*' * 10}...{key[-4:]}")
    
    def _log(self, message: str, level: str = "info") -> None:
        """Log message through output manager if available."""
        if self.output:
            if level == "error":
                self.output.print_error(message)
            elif level == "warning":
                self.output.print_warning(message)
            else:
                self.output.print_info(message)
        else:
            print(f"[{level.upper()}] {message}")
    
    def _wait_for_rate_limit(self) -> None:
        """Apply rate limiting between API requests."""
        current_time = time.time()
        time_since_last = (current_time - self.last_request_time) * 1000  # Convert to ms
        
        if time_since_last < self.api_delay_min:
            # Random delay between min and max
            delay_ms = random.randint(self.api_delay_min, self.api_delay_max)
            delay_seconds = delay_ms / 1000.0
            time.sleep(delay_seconds)
        
        self.last_request_time = time.time()
    
    def _make_api_request(self, endpoint: str, headers: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make API request with error handling and retry logic.
        
        Args:
            endpoint (str): API endpoint path
            headers (Dict, optional): Additional headers
            
        Returns:
            Optional[Dict]: API response data or None if failed
        """
        if not headers:
            headers = {}
        
        # Add authentication headers
        headers.update({
            'x-rapidapi-key': self.api_key,
            'x-rapidapi-host': self.base_host
        })
        
        for attempt in range(self.max_retries):
            try:
                # Apply rate limiting
                self._wait_for_rate_limit()
                
                # Make request
                conn = http.client.HTTPSConnection(self.base_host)
                conn.request("GET", endpoint, headers=headers)
                response = conn.getresponse()
                
                self.requests_made += 1
                
                # Handle response
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    conn.close()
                    return data
                elif response.status == 429:
                    # Rate limit exceeded
                    self.quota_exceeded_count += 1
                    retry_after = int(response.getheader('Retry-After', 60))
                    self._log(f"⚠️ Rate limit exceeded, waiting {retry_after}s", "warning")
                    conn.close()
                    time.sleep(retry_after)
                    continue
                elif response.status == 403:
                    # Quota exceeded or invalid key
                    self._log(f"❌ API quota exceeded or invalid key (HTTP {response.status})", "error")
                    conn.close()
                    
                    # Try switching to next API key
                    if self._switch_to_next_api_key():
                        continue
                    else:
                        raise TikTokAPIError(f"All API keys exhausted (HTTP {response.status})", response.status)
                else:
                    # Other HTTP errors
                    error_data = response.read().decode("utf-8")
                    self._log(f"❌ API request failed (HTTP {response.status}): {error_data}", "error")
                    conn.close()
                    
                    if attempt < self.max_retries - 1:
                        delay = self.base_retry_delay * (2 ** attempt)  # Exponential backoff
                        self._log(f"🔄 Retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})", "info")
                        time.sleep(delay)
                    else:
                        self.requests_failed += 1
                        raise TikTokAPIError(f"API request failed after {self.max_retries} attempts", response.status)
                        
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = self.base_retry_delay * (2 ** attempt)
                    self._log(f"⚠️ Request error: {e}, retrying in {delay}s", "warning")
                    time.sleep(delay)
                else:
                    self._log(f"❌ Request failed after {self.max_retries} attempts: {e}", "error")
                    self.requests_failed += 1
                    raise TikTokAPIError(f"Network error: {e}")
        
        return None
    
    def _switch_to_next_api_key(self) -> bool:
        """Switch to next available API key."""
        if self.current_api_key_index + 1 < len(self.api_keys):
            self.current_api_key_index += 1
            old_key = self.api_key
            self.api_key = self.api_keys[self.current_api_key_index]
            
            self._log(f"🔄 Switching to API Key {self.current_api_key_index + 1}", "info")
            self._log(f"   Previous: {'*' * 10}...{old_key[-4:]}", "info")
            self._log(f"   Current:  {'*' * 10}...{self.api_key[-4:]}", "info")
            
            return True
        else:
            self._log(f"❌ No more API keys available ({len(self.api_keys)}/{len(self.api_keys)} used)", "error")
            return False
    
    def get_user_info(self, username: str) -> Optional[Dict]:
        """
        Get user information by username.
        
        Args:
            username (str): TikTok username (without @)
            
        Returns:
            Optional[Dict]: User information or None if failed
        """
        endpoint = f"{self.base_path}/user/info?uniqueId={username}"
        
        try:
            self._log(f"🔍 Fetching user info for: {username}")
            response = self._make_api_request(endpoint)
            
            if response and 'userInfo' in response:
                user_info = response['userInfo']['user']
                return {
                    'id': user_info.get('id'),
                    'sec_uid': user_info.get('secUid'),
                    'unique_id': user_info.get('uniqueId'),
                    'nickname': user_info.get('nickname'),
                    'avatar': user_info.get('avatarThumb'),
                    'signature': user_info.get('signature'),
                    'follower_count': response['userInfo']['stats'].get('followerCount', 0),
                    'following_count': response['userInfo']['stats'].get('followingCount', 0),
                    'heart_count': response['userInfo']['stats'].get('heartCount', 0),
                    'video_count': response['userInfo']['stats'].get('videoCount', 0)
                }
            else:
                self._log(f"⚠️ No user info found for: {username}", "warning")
                return None
                
        except TikTokAPIError as e:
            self._log(f"❌ Failed to get user info for {username}: {e.message}", "error")
            return None
    
    def get_user_videos(self, username: str, count: int = 30, cursor: int = 0) -> List[Dict]:
        """
        Get videos from a specific user.
        
        Args:
            username (str): TikTok username (without @)
            count (int): Number of videos to fetch (default: 30)
            cursor (int): Pagination cursor (default: 0)
            
        Returns:
            List[Dict]: List of video information dictionaries
        """
        # First get user info to obtain secUid
        user_info = self.get_user_info(username)
        if not user_info or not user_info.get('sec_uid'):
            self._log(f"❌ Cannot get videos for {username}: User info not available", "error")
            return []
        
        sec_uid = user_info['sec_uid']
        endpoint = f"{self.base_path}/user/posts?secUid={sec_uid}&count={count}&cursor={cursor}"
        
        try:
            self._log(f"🎬 Fetching {count} videos from user: {username}")
            response = self._make_api_request(endpoint)
            
            if response and 'data' in response and 'itemList' in response['data']:
                videos = []
                for item in response['data']['itemList']:
                    video_info = self._extract_video_info_from_item(item, username)
                    if video_info:
                        videos.append(video_info)
                
                self._log(f"✅ Found {len(videos)} videos from {username}")
                return videos
            else:
                self._log(f"⚠️ No videos found for user: {username}", "warning")
                return []
                
        except TikTokAPIError as e:
            self._log(f"❌ Failed to get videos for {username}: {e.message}", "error")
            return []
    
    def search_videos_by_keyword_with_pagination(self, keyword: str, max_total_count: Optional[int] = None) -> List[Dict]:
        """
        Search videos by keyword with EXHAUSTIVE pagination - gets ALL available results.
        
        Args:
            keyword (str): Keyword or phrase to search for
            max_total_count (int, optional): Maximum total videos to fetch (None = get ALL available)
            
        Returns:
            List[Dict]: List of ALL available video information dictionaries
        """
        all_videos = []
        cursor = 0
        search_id = 0
        page_num = 1
        max_pages = 100  # Safety limit to prevent infinite loops
        
        self._log(f"🚀 Starting EXHAUSTIVE keyword search for: '{keyword}'")
        self._log(f"📊 Max total count: {max_total_count if max_total_count else 'UNLIMITED (get all)'}")
        
        while page_num <= max_pages:
            self._log(f"\n� Page {page_num} - Cursor: {cursor}")
            
            # Fetch current page
            result = self.search_videos_by_keyword(keyword, count=50, cursor=cursor, search_id=search_id)
            
            videos = result.get('videos', [])
            has_more = result.get('has_more', False)
            next_cursor = result.get('next_cursor')
            
            if not videos:
                self._log(f"❌ No videos found on page {page_num}, stopping pagination")
                break
            
            # Add videos to collection
            all_videos.extend(videos)
            current_total = len(all_videos)
            
            self._log(f"✅ Page {page_num}: +{len(videos)} videos | Total: {current_total}")
            
            # Check if we've reached our max limit
            if max_total_count and current_total >= max_total_count:
                all_videos = all_videos[:max_total_count]  # Trim to exact limit
                self._log(f"🎯 Reached max limit of {max_total_count} videos")
                break
            
            # Check if API says there are more results
            if not has_more:
                self._log(f"✅ API indicates no more results (has_more: {has_more})")
                break
            
            # Check if we have a valid next cursor
            if next_cursor is None:
                self._log(f"❌ No next_cursor provided by API, stopping pagination")
                break
            
            # Update cursor for next iteration using API's next_cursor
            cursor = next_cursor
            page_num += 1
            
            # Rate limiting between pages (be respectful to API)
            self._log(f"⏳ Sleeping 2 seconds before next page...")
            time.sleep(2)
        
        # Final summary
        self._log(f"\n🎉 EXHAUSTIVE search completed for '{keyword}'!")
        self._log(f"📊 Total pages fetched: {page_num - 1}")
        self._log(f"📊 Total videos collected: {len(all_videos)}")
        
        if page_num > max_pages:
            self._log(f"⚠️ Reached safety limit of {max_pages} pages")
        
        return all_videos

    def search_videos_by_keyword(self, keyword: str, count: int = 30, cursor: int = 0, search_id: int = 0) -> Dict[str, Any]:
        """
        Search videos by general keyword/query using TikTok's video search API.
        
        Args:
            keyword (str): Keyword or phrase to search for
            count (int): Number of videos to fetch (default: 30)
            cursor (int): Pagination cursor (default: 0)
            search_id (int): Search ID for TikTok API (default: 0)
            
        Returns:
            Dict: Dictionary containing videos list and pagination info
        """
        from urllib.parse import quote_plus
        
        # URL encode the keyword to handle spaces and special characters
        encoded_keyword = quote_plus(keyword)
        
        # Use the correct TikTok video search endpoint
        endpoint = f"{self.base_path}/search/video?keyword={encoded_keyword}&cursor={cursor}&search_id={search_id}"
        
        try:
            self._log(f"🔍 Searching videos by keyword: '{keyword}' (cursor: {cursor})")
            response = self._make_api_request(endpoint)
            
            if response and 'item_list' in response:
                videos = []
                items = response.get('item_list', [])
                
                # Extract pagination info from API response
                has_more = response.get('has_more', 0)
                next_cursor = response.get('cursor', None)
                
                self._log(f"📝 API Response: {len(items)} items, has_more: {has_more}, next_cursor: {next_cursor}")
                
                for item in items:
                    video_info = self._extract_video_info_from_item(item)
                    if video_info:
                        videos.append(video_info)
                
                self._log(f"✅ Found {len(videos)} videos for keyword '{keyword}'")
                
                return {
                    'videos': videos,
                    'has_more': bool(has_more),
                    'next_cursor': next_cursor,
                    'total_items': len(videos)
                }
            else:
                self._log(f"⚠️ No videos found for keyword: '{keyword}' - Response: {response}", "warning")
                return {
                    'videos': [],
                    'has_more': False,
                    'next_cursor': None,
                    'total_items': 0
                }
                
        except TikTokAPIError as e:
            self._log(f"❌ Failed to search keyword '{keyword}': {e.message}", "error")
            return {
                'videos': [],
                'has_more': False,
                'next_cursor': None,
                'total_items': 0
            }


    
    def _extract_video_info_from_item(self, item: Dict, username: Optional[str] = None) -> Optional[Dict]:
        """
        Extract video information from TikTok API response item.
        
        Args:
            item (Dict): Video item from API response
            username (str, optional): Username if known
            
        Returns:
            Optional[Dict]: Extracted video information
        """
        try:
            video_id = item.get('id')
            if not video_id:
                return None
            
            # Extract basic video info
            desc = item.get('desc', '')
            create_time = item.get('createTime', 0)
            
            # Extract video details
            video_data = item.get('video', {})
            duration = video_data.get('duration', 0)
            
            # Extract statistics
            stats = item.get('stats', {})
            play_count = stats.get('playCount', 0)
            like_count = stats.get('diggCount', 0)
            comment_count = stats.get('commentCount', 0)
            share_count = stats.get('shareCount', 0)
            
            # Extract author info
            author = item.get('author', {})
            author_username = author.get('uniqueId', username or 'unknown')
            author_nickname = author.get('nickname', '')
            
            # Extract URLs
            download_url = video_data.get('downloadAddr', '')
            play_url = video_data.get('playAddr', '')
            cover_url = video_data.get('cover', '')
            
            # Build TikTok URL
            tiktok_url = f"https://www.tiktok.com/@{author_username}/video/{video_id}"
            
            return {
                'video_id': video_id,
                'title': desc[:100] + '...' if len(desc) > 100 else desc,  # Use description as title
                'description': desc,
                'duration': duration / 1000 if duration > 1000 else duration,  # Convert to seconds if needed
                'create_time': create_time,
                'created_at': datetime.fromtimestamp(create_time).isoformat() if create_time else '',
                'author_username': author_username,
                'author_nickname': author_nickname,
                'channel_id': author.get('id', ''),
                'channel_title': author_nickname,
                'play_count': play_count,
                'like_count': like_count,
                'comment_count': comment_count,
                'share_count': share_count,
                'download_url': download_url,
                'play_url': play_url,
                'cover_url': cover_url,
                'url': tiktok_url
            }
            
        except Exception as e:
            self._log(f"⚠️ Error extracting video info: {e}", "warning")
            return None
    
    def get_api_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        return {
            'requests_made': self.requests_made,
            'requests_failed': self.requests_failed,
            'quota_exceeded_count': self.quota_exceeded_count,
            'current_api_key_index': self.current_api_key_index,
            'total_api_keys': len(self.api_keys),
            'success_rate': (self.requests_made - self.requests_failed) / max(self.requests_made, 1) * 100
        }
    
    def print_api_usage_summary(self) -> None:
        """Print API usage summary."""
        stats = self.get_api_usage_stats()
        print("\n📊 TikTok API Usage Summary:")
        print("=" * 40)
        print(f"Total Requests: {stats['requests_made']}")
        print(f"Failed Requests: {stats['requests_failed']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Quota Exceeded: {stats['quota_exceeded_count']} times")
        print(f"API Keys Used: {stats['current_api_key_index'] + 1}/{stats['total_api_keys']}")
        print("=" * 40)


# For testing the TikTokAPIClient directly
if __name__ == "__main__":
    print("🧪 Testing TikTok API Client...")
    
    try:
        # Initialize client
        client = TikTokAPIClient()
        
        # Test keyword search functionality
        print("\n🔍 Testing keyword search functionality...")
        test_keywords = ["trẻ em việt nam", "thiếu nhi", "bé học nói"]
        
        for keyword in test_keywords:
            print(f"\n--- Testing keyword: '{keyword}' ---")
            videos = client.search_videos_by_keyword(keyword, count=5)
            
            if videos:
                print(f"✅ Found {len(videos)} videos for keyword '{keyword}'")
                for i, video in enumerate(videos[:3], 1):  # Show first 3
                    print(f"   {i}. {video['title'][:50]}...")
                    print(f"      Author: @{video['author_username']}")
                    print(f"      Duration: {video['duration']}s, Views: {video['play_count']}")
                    print(f"      URL: {video['url']}")
            else:
                print(f"⚠️ No videos found for keyword '{keyword}'")
        
        # Test user info (existing test)
        print(f"\n👤 Testing user info...")
        test_username = "moxierobot"
        user_info = client.get_user_info(test_username)
        if user_info:
            print(f"✅ User info retrieved for {test_username}")
            print(f"   Nickname: {user_info['nickname']}")
            print(f"   Followers: {user_info['follower_count']}")
            print(f"   Videos: {user_info['video_count']}")
        
        # Test user videos (existing test)
        print(f"\n🎬 Testing user videos...")
        videos = client.get_user_videos(test_username, count=3)
        if videos:
            print(f"✅ Retrieved {len(videos)} videos from {test_username}")
            for i, video in enumerate(videos, 1):
                print(f"   {i}. {video['title'][:50]}...")
                print(f"      Duration: {video['duration']}s, Likes: {video['like_count']}")
        
        # Test pagination for keyword search
        print(f"\n📄 Testing keyword search with pagination...")
        paginated_videos = client.search_videos_by_keyword_with_pagination("trẻ em", total_count=10)
        if paginated_videos:
            print(f"✅ Paginated search returned {len(paginated_videos)} videos")
            print(f"   First video: {paginated_videos[0]['title'][:50]}...")
            print(f"   Last video: {paginated_videos[-1]['title'][:50]}...")
        
        # Print usage stats
        client.print_api_usage_summary()
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()