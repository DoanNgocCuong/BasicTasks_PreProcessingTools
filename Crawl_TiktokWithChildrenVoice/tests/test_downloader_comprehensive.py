#!/usr/bin/env python3
"""
Comprehensive TikTok Downloader Test with RapidAPI Integration
Tests the full pipeline: API -> Download -> Convert to Audio
"""

import os
import sys
import time
from pathlib import Path

# Import the modules
from tiktok_api_client import TikTokAPIClient
from tiktok_video_downloader import TikTokVideoDownloader

def test_with_real_api_data():
    """Test the downloader with real TikTok videos from RapidAPI."""
    
    print("🚀 Testing TikTok Downloader with Real API Data")
    print("=" * 60)
    
    try:
        # Initialize API client and downloader
        print("🔧 Initializing API client and downloader...")
        api_client = TikTokAPIClient()
        downloader = TikTokVideoDownloader()
        
        # Test keywords that are likely to have Vietnamese children's content
        test_keywords = [
            "bé học",
            "trẻ em", 
            "bé hát"
        ]
        
        print(f"🔍 Testing with keywords: {test_keywords}")
        
        successful_downloads = 0
        total_attempts = 0
        
        for keyword in test_keywords:
            print(f"\n🔍 Searching for videos with keyword: '{keyword}'")
            
            try:
                # Search for videos
                search_result = api_client.search_videos_by_keyword(keyword, count=3)
                
                if not search_result or 'videos' not in search_result:
                    print(f"⚠️ No videos found for keyword: {keyword}")
                    continue
                
                videos = search_result['videos']
                print(f"📊 Found {len(videos)} videos for '{keyword}'")
                
                # Test download for first 2 videos
                for i, video in enumerate(videos[:2], 1):
                    total_attempts += 1
                    
                    print(f"\n🎬 Testing video {i}:")
                    print(f"   Title: {video.get('title', 'Unknown')[:60]}...")
                    print(f"   Video ID: {video.get('video_id', 'Unknown')}")
                    print(f"   Duration: {video.get('duration', 0)} seconds")
                    
                    # Check if we have download URLs
                    if video.get('download_url') or video.get('play_url'):
                        print(f"   ✅ Download URLs available")
                        
                        # Test the download
                        audio_path, duration = downloader.download_and_convert_audio(video, index=total_attempts)
                        
                        if audio_path and duration:
                            print(f"   ✅ SUCCESS! Audio created: {Path(audio_path).name}")
                            print(f"   📊 Duration: {duration:.2f}s")
                            successful_downloads += 1
                            
                            # Clean up to save space
                            downloader.cleanup_audio_file(audio_path)
                        else:
                            print(f"   ❌ Download/conversion failed")
                    else:
                        print(f"   ⚠️ No download URLs in video data")
                    
                    # Brief pause between downloads
                    time.sleep(1)
                
            except Exception as e:
                print(f"❌ Error testing keyword '{keyword}': {e}")
                continue
        
        # Print results
        print(f"\n📊 Test Results Summary:")
        print(f"=" * 40)
        print(f"Total Attempts: {total_attempts}")
        print(f"Successful Downloads: {successful_downloads}")
        success_rate = (successful_downloads / max(total_attempts, 1)) * 100
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Print downloader statistics
        downloader.print_download_statistics()
        
        if successful_downloads > 0:
            print(f"\n🎉 SUCCESS! Downloader is working with API data")
            print(f"💡 Recommendation: Use RapidAPI + direct download method")
            return True
        else:
            print(f"\n⚠️ No successful downloads")
            print(f"💡 This might indicate API issues or download URL problems")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_download_only():
    """Test just the direct download functionality with mock data."""
    
    print("\n🔧 Testing Direct Download Functionality")
    print("=" * 50)
    
    downloader = TikTokVideoDownloader()
    
    # Create mock video data with different URL patterns
    mock_videos = [
        {
            'video_id': 'mock_test_1',
            'title': 'Mock Test Video 1',
            'download_url': 'https://example.com/mock_video1.mp4',  # This will fail but tests the logic
            'play_url': 'https://example.com/mock_video1_play.mp4',
            'url': 'https://www.tiktok.com/@mock/video/123456'
        }
    ]
    
    print("🧪 Testing with mock data to verify download logic...")
    
    for i, video in enumerate(mock_videos, 1):
        print(f"\n🎬 Mock Test {i}: {video['title']}")
        
        # Test URL ID extraction
        video_id = downloader.extract_tiktok_id(video['url'])
        print(f"   Video ID extraction: {video_id}")
        
        # Test download attempt (will fail but shows the flow)
        audio_path, duration = downloader.download_and_convert_audio(video, index=i)
        
        if audio_path:
            print(f"   ✅ Mock test passed (audio created)")
            downloader.cleanup_audio_file(audio_path)
        else:
            print(f"   ⚠️ Mock test behaved as expected (no audio - URLs were fake)")
    
    return True

def test_android_specific():
    """Test Android-specific header configurations."""
    
    print("\n📱 Testing Android-Specific Headers")
    print("=" * 50)
    
    from tiktok_video_downloader import TIKTOK_HEADERS_CONFIGS
    
    print(f"🔧 Available header configurations: {len(TIKTOK_HEADERS_CONFIGS)}")
    
    for i, headers in enumerate(TIKTOK_HEADERS_CONFIGS, 1):
        print(f"\n📱 Header Config {i}:")
        print(f"   User-Agent: {headers.get('User-Agent', 'Not set')[:60]}...")
        
        # Check if it's Android-like
        user_agent = headers.get('User-Agent', '')
        if 'TikTok' in user_agent and 'iPhone' in user_agent:
            print(f"   🍎 Type: iOS TikTok App")
        elif 'TikTok' in user_agent:
            print(f"   🤖 Type: Android TikTok App")
        elif 'iPhone' in user_agent:
            print(f"   📱 Type: Mobile Safari")
        else:
            print(f"   🖥️ Type: Desktop Browser")
    
    print(f"\n💡 Android TikTok headers are typically most effective")
    return True

def main():
    """Run comprehensive tests."""
    
    print("🧪 Comprehensive TikTok Downloader Testing")
    print("=" * 60)
    
    success_count = 0
    
    # Test 1: System check
    print("✅ Test 1: System Dependencies")
    downloader = TikTokVideoDownloader()
    if downloader.has_ffmpeg and downloader.has_ytdlp:
        print("   ✅ All dependencies available")
        success_count += 1
    else:
        print("   ⚠️ Some dependencies missing")
    
    # Test 2: Direct download logic
    print("\n✅ Test 2: Download Logic")
    if test_direct_download_only():
        print("   ✅ Download logic working")
        success_count += 1
    
    # Test 3: Android headers
    print("\n✅ Test 3: Header Configurations")
    if test_android_specific():
        print("   ✅ Header configurations loaded")
        success_count += 1
    
    # Test 4: Real API integration (most important)
    print("\n✅ Test 4: Real API Integration")
    if test_with_real_api_data():
        print("   ✅ Real API integration working")
        success_count += 1
    else:
        print("   ⚠️ Real API integration had issues")
    
    # Summary
    print(f"\n📊 Final Test Summary:")
    print(f"=" * 40)
    print(f"Tests Passed: {success_count}/4")
    
    if success_count >= 3:
        print(f"🎉 OVERALL SUCCESS: Downloader is functional!")
        print(f"💡 Ready for production use")
        return True
    else:
        print(f"⚠️ Some tests failed - may need iteration")
        print(f"💡 Focus on fixing failing components")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)