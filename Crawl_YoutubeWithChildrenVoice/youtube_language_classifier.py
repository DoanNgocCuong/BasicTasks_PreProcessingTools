#!/usr/bin/env python3
"""
YouTube Language Classifier using Auto-Generated Transcripts

This module provides language detection for YouTube videos using the YouTube Transcript API
to check auto-generated captions. This is faster and more reliable than audio-based 
language detection for YouTube content.

Author: Le Hoang Minh
"""

import re
import sys
from typing import Optional, Dict, Any
from youtube_transcript_api import YouTubeTranscriptApi


class YouTubeLanguageClassifier:
    """YouTube language classifier using auto-generated transcripts."""
    
    def __init__(self):
        """Initialize the YouTube language classifier."""
        # YouTube URL patterns for video ID extraction
        self.url_patterns = [
            re.compile(r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]+)'),
            re.compile(r'youtube\.com/v/([a-zA-Z0-9_-]+)'),
            re.compile(r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]+)')
        ]
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from YouTube URL.
        
        Args:
            url (str): YouTube URL
            
        Returns:
            Optional[str]: Video ID or None if not found
        """
        url = url.strip()
        for pattern in self.url_patterns:
            match = pattern.search(url)
            if match:
                return match.group(1)
        return None
    
    def get_auto_generated_language(self, video_id: str) -> Optional[str]:
        """
        Retrieves the language code of the auto-generated transcript for a YouTube video.

        Args:
            video_id (str): The ID of the YouTube video.

        Returns:
            Optional[str]: The language code of the auto-generated transcript, or None if not found.
        """
        try:
            # List all available transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            for transcript in transcript_list:
                # The user wants the language of auto-generated captions.
                if transcript.is_generated:
                    return transcript.language_code
        except Exception as e:
            print(f"⚠️ Error fetching transcripts for video '{video_id}': {e}")
            return None
        
        return None
    
    def detect_language_from_url(self, youtube_url: str) -> Dict[str, Any]:
        """
        Detect language from YouTube URL using auto-generated transcripts.
        
        Args:
            youtube_url (str): YouTube video URL
            
        Returns:
            Dict[str, Any]: Language detection result with metadata
        """
        # Extract video ID from URL
        video_id = self.extract_video_id(youtube_url)
        if not video_id:
            return {
                'detected_language': None,
                'is_vietnamese': False,
                'confidence': 0.0,
                'method': 'transcript_api',
                'error': 'Invalid YouTube URL or video ID not found',
                'video_id': None
            }
        
        # Get auto-generated language
        detected_language = self.get_auto_generated_language(video_id)
        
        if detected_language is None:
            return {
                'detected_language': None,
                'is_vietnamese': False,
                'confidence': 0.0,
                'method': 'transcript_api',
                'error': 'No auto-generated transcript found',
                'video_id': video_id
            }
        
        # Check if Vietnamese
        is_vietnamese = detected_language.lower() == 'vi'
        
        return {
            'detected_language': detected_language,
            'is_vietnamese': is_vietnamese,
            'confidence': 1.0,  # Transcript-based detection is highly reliable
            'method': 'transcript_api',
            'error': None,
            'video_id': video_id
        }
    
    def detect_language_from_video_id(self, video_id: str) -> Dict[str, Any]:
        """
        Detect language from video ID using auto-generated transcripts.
        
        Args:
            video_id (str): YouTube video ID
            
        Returns:
            Dict[str, Any]: Language detection result with metadata
        """
        detected_language = self.get_auto_generated_language(video_id)
        
        if detected_language is None:
            return {
                'detected_language': None,
                'is_vietnamese': False,
                'confidence': 0.0,
                'method': 'transcript_api',
                'error': 'No auto-generated transcript found',
                'video_id': video_id
            }
        
        # Check if Vietnamese
        is_vietnamese = detected_language.lower() == 'vi'
        
        return {
            'detected_language': detected_language,
            'is_vietnamese': is_vietnamese,
            'confidence': 1.0,  # Transcript-based detection is highly reliable
            'method': 'transcript_api',
            'error': None,
            'video_id': video_id
        }
    
    def is_vietnamese_video(self, youtube_url: str) -> Optional[bool]:
        """
        Simple check if a YouTube video is in Vietnamese.
        
        Args:
            youtube_url (str): YouTube video URL
            
        Returns:
            Optional[bool]: True if Vietnamese, False if not, None if error
        """
        result = self.detect_language_from_url(youtube_url)
        if result['error']:
            return None
        return result['is_vietnamese']
    
    def is_vietnamese_video_assume_on_failure(self, youtube_url: str) -> bool:
        """
        Check if a YouTube video is in Vietnamese, assuming Vietnamese when detection fails.
        This is useful for systems that prefer to err on the side of inclusion.
        
        Args:
            youtube_url (str): YouTube video URL
            
        Returns:
            bool: True if Vietnamese or if detection fails, False if definitively not Vietnamese
        """
        result = self.detect_language_from_url(youtube_url)
        if result['error']:
            return True  # Assume Vietnamese when detection fails
        return result['is_vietnamese']


def main():
    """Main function for command-line usage."""
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <video_id_or_url>", file=sys.stderr)
        print("Examples:", file=sys.stderr)
        print(f"  python {sys.argv[0]} dQw4w9WgXcQ", file=sys.stderr)
        print(f"  python {sys.argv[0]} https://www.youtube.com/watch?v=dQw4w9WgXcQ", file=sys.stderr)
        sys.exit(1)

    input_arg = sys.argv[1]
    classifier = YouTubeLanguageClassifier()
    
    # Check if input is URL or video ID
    if input_arg.startswith('http'):
        result = classifier.detect_language_from_url(input_arg)
    else:
        result = classifier.detect_language_from_video_id(input_arg)
    
    if result['error']:
        print(f"Error: {result['error']}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Video ID: {result['video_id']}")
    print(f"Detected Language: {result['detected_language']}")
    print(f"Is Vietnamese: {result['is_vietnamese']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Method: {result['method']}")


if __name__ == "__main__":
    main()
