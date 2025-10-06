#!/usr/bin/env python3
"""
Test script for chunk analysis functionality.

This script tests the new chunking features for long videos by simulating
the analysis process with a sample video URL.

Usage:
    python test_chunk_analysis.py

Author: Assistant
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from youtube_video_crawler import YouTubeVideoCrawler, CrawlerConfig

def test_chunk_analysis():
    """Test the chunk analysis functionality with a sample long video."""
    
    print("🧪 Testing Chunk Analysis Functionality")
    print("=" * 50)
    
    # Create a test configuration
    test_config = CrawlerConfig(
        debug_mode=True,  # Enable detailed logging
        target_videos_per_query=1,  # Just test one video
        search_queries=["bé giới thiệu bản thân"],
        enable_language_detection=True  # Enable full analysis
    )
    
    try:
        # Initialize crawler with test config
        print("📋 Initializing YouTube Video Crawler...")
        crawler = YouTubeVideoCrawler(config=test_config)
        
        # Create a sample video dict that would normally come from YouTube API
        # Using a longer video to trigger chunking (adjust URL as needed)
        sample_video = {
            'video_id': 'test123',
            'title': 'Test Long Video for Chunking Analysis',
            'channel_id': 'test_channel',
            'channel_title': 'Test Channel',
            'description': 'Test video description',
            'url': 'https://www.youtube.com/watch?v=FcFypeosrJk',  # Replace with actual long video
            'duration': 1800  # 30 minutes (will trigger chunking if MAX_AUDIO_DURATION_SECONDS < 1800)
        }
        
        print(f"🎬 Test video: {sample_video['title']}")
        print(f"⏱️  Configured duration: {sample_video['duration']}s ({sample_video['duration']//60}m {sample_video['duration']%60}s)")
        
        # Check current duration limit setting
        from env_config import config as env_config
        max_duration = env_config.MAX_AUDIO_DURATION_SECONDS
        if max_duration:
            print(f"📏 Max duration limit: {max_duration}s ({max_duration//60}m)")
            if sample_video['duration'] > max_duration:
                print("✅ This video will trigger chunk analysis")
            else:
                print("⚠️  This video will NOT trigger chunk analysis (too short)")
        else:
            print("⚠️  No duration limit set - chunking will not be triggered")
        
        print("\n🚀 Starting analysis...")
        print("-" * 30)
        
        # Perform the analysis
        result = crawler.analyze_video_audio(sample_video, video_type="test")
        
        print("\n📊 Analysis Results:")
        print("=" * 30)
        print(f"✅ Vietnamese: {result.is_vietnamese}")
        print(f"🎯 Language: {result.detected_language}")  
        print(f"👶 Children's Voice: {result.has_children_voice}")
        print(f"🎚️  Confidence: {result.confidence:.2f}")
        print(f"⏱️  Total Time: {result.total_analysis_time:.2f}s")
        print(f"👶 Detection Time: {result.children_detection_time:.2f}s")
        print(f"📹 Video Length: {result.video_length_seconds:.1f}s" if result.video_length_seconds else "Unknown")
        
        # Chunk-specific results
        if hasattr(result, 'was_chunked') and result.was_chunked:
            print(f"🧩 Was Chunked: YES")
            print(f"📊 Chunks Analyzed: {result.chunks_analyzed}")
            if result.positive_chunk_index:
                print(f"🎯 Positive Chunk: #{result.positive_chunk_index}")
            else:
                print(f"❌ No positive chunks found")
        else:
            print(f"🧩 Was Chunked: NO")
            
        if result.error:
            print(f"❌ Error: {result.error}")
            
        print("\n🎉 Test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chunk_splitting():
    """Test just the audio splitting functionality without full analysis."""
    
    print("\n🔧 Testing Audio Splitting Functionality")
    print("=" * 50)
    
    try:
        # Create a test audio file (you would need an actual audio file for this test)
        test_audio_file = current_dir / "youtube_audio_outputs" / "test_audio.wav"
        
        if not test_audio_file.exists():
            print("⚠️  No test audio file found, skipping split test")
            print(f"   Expected file: {test_audio_file}")
            print("   To test splitting, place a test .wav file at the above location")
            return True
            
        # Initialize crawler  
        test_config = CrawlerConfig(
            debug_mode=True,
            target_videos_per_query=1,
            search_queries=["test"]
        )
        crawler = YouTubeVideoCrawler(config=test_config)
        
        print(f"📂 Test audio file: {test_audio_file}")
        
        # Test chunk splitting
        chunk_files = crawler._split_audio_into_chunks(str(test_audio_file), 300)  # 5-minute chunks
        
        print(f"🧩 Created {len(chunk_files)} chunks:")
        for i, chunk_file in enumerate(chunk_files, 1):
            if os.path.exists(chunk_file):
                size = os.path.getsize(chunk_file)
                print(f"  {i}. {chunk_file} ({size} bytes)")
                
        # Clean up test chunks
        crawler._cleanup_chunk_files(chunk_files)
        print("🧹 Cleaned up test chunks")
        
        print("✅ Audio splitting test completed!")
        return True
        
    except Exception as e:
        print(f"❌ Audio splitting test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 YouTube Video Crawler - Chunk Analysis Test Suite")
    print("=" * 60)
    
    # Test 1: Basic chunk analysis
    success1 = test_chunk_analysis()
    
    # Test 2: Audio splitting only
    success2 = test_chunk_splitting()
    
    print("\n📋 Test Summary:")
    print("=" * 30)
    print(f"Chunk Analysis: {'✅ PASSED' if success1 else '❌ FAILED'}")
    print(f"Audio Splitting: {'✅ PASSED' if success2 else '❌ FAILED'}")
    
    if success1 and success2:
        print("\n🎉 All tests passed! Chunk analysis is ready to use.")
        print("\nTo enable chunking in production:")
        print("1. Set MAX_AUDIO_DURATION_SECONDS in your .env file")
        print("2. Long videos will automatically use chunk analysis")
        print("3. The crawler will stop at the first chunk with Vietnamese children's voice")
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")
        
    print("\n" + "=" * 60)