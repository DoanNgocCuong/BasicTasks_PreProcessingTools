#!/usr/bin/env python3
"""
Test TikTok Downloader with Real Video Data
Uses existing video data from previous successful crawls
"""

import os
import sys
import json
import time
from pathlib import Path
from tiktok_video_downloader import TikTokVideoDownloader

def load_test_video_data():
    """Load real video data from recent collection results."""
    
    test_data_file = "tiktok_url_outputs/20250930_170150_detailed_collection_results.json"
    
    try:
        with open(test_data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract videos that have both download_url and play_url
        test_videos = []
        
        # Look for collected videos in different possible locations
        if 'collected_videos' in data:
            videos = data['collected_videos']
        elif 'videos' in data:
            videos = data['videos']
        else:
            # Search through the entire structure for video objects
            videos = []
            def find_videos(obj):
                if isinstance(obj, dict):
                    if 'video_id' in obj and 'download_url' in obj:
                        videos.append(obj)
                    for value in obj.values():
                        find_videos(value)
                elif isinstance(obj, list):
                    for item in obj:
                        find_videos(item)
            
            find_videos(data)
        
        # Filter for videos with proper download URLs
        for video in videos:
            if isinstance(video, dict) and video.get('download_url') and video.get('play_url'):
                test_videos.append({
                    'video_id': video.get('video_id'),
                    'title': video.get('title', 'Unknown Title'),
                    'duration': video.get('duration', 0),
                    'download_url': video.get('download_url'),
                    'play_url': video.get('play_url'),
                    'url': video.get('url', ''),
                    'author_username': video.get('author_username', 'unknown')
                })
        
        print(f"✅ Loaded {len(test_videos)} videos with download URLs")
        return test_videos[:3]  # Test with first 3 videos
        
    except Exception as e:
        print(f"❌ Error loading test data: {e}")
        return []

def test_direct_download_with_real_urls():
    """Test direct download with real TikTok video URLs."""
    
    print("🧪 Testing Direct Download with Real TikTok URLs")
    print("=" * 60)
    
    # Load test data
    test_videos = load_test_video_data()
    
    if not test_videos:
        print("❌ No test videos available")
        return False
    
    # Initialize downloader
    downloader = TikTokVideoDownloader()
    
    successful_tests = 0
    total_tests = len(test_videos)
    
    print(f"📊 Testing {total_tests} videos with real download URLs...")
    
    for i, video in enumerate(test_videos, 1):
        print(f"\n🎬 Test {i}/{total_tests}: {video['title'][:50]}...")
        print(f"   Video ID: {video['video_id']}")
        print(f"   Duration: {video['duration']}s")
        print(f"   Author: @{video['author_username']}")
        
        # Test both download URLs
        test_paths = {
            'download_url': f"./test_output/real_test_{i}_download.mp4",
            'play_url': f"./test_output/real_test_{i}_play.mp4"
        }
        
        # Create output directory
        Path("./test_output").mkdir(exist_ok=True)
        
        success_this_video = False
        
        for url_type, test_path in test_paths.items():
            url = video[url_type]
            if not url:
                continue
                
            print(f"   🔄 Testing {url_type}...")
            print(f"      URL: {url[:80]}...")
            
            # Test direct download
            download_success = downloader.download_video_direct(url, test_path)
            
            if download_success:
                print(f"   ✅ {url_type} download successful!")
                
                # Test audio conversion
                audio_path = test_path.replace('.mp4', '.wav')
                audio_success = downloader.convert_to_audio(test_path, audio_path)
                
                if audio_success:
                    print(f"   ✅ Audio conversion successful!")
                    
                    # Get duration
                    duration = downloader._get_audio_duration(audio_path)
                    print(f"   📊 Audio duration: {duration:.2f}s")
                    
                    success_this_video = True
                    
                    # Clean up
                    Path(test_path).unlink(missing_ok=True)
                    Path(audio_path).unlink(missing_ok=True)
                    
                    break  # Success with this URL type, move to next video
                else:
                    print(f"   ❌ Audio conversion failed")
                    Path(test_path).unlink(missing_ok=True)
            else:
                print(f"   ❌ {url_type} download failed")
        
        if success_this_video:
            successful_tests += 1
            print(f"   🎉 Test {i} PASSED!")
        else:
            print(f"   ❌ Test {i} failed")
        
        # Brief pause between tests
        time.sleep(1)
    
    # Results
    success_rate = (successful_tests / total_tests) * 100
    print(f"\n📊 Real URL Test Results:")
    print(f"=" * 40)
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Print downloader statistics
    downloader.print_download_statistics()
    
    if successful_tests > 0:
        print(f"\n🎉 SUCCESS! Downloader works with real TikTok URLs!")
        return True
    else:
        print(f"\n⚠️ All real URL tests failed")
        return False

def test_full_pipeline_integration():
    """Test the complete download and convert pipeline."""
    
    print("\n🔧 Testing Full Pipeline Integration")
    print("=" * 50)
    
    test_videos = load_test_video_data()
    
    if not test_videos:
        print("❌ No test videos available")
        return False
    
    downloader = TikTokVideoDownloader()
    
    # Test the full pipeline method
    video = test_videos[0]  # Use first video
    
    print(f"🎬 Testing full pipeline with: {video['title'][:50]}...")
    
    # This tests the complete download_and_convert_audio method
    audio_path, duration = downloader.download_and_convert_audio(video, index=1)
    
    if audio_path and duration:
        print(f"✅ Full pipeline SUCCESS!")
        print(f"📁 Audio file: {Path(audio_path).name}")
        print(f"⏱️ Duration: {duration:.2f}s")
        
        # Verify file exists and has content
        if Path(audio_path).exists() and Path(audio_path).stat().st_size > 1000:
            print(f"📊 File size: {Path(audio_path).stat().st_size:,} bytes")
            print(f"🎉 Full pipeline test PASSED!")
            
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
    """Run focused tests with real data."""
    
    print("🚀 TikTok Downloader - Real Data Testing")
    print("=" * 60)
    
    # Change to correct directory
    os.chdir(Path(__file__).parent)
    
    tests_passed = 0
    
    # Test 1: System check
    print("✅ Test 1: System Check")
    downloader = TikTokVideoDownloader()
    if downloader.has_ffmpeg and downloader.has_ytdlp:
        print("   ✅ All dependencies available")
        tests_passed += 1
    else:
        print("   ❌ Dependencies missing")
    
    # Test 2: Real URL downloads
    print("\n✅ Test 2: Real URL Downloads")
    if test_direct_download_with_real_urls():
        print("   ✅ Real URL downloads working")
        tests_passed += 1
    else:
        print("   ❌ Real URL downloads failed")
    
    # Test 3: Full pipeline
    print("\n✅ Test 3: Full Pipeline")
    if test_full_pipeline_integration():
        print("   ✅ Full pipeline working")
        tests_passed += 1
    else:
        print("   ❌ Full pipeline failed")
    
    # Summary
    print(f"\n📊 Final Results:")
    print(f"=" * 30)
    print(f"Tests Passed: {tests_passed}/3")
    
    if tests_passed >= 2:
        print(f"🎉 OVERALL SUCCESS!")
        print(f"💡 The downloader is working with real TikTok data")
        return True
    else:
        print(f"⚠️ Some critical tests failed")
        return False

if __name__ == "__main__":
    success = main()
    
    # Clean up test files
    try:
        import shutil
        if Path("./test_output").exists():
            shutil.rmtree("./test_output", ignore_errors=True)
        print("🧹 Cleaned up test files")
    except:
        pass
    
    sys.exit(0 if success else 1)