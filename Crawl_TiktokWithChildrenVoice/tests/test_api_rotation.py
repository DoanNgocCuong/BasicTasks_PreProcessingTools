#!/usr/bin/env python3
"""
Test script to validate API key rotation functionality
"""

import time
from tiktok_api_client import TikTokAPIClient

def test_key_rotation():
    """Test API key rotation by making rapid requests"""
    print("🧪 Testing API Key Rotation...")
    
    # Initialize client
    client = TikTokAPIClient()
    print(f"✅ Client initialized with {len(client.api_keys)} API keys")
    print(f"🔑 Starting with key index: {client.current_api_key_index}")
    print(f"🔑 Current key: ...{client.api_key[-4:]}")
    
    # Make multiple requests to trigger rate limiting
    test_keyword = "test"
    
    for i in range(5):
        print(f"\n🔄 Test request {i + 1}/5...")
        try:
            # Search for videos - this should trigger rate limiting
            videos = client.search_videos_by_keyword(test_keyword, count=10, cursor=0)
            print(f"✅ Request {i + 1} succeeded: {len(videos) if videos else 0} videos")
            
        except Exception as e:
            print(f"❌ Request {i + 1} failed: {e}")
        
        # Check current key after each request
        print(f"🔑 Current key index: {client.current_api_key_index}")
        print(f"🔑 Current key: ...{client.api_key[-4:]}")
        
        # Show stats
        stats = client.get_api_usage_stats()
        print(f"📊 Requests made: {stats['requests_made']}")
        print(f"📊 Rate limits: {stats['quota_exceeded_count']}")
        print(f"📊 Keys used: {stats['current_api_key_index'] + 1}/{stats['total_api_keys']}")
        
        # Small delay between requests
        time.sleep(1)
    
    print(f"\n🎯 Final Test Results:")
    client.print_api_usage_summary()

if __name__ == "__main__":
    test_key_rotation()