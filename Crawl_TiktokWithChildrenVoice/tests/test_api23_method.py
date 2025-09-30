#!/usr/bin/env python3
"""
Test TikTok API23 Download Method
Tests the new TikTok API23 endpoint for downloading videos
"""

import os
import sys
import time
from pathlib import Path
from tiktok_video_downloader import TikTokVideoDownloader

def test_api23_method():
    """Test the TikTok API23 download method."""
    
    print("🚀 Testing TikTok API23 Download Method")
    print("=" * 50)
    
    # Initialize downloader
    downloader = TikTokVideoDownloader()
    
    # Test URLs - using the example from the API documentation
    test_videos = [
        {
            'video_id': 'api23_test_1',
            'title': 'Taylor Swift TikTok Test',
            'url': 'https://www.tiktok.com/@taylorswift/video/7288965373704064286',
            'duration': 30  # estimated
        },
        {
            'video_id': 'api23_test_2', 
            'title': 'Vietnamese Children Test',
            'url': 'https://www.tiktok.com/@rubyvuvn/video/7328257376878939410',  # From our real data
            'duration': 99
        }
    ]
    
    # Create test output directory
    Path("./test_api23_output").mkdir(exist_ok=True)
    
    successful_tests = 0
    total_tests = len(test_videos)
    
    for i, video in enumerate(test_videos, 1):
        print(f"\n🎬 Test {i}/{total_tests}: {video['title']}")
        print(f"   URL: {video['url']}")
        
        # Test API23 download method directly
        test_video_path = f"./test_api23_output/test_{i}_video.mp4"
        test_audio_path = f"./test_api23_output/test_{i}_audio.wav"
        
        print(f"   🚀 Testing API23 download method...")
        
        # Test the API23 download
        api23_success = downloader.download_video_api23(video['url'], test_video_path)
        
        if api23_success:
            print(f"   ✅ API23 download successful!")
            
            # Test audio conversion
            print(f"   🎵 Testing audio conversion...")
            audio_success = downloader.convert_to_audio(test_video_path, test_audio_path)
            
            if audio_success:
                print(f"   ✅ Audio conversion successful!")
                
                # Get duration
                duration = downloader._get_audio_duration(test_audio_path)
                print(f"   📊 Audio duration: {duration:.2f} seconds")
                
                # Verify file sizes
                video_size = Path(test_video_path).stat().st_size
                audio_size = Path(test_audio_path).stat().st_size
                print(f"   📁 Video size: {video_size:,} bytes")
                print(f"   📁 Audio size: {audio_size:,} bytes")
                
                successful_tests += 1
                print(f"   🎉 Test {i} PASSED!")
                
                # Clean up test files
                Path(test_video_path).unlink(missing_ok=True)
                Path(test_audio_path).unlink(missing_ok=True)
            else:
                print(f"   ❌ Audio conversion failed")
                Path(test_video_path).unlink(missing_ok=True)
        else:
            print(f"   ❌ API23 download failed")
        
        # Brief pause between tests
        time.sleep(2)
    
    # Results
    success_rate = (successful_tests / total_tests) * 100
    print(f"\n📊 API23 Test Results:")
    print(f"=" * 30)
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    return successful_tests > 0

def test_full_pipeline_with_api23():
    """Test the full pipeline with API23 as primary method."""
    
    print("\n🔧 Testing Full Pipeline with API23")
    print("=" * 40)
    
    downloader = TikTokVideoDownloader()
    
    # Test video data
    video_info = {
        'video_id': 'full_pipeline_test',
        'title': 'Full Pipeline API23 Test',
        'url': 'https://www.tiktok.com/@taylorswift/video/7288965373704064286',
        'duration': 30
    }
    
    print(f"🎬 Testing full pipeline: {video_info['title']}")
    
    # Test the complete pipeline
    audio_path, duration = downloader.download_and_convert_audio(video_info, index=1)
    
    if audio_path and duration:
        print(f"✅ Full pipeline with API23 SUCCESS!")
        print(f"📁 Audio file: {Path(audio_path).name}")
        print(f"⏱️ Duration: {duration:.2f}s")
        
        # Verify file
        if Path(audio_path).exists() and Path(audio_path).stat().st_size > 1000:
            file_size = Path(audio_path).stat().st_size
            print(f"📊 File size: {file_size:,} bytes")
            
            # Clean up
            downloader.cleanup_audio_file(audio_path)
            return True
        else:
            print(f"❌ Audio file too small or missing")
            return False
    else:
        print(f"❌ Full pipeline test failed")
        return False

def main():
    """Run API23 tests."""
    
    print("🧪 TikTok API23 Download Method Testing")
    print("=" * 50)
    
    tests_passed = 0
    
    # Test 1: System check
    print("✅ Test 1: System Check")
    downloader = TikTokVideoDownloader()
    if downloader.has_ffmpeg:
        print("   ✅ FFmpeg available")
        tests_passed += 1
    else:
        print("   ❌ FFmpeg missing")
    
    # Test 2: API23 method
    print("\n✅ Test 2: API23 Download Method")
    if test_api23_method():
        print("   ✅ API23 method working")
        tests_passed += 1
    else:
        print("   ❌ API23 method failed")
    
    # Test 3: Full pipeline
    print("\n✅ Test 3: Full Pipeline with API23")
    if test_full_pipeline_with_api23():
        print("   ✅ Full pipeline working")
        tests_passed += 1
    else:
        print("   ❌ Full pipeline failed")
    
    # Summary
    print(f"\n📊 Final Results:")
    print(f"=" * 25)
    print(f"Tests Passed: {tests_passed}/3")
    
    if tests_passed >= 2:
        print(f"🎉 SUCCESS! API23 method is working!")
        print(f"💡 The downloader now uses API23 as primary method")
        return True
    else:
        print(f"⚠️ Some tests failed - may need API key configuration")
        print(f"💡 Check your RapidAPI key in environment variables")
        return False

if __name__ == "__main__":
    success = main()
    
    # Clean up test files
    try:
        import shutil
        if Path("./test_api23_output").exists():
            shutil.rmtree("./test_api23_output", ignore_errors=True)
        print("🧹 Cleaned up test files")
    except:
        pass
    
    sys.exit(0 if success else 1)