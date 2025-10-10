"""
URL Utilities

Common functions for handling YouTube URLs, video ID extraction,
and URL normalization.

Author: Refactoring Assistant
"""

import re
from typing import Optional
from urllib.parse import urlparse, parse_qs


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL.
    
    Supports various YouTube URL formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://m.youtube.com/watch?v=VIDEO_ID
    
    Args:
        url (str): YouTube URL
        
    Returns:
        Optional[str]: Video ID or None if not found
    """
    try:
        # Clean the URL
        url = url.strip()
        
        # Parse using urlparse for standard format
        parsed = urlparse(url)
        if 'youtube.com' in parsed.netloc:
            return parse_qs(parsed.query).get('v', [None])[0]
        elif 'youtu.be' in parsed.netloc:
            return parsed.path[1:]
        
        # Fallback to regex patterns
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]+)',
            r'youtube\.com/v/([a-zA-Z0-9_-]+)',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
                
    except Exception:
        pass
    
    return None


def normalize_youtube_url(url: str) -> Optional[str]:
    """Normalize YouTube URL to standard format.
    
    Args:
        url (str): YouTube URL in any supported format
        
    Returns:
        Optional[str]: Normalized URL or None if invalid
    """
    video_id = extract_video_id(url)
    if video_id:
        return f"https://www.youtube.com/watch?v={video_id}"
    return None


def is_valid_youtube_url(url: str) -> bool:
    """Check if URL is a valid YouTube video URL.
    
    Args:
        url (str): URL to validate
        
    Returns:
        bool: True if valid YouTube video URL
    """
    return extract_video_id(url) is not None


def get_video_ids_from_urls(urls: list[str]) -> list[str]:
    """Extract video IDs from a list of URLs.
    
    Args:
        urls (list[str]): List of YouTube URLs
        
    Returns:
        list[str]: List of video IDs (skips invalid URLs)
    """
    video_ids = []
    for url in urls:
        video_id = extract_video_id(url)
        if video_id:
            video_ids.append(video_id)
    return video_ids