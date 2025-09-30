#!/usr/bin/env python3
"""
Independent test script for TikTok Video Downloader
Tests different download methods and header configurations
"""

import os
import sys
import time
from pathlib import Path

# Import the downloader
from tiktok_video_downloader import TikTokVideoDownloader

def test_download_methods():
    """Test different download methods with a sample TikTok video."""
    
    print("🧪 Testing TikTok Video Downloader Methods")
    print("=" * 50)
    
    # Initialize downloader
    downloader = TikTokVideoDownloader()
    
    # Test URLs - using common TikTok URLs that should work
    test_videos = [
        {
            'url': 'https://www.tiktok.com/@tiktok/video/7016451725901745414',
            'video_id': 'test_video_1',
            'title': 'Test Video 1'
        },
        {
            'url': 'https://www.tiktok.com/@officialpsy/video/7144562224176639234',
            'video_id': 'test_video_2', 
            'title': 'Test Video 2'
        }
    ]
    
    # Test each video
    for i, video_info in enumerate(test_videos, 1):
        print(f"\n🎬 Test {i}: {video_info['title']}")
        print(f"URL: {video_info['url']}")
        
        # Test video ID extraction
        video_id = downloader.extract_tiktok_id(video_info['url'])
        print(f"Extracted ID: {video_id}")
        
        # Create test paths
        test_video_path = f"./test_output/test_video_{i}.mp4"
        test_audio_path = f"./test_output/test_audio_{i}.wav"
        
        # Create output directory
        Path("./test_output").mkdir(exist_ok=True)
        
        print(f"\n🔄 Testing yt-dlp download...")
        
        # Test yt-dlp download
        ytdlp_success = downloader.download_video_ytdlp(video_info['url'], test_video_path)
        if ytdlp_success:
            print(f"✅ yt-dlp download successful!")
            
            # Test audio conversion
            print(f"🎵 Testing audio conversion...")
            audio_success = downloader.convert_to_audio(test_video_path, test_audio_path)
            
            if audio_success:
                print(f"✅ Audio conversion successful!")
                
                # Get duration
                duration = downloader._get_audio_duration(test_audio_path)
                print(f"📊 Audio duration: {duration:.2f} seconds")
                
                # Clean up test files
                Path(test_video_path).unlink(missing_ok=True)
                Path(test_audio_path).unlink(missing_ok=True)
                
                print(f"✅ Test {i} PASSED - Full pipeline working!")
                break  # One successful test is enough
            else:
                print(f"❌ Audio conversion failed")
                Path(test_video_path).unlink(missing_ok=True)
        else:
            print(f"❌ yt-dlp download failed")
        
        print(f"⏭️ Moving to next test...")
        time.sleep(2)  # Brief pause between tests
    
    # Print final statistics
    print(f"\n📊 Final Statistics:")
    downloader.print_download_statistics()

def test_android_headers():
    """Test Android-specific headers that usually work better."""
    
    print("\n📱 Testing Android Client Headers")
    print("=" * 50)
    
    downloader = TikTokVideoDownloader()
    
    # Test with a simple video info
    video_info = {
        'url': 'https://www.tiktok.com/@tiktok/video/7016451725901745414',
        'video_id': 'android_test',
        'title': 'Android Header Test'
    }
    
    print(f"🔄 Testing with Android client headers...")
    
    # Test the full download and convert pipeline
    audio_path, duration = downloader.download_and_convert_audio(video_info, index=1)
    
    if audio_path and duration:
        print(f"✅ Android headers test SUCCESSFUL!")
        print(f"📁 Audio file: {audio_path}")
        print(f"⏱️ Duration: {duration:.2f} seconds")
        
        # Clean up
        downloader.cleanup_audio_file(audio_path)
        
        return True
    else:
        print(f"❌ Android headers test failed")
        return False

def main():
    """Run all tests."""
    
    print("🚀 Starting TikTok Downloader Independent Tests")
    print("=" * 60)
    
    try:
        # Test 1: System check
        print("🔧 System Dependency Check...")
        downloader = TikTokVideoDownloader()
        print(f"FFmpeg: {'✅' if downloader.has_ffmpeg else '❌'}")
        print(f"yt-dlp: {'✅' if downloader.has_ytdlp else '❌'}")
        
        if not downloader.has_ffmpeg:
            print("❌ FFmpeg required but not found!")
            return False
            
        if not downloader.has_ytdlp:
            print("⚠️ yt-dlp not found - will limit testing")
        
        # Test 2: Download methods
        test_download_methods()
        
        # Test 3: Android headers (usually more reliable)
        android_success = test_android_headers()
        
        if android_success:
            print("\n🎉 SUCCESS: Android client headers work!")
            print("💡 Recommendation: Use Android client headers for production")
        else:
            print("\n⚠️ All download methods had issues")
            print("💡 This might be due to TikTok's anti-bot measures")
            print("💡 Try running again or use different test URLs")
        
        print("\n✅ Independent testing completed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Clean up any remaining files
        try:
            import shutil
            if Path("./test_output").exists():
                shutil.rmtree("./test_output", ignore_errors=True)
            print("🧹 Cleaned up test files")
        except:
            pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)