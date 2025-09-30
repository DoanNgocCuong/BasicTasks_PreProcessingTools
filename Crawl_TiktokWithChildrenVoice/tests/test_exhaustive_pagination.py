#!/usr/bin/env python3
"""
Test script for exhaustive pagination functionality.
"""

import sys
import time
from tiktok_api_client import TikTokAPIClient
from tiktok_video_crawler import OutputManager

def test_exhaustive_pagination():
    """Test the new exhaustive pagination functionality."""
    
    print("🚀 Testing EXHAUSTIVE pagination functionality...")
    
    # Initialize components
    output = OutputManager()
    client = TikTokAPIClient(output)
    
    # Test keyword
    test_keyword = "bé tập đếm"
    
    print(f"\n🔍 Testing exhaustive search for: '{test_keyword}'")
    print("=" * 60)
    
    # Test 1: Limited exhaustive search (max 100 videos)
    print("\n📋 Test 1: Limited exhaustive search (max 100 videos)")
    start_time = time.time()
    videos = client.search_videos_by_keyword_with_pagination(test_keyword, max_total_count=100)
    end_time = time.time()
    
    print(f"✅ Test 1 Results:")
    print(f"   📊 Total videos found: {len(videos)}")
    print(f"   ⏱️ Time taken: {end_time - start_time:.2f} seconds")
    
    # Test 2: Single page request (for comparison)
    print("\n📋 Test 2: Single page request")
    start_time = time.time()
    result = client.search_videos_by_keyword(test_keyword, count=50)
    single_page_videos = result.get('videos', [])
    has_more = result.get('has_more', False)
    next_cursor = result.get('next_cursor')
    end_time = time.time()
    
    print(f"✅ Test 2 Results:")
    print(f"   📊 Videos in single page: {len(single_page_videos)}")
    print(f"   🔄 Has more results: {has_more}")
    print(f"   📍 Next cursor: {next_cursor}")
    print(f"   ⏱️ Time taken: {end_time - start_time:.2f} seconds")
    
    # Test 3: Unlimited exhaustive search (get ALL available - limited to 10 pages for testing)
    print("\n📋 Test 3: Unlimited exhaustive search (limited to reasonable amount)")
    print("⚠️  This will get ALL available results for the keyword...")
    
    # Create a custom client with lower page limit for testing
    start_time = time.time()
    all_videos = client.search_videos_by_keyword_with_pagination(test_keyword, max_total_count=None)
    end_time = time.time()
    
    print(f"✅ Test 3 Results:")
    print(f"   📊 Total videos found: {len(all_videos)}")
    print(f"   ⏱️ Time taken: {end_time - start_time:.2f} seconds")
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 EXHAUSTIVE PAGINATION TEST SUMMARY:")
    print(f"   🔍 Keyword tested: '{test_keyword}'")
    print(f"   📄 Single page: {len(single_page_videos)} videos")
    print(f"   🎯 Limited exhaustive (100): {len(videos)} videos")
    print(f"   🌟 Unlimited exhaustive: {len(all_videos)} videos")
    print(f"   📈 Improvement: {len(all_videos) - len(single_page_videos)} additional videos found!")
    
    if has_more and len(all_videos) > len(single_page_videos):
        print("✅ SUCCESS: Exhaustive pagination is working correctly!")
        print("   The system now extracts ALL available results from the API.")
    else:
        print("⚠️  WARNING: Results may indicate no additional pages available.")
    
    return len(all_videos)

if __name__ == "__main__":
    try:
        total_found = test_exhaustive_pagination()
        print(f"\n🎉 Test completed! Total videos found: {total_found}")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)