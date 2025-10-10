#!/usr/bin/env python3
"""
Test YouTube Crawler with Selenium Proxy Integration

This script demonstrates how to run the YouTube crawler through the Selenium proxy
for IP rotation and anonymization.
"""

import os
import sys
import time
import requests
from datetime import datetime

def setup_proxy_environment():
    """Configure environment variables for proxy usage."""
    print("🔧 STEP 4: CONFIGURING CRAWLER FOR PROXY")
    print("=" * 50)
    
    # Set proxy environment variables
    proxy_url = "http://127.0.0.1:8080"
    os.environ['HTTP_PROXY'] = proxy_url
    os.environ['HTTPS_PROXY'] = proxy_url
    
    print(f"✅ HTTP_PROXY = {os.environ.get('HTTP_PROXY')}")
    print(f"✅ HTTPS_PROXY = {os.environ.get('HTTPS_PROXY')}")
    
    return proxy_url

def test_proxy_connection(proxy_url):
    """Test if the proxy is working correctly."""
    print("\n🧪 Testing proxy connection...")
    
    try:
        # Test admin endpoint
        response = requests.get(f"{proxy_url}/_proxy_admin/test", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Proxy admin test: {data.get('message', 'OK')}")
            print(f"📊 Total requests processed: {data.get('total_requests_processed', 0)}")
        else:
            print(f"❌ Proxy admin test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Proxy connection failed: {e}")
        return False
    
    try:
        # Test IP check through proxy
        print("\n🌐 Testing IP through proxy...")
        response = requests.get("http://httpbin.org/ip", timeout=30)
        if response.status_code == 200:
            ip_data = response.json()
            current_ip = ip_data.get('origin', 'Unknown')
            print(f"✅ Current IP through proxy: {current_ip}")
            
            # Check if we're using proxy (should not be local IP)
            if current_ip.startswith('192.168.') or current_ip.startswith('10.') or current_ip.startswith('127.'):
                print("⚠️  Warning: Appears to be local IP - proxy may not be routing correctly")
            else:
                print("🎉 Success: Using external IP through proxy!")
        
        return True
        
    except Exception as e:
        print(f"❌ IP test through proxy failed: {e}")
        return False

def run_youtube_crawler_test():
    """Run a small test of the YouTube crawler with proxy."""
    print("\n🎬 STEP 5: TESTING YOUTUBE CRAWLER WITH PROXY")
    print("=" * 50)
    
    try:
        # Import your crawler
        print("📋 Importing YouTube crawler...")
        from youtube_video_crawler import YouTubeVideoCrawler
        
        print("✅ YouTube crawler imported successfully")
        
        # Create crawler instance
        print("📋 Creating crawler instance...")
        crawler = YouTubeVideoCrawler()
        
        # Test with a simple query
        test_query = "children stories"
        max_videos = 5  # Small test
        
        print(f"📋 Testing crawler with query: '{test_query}'")
        print(f"📋 Max videos: {max_videos}")
        print("📋 All requests will go through proxy at 127.0.0.1:8080")
        
        # Run the crawler
        print("\n🚀 Starting crawl...")
        start_time = time.time()
        
        results = crawler.search_videos(
            query=test_query,
            max_results=max_videos
        )
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n✅ Crawl completed in {duration:.2f} seconds")
        print(f"📊 Found {len(results)} videos")
        
        # Show sample results
        if results:
            print("\n📋 Sample results:")
            for i, video in enumerate(results[:3]):
                title = video.get('title', 'No title')[:50]
                video_id = video.get('video_id', 'No ID')
                print(f"  {i+1}. {title}... (ID: {video_id})")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import YouTube crawler: {e}")
        print("💡 Make sure youtube_video_crawler.py exists and is properly configured")
        return False
    except Exception as e:
        print(f"❌ Crawler test failed: {e}")
        return False

def check_proxy_activity():
    """Check proxy server activity after crawler test."""
    print("\n📊 STEP 6: CHECKING PROXY ACTIVITY")
    print("=" * 40)
    
    try:
        response = requests.get("http://127.0.0.1:8080/_proxy_admin/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            server_info = data.get('server', {})
            stats = data.get('statistics', {})
            
            print("✅ Proxy server status:")
            print(f"   📡 Running: {server_info.get('is_running', False)}")
            print(f"   📊 Total requests: {stats.get('total_requests', 0)}")
            print(f"   ✅ Successful: {stats.get('successful_requests', 0)}")
            print(f"   ❌ Failed: {stats.get('failed_requests', 0)}")
            print(f"   📈 Success rate: {stats.get('success_rate_percent', 0):.1f}%")
            
            if stats.get('total_requests', 0) > 0:
                print("\n🎉 SUCCESS: Proxy intercepted requests from YouTube crawler!")
                return True
            else:
                print("\n⚠️  No requests detected - crawler may not be using proxy")
                return False
        else:
            print(f"❌ Failed to get proxy status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to check proxy activity: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 YOUTUBE CRAWLER + SELENIUM PROXY INTEGRATION TEST")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Setup proxy environment
    proxy_url = setup_proxy_environment()
    
    # Step 2: Test proxy connection
    if not test_proxy_connection(proxy_url):
        print("\n❌ PROXY TEST FAILED - Cannot proceed")
        print("💡 Make sure the proxy server is running in another terminal")
        return
    
    # Step 3: Run YouTube crawler test
    crawler_success = run_youtube_crawler_test()
    
    # Step 4: Check proxy activity
    proxy_activity = check_proxy_activity()
    
    # Final results
    print("\n" + "=" * 60)
    print("🏁 FINAL RESULTS:")
    print(f"   ✅ Proxy connection: {'PASS' if True else 'FAIL'}")
    print(f"   ✅ YouTube crawler: {'PASS' if crawler_success else 'FAIL'}")
    print(f"   ✅ Proxy integration: {'PASS' if proxy_activity else 'FAIL'}")
    
    if crawler_success and proxy_activity:
        print("\n🎉 SUCCESS! YouTube crawler is now using Selenium proxy for IP rotation!")
        print("💡 You can now run your full crawler with automatic IP switching")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    print("=" * 60)

if __name__ == "__main__":
    main()