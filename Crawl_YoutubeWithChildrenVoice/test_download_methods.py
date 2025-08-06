#!/usr/bin/env python3
"""
Test script to verify different download methods and their effectiveness against bot detection.
"""

import sys
import os
from youtube_audio_downloader import Config, YoutubeAudioDownloader

def test_download_methods():
    """Test both download methods with a sample YouTube URL."""
    
    # Sample YouTube URL (a popular children's video)
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Replace with actual test URL
    
    print("🧪 Testing Download Methods")
    print("=" * 50)
    
    # Initialize downloader
    config = Config()
    downloader = YoutubeAudioDownloader(config)
    
    print(f"📺 Testing URL: {test_url}")
    print()
    
    # Test 1: API-assisted method
    print("🔧 Test 1: API-assisted download method")
    print("-" * 40)
    try:
        wav_path, duration = downloader.download_audio_via_api(test_url, index=1)
        if wav_path:
            print(f"✅ API-assisted method SUCCESS")
            print(f"   📁 File: {wav_path}")
            print(f"   ⏱️  Duration: {duration:.1f}s")
        else:
            print("❌ API-assisted method FAILED")
    except Exception as e:
        print(f"❌ API-assisted method ERROR: {e}")
    
    print()
    
    # Test 2: Traditional yt-dlp method
    print("🔧 Test 2: Traditional yt-dlp method")
    print("-" * 40)
    try:
        wav_path, duration = downloader.download_audio_from_yturl(test_url, index=2)
        if wav_path:
            print(f"✅ Traditional method SUCCESS")
            print(f"   📁 File: {wav_path}")
            print(f"   ⏱️  Duration: {duration:.1f}s")
        else:
            print("❌ Traditional method FAILED")
    except Exception as e:
        print(f"❌ Traditional method ERROR: {e}")
    
    print()
    print("🏁 Test completed!")

if __name__ == "__main__":
    test_download_methods() 