#!/usr/bin/env python3
"""
Test script for TikTok keyword search functionality

This script tests the keyword search implementation to ensure it's working
correctly with the TikTok API.

Author: Generated for TikTok Children's Voice Crawler
Version: 1.0
"""

import sys
import os
from pathlib import Path

# Add current directory to path for imports
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Import required modules
try:
    from tiktok_api_client import TikTokAPIClient
    from env_config import config
    API_AVAILABLE = True
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all required modules and configuration are available")
    API_AVAILABLE = False


def test_keyword_search():
    """Test the keyword search functionality."""
    if not API_AVAILABLE:
        print("❌ Required modules not available, cannot run test")
        return False
    
    print("🧪 Testing TikTok Keyword Search Functionality")
    print("=" * 60)
    
    try:
        # Initialize API client
        print("🔧 Initializing TikTok API client...")
        client = TikTokAPIClient()
        
        # Test keywords (Vietnamese children's content related)
        test_keywords = [
            "trẻ em việt nam",
            "thiếu nhi",
            "bé học nói",
            "trẻ em hát",
            "bé tập đọc",
            "con nít chơi"
        ]
        
        print(f"\n🔍 Testing {len(test_keywords)} keywords:")
        all_results = {}
        
        for i, keyword in enumerate(test_keywords, 1):
            print(f"\n--- Test {i}/{len(test_keywords)}: '{keyword}' ---")
            
            # Test basic search
            print(f"🔍 Searching for '{keyword}' (5 videos)...")
            videos = client.search_videos_by_keyword(keyword, count=5)
            
            if videos:
                print(f"✅ Found {len(videos)} videos")
                
                # Display video details
                for j, video in enumerate(videos, 1):
                    print(f"   {j}. Title: {video['title'][:60]}...")
                    print(f"      Author: @{video['author_username']}")
                    print(f"      Duration: {video['duration']}s")
                    print(f"      Views: {video['play_count']:,}")
                    print(f"      Likes: {video['like_count']:,}")
                    print(f"      URL: {video['url']}")
                    print()
                
                all_results[keyword] = {
                    'success': True,
                    'count': len(videos),
                    'videos': videos
                }
            else:
                print(f"⚠️ No videos found for '{keyword}'")
                all_results[keyword] = {
                    'success': False,
                    'count': 0,
                    'videos': []
                }
        
        # Test pagination
        print(f"\n📄 Testing pagination with keyword 'trẻ em'...")
        paginated_videos = client.search_videos_by_keyword_with_pagination("trẻ em", total_count=15)
        
        if paginated_videos:
            print(f"✅ Paginated search returned {len(paginated_videos)} videos")
            print(f"   First: {paginated_videos[0]['title'][:50]}...")
            print(f"   Last: {paginated_videos[-1]['title'][:50]}...")
        else:
            print(f"⚠️ Pagination test failed")
        
        # Print summary
        print(f"\n📊 Test Summary:")
        print("=" * 40)
        successful_searches = sum(1 for r in all_results.values() if r['success'])
        total_videos_found = sum(r['count'] for r in all_results.values())
        
        print(f"Successful searches: {successful_searches}/{len(test_keywords)}")
        print(f"Total videos found: {total_videos_found}")
        print(f"Success rate: {(successful_searches / len(test_keywords)) * 100:.1f}%")
        
        # Show most successful keywords
        if total_videos_found > 0:
            print(f"\nMost successful keywords:")
            sorted_results = sorted(all_results.items(), key=lambda x: x[1]['count'], reverse=True)
            for keyword, result in sorted_results[:3]:
                if result['count'] > 0:
                    print(f"  '{keyword}': {result['count']} videos")
        
        # API usage stats
        print(f"\n🔧 API Usage Statistics:")
        client.print_api_usage_summary()
        
        return successful_searches > 0
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_specific_vietnamese_keywords():
    """Test with specific Vietnamese children's content keywords."""
    print(f"\n🇻🇳 Testing Vietnamese Children's Content Keywords")
    print("=" * 60)
    
    # Keywords from the config file
    vietnamese_keywords = [
        "bé tập đếm",
        "bé tập đọc", 
        "trẻ em hát",
        "bé học nói",
        "thiếu nhi việt nam",
        "đồng dao việt nam"
    ]
    
    try:
        client = TikTokAPIClient()
        successful_keywords = []
        
        for keyword in vietnamese_keywords:
            print(f"\n🔍 Testing: '{keyword}'")
            videos = client.search_videos_by_keyword(keyword, count=3)
            
            if videos:
                print(f"✅ Found {len(videos)} videos")
                successful_keywords.append(keyword)
                
                # Show best video (highest view count)
                best_video = max(videos, key=lambda v: v.get('play_count', 0))
                print(f"   🌟 Best video: {best_video['title'][:50]}...")
                print(f"      Views: {best_video['play_count']:,}")
                print(f"      Author: @{best_video['author_username']}")
            else:
                print(f"⚠️ No results")
        
        print(f"\n✅ Vietnamese test completed:")
        print(f"   Successful keywords: {len(successful_keywords)}/{len(vietnamese_keywords)}")
        for kw in successful_keywords:
            print(f"   ✓ '{kw}'")
        
        return len(successful_keywords) > 0
        
    except Exception as e:
        print(f"❌ Vietnamese keyword test failed: {e}")
        return False


def main():
    """Main test function."""
    print("🚀 TikTok Keyword Search Test Suite")
    print("This test verifies the keyword search functionality for Vietnamese children's content")
    print()
    
    # Check if API is configured
    if not API_AVAILABLE:
        print("❌ Cannot run tests - API configuration not available")
        print("Please ensure:")
        print("  1. TIKTOK_API_KEY is set in environment variables")
        print("  2. env_config.py is properly configured")
        print("  3. All required modules are installed")
        return
    
    # Run tests
    test_results = []
    
    # Basic keyword search test
    print("🧪 Running basic keyword search test...")
    basic_test_result = test_keyword_search()
    test_results.append(("Basic Keyword Search", basic_test_result))
    
    # Vietnamese-specific test
    print("🧪 Running Vietnamese children's content test...")
    vietnamese_test_result = test_specific_vietnamese_keywords()
    test_results.append(("Vietnamese Content Search", vietnamese_test_result))
    
    # Final summary
    print(f"\n🎯 Final Test Results:")
    print("=" * 50)
    
    all_passed = True
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print(f"\n🎉 All tests passed! Keyword search functionality is working correctly.")
        print(f"The TikTok API client can successfully search for Vietnamese children's content.")
    else:
        print(f"\n⚠️ Some tests failed. Please check API configuration and network connectivity.")
    
    print(f"\n📝 Note: If tests fail, verify:")
    print(f"  1. API key is valid and has quota available")
    print(f"  2. Internet connection is working")
    print(f"  3. TikTok API service is accessible")


if __name__ == "__main__":
    main()