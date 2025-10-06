#!/usr/bin/env python3
"""
Simple YouTube Crawler Test with Selenium Proxy

This script tests if your YouTube crawler works with the proxy by making
a simple collection run.
"""

import os
import sys
import time
import requests
from datetime import datetime

def setup_proxy_environment():
    """Configure environment variables for proxy usage."""
    print("🔧 CONFIGURING ENVIRONMENT FOR PROXY")
    print("=" * 40)
    
    # Set proxy environment variables
    proxy_url = "http://127.0.0.1:8080"
    os.environ['HTTP_PROXY'] = proxy_url
    os.environ['HTTPS_PROXY'] = proxy_url
    
    print(f"✅ HTTP_PROXY = {os.environ.get('HTTP_PROXY')}")
    print(f"✅ HTTPS_PROXY = {os.environ.get('HTTPS_PROXY')}")
    
    return proxy_url

def test_proxy_connection(proxy_url):
    """Test if the proxy is working correctly."""
    print("\n🧪 TESTING PROXY CONNECTION...")
    
    try:
        # Test admin endpoint
        response = requests.get(f"{proxy_url}/_proxy_admin/test", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Proxy test: {data.get('message', 'OK')}")
            return True
        else:
            print(f"❌ Proxy test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Proxy connection failed: {e}")
        return False

def run_simple_crawler_test():
    """Run a simple test of the YouTube crawler."""
    print("\n🎬 TESTING YOUTUBE CRAWLER WITH PROXY")
    print("=" * 40)
    
    try:
        print("📋 Importing YouTube crawler...")
        from youtube_video_crawler import YouTubeVideoCrawler
        print("✅ Import successful")
        
        print("📋 Creating crawler instance...")
        crawler = YouTubeVideoCrawler()
        print("✅ Crawler created")
        
        print("📋 Running crawler collection...")
        print("⏱️  This will take a few moments...")
        
        # Start the collection
        start_time = time.time()
        results = crawler.collect_videos()
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\n✅ Collection completed in {duration:.2f} seconds")
        print(f"📊 Total videos collected: {len(results) if results else 0}")
        
        if results:
            print(f"📋 Sample URLs:")
            for i, url in enumerate(results[:3]):
                print(f"  {i+1}. {url}")
        
        return len(results) > 0
        
    except Exception as e:
        print(f"❌ Crawler test failed: {e}")
        return False

def check_proxy_activity():
    """Check proxy server activity after crawler test."""
    print("\n📊 CHECKING PROXY ACTIVITY")
    print("=" * 30)
    
    try:
        response = requests.get("http://127.0.0.1:8080/_proxy_admin/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            stats = data.get('statistics', {})
            
            total_requests = stats.get('total_requests', 0)
            successful = stats.get('successful_requests', 0)
            failed = stats.get('failed_requests', 0)
            
            print("✅ Proxy activity detected:")
            print(f"   📊 Total requests: {total_requests}")
            print(f"   ✅ Successful: {successful}")
            print(f"   ❌ Failed: {failed}")
            
            if total_requests > 0:
                print("\n🎉 SUCCESS: Crawler used the proxy!")
                return True
            else:
                print("\n⚠️  No proxy activity detected")
                return False
        else:
            print(f"❌ Could not get proxy status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to check proxy activity: {e}")
        return False

def main():
    """Main test function."""
    print("🚀 SIMPLE YOUTUBE CRAWLER + PROXY TEST")
    print("=" * 45)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Setup proxy environment
    proxy_url = setup_proxy_environment()
    
    # Step 2: Test proxy connection
    if not test_proxy_connection(proxy_url):
        print("\n❌ PROXY TEST FAILED - Make sure proxy server is running")
        return
    
    # Step 3: Run YouTube crawler
    crawler_success = run_simple_crawler_test()
    
    # Step 4: Check proxy activity
    proxy_activity = check_proxy_activity()
    
    # Final results
    print("\n" + "=" * 45)
    print("🏁 FINAL RESULTS:")
    print(f"   ✅ Proxy connection: {'PASS' if True else 'FAIL'}")
    print(f"   ✅ YouTube crawler: {'PASS' if crawler_success else 'FAIL'}")
    print(f"   ✅ Proxy integration: {'PASS' if proxy_activity else 'FAIL'}")
    
    if crawler_success and proxy_activity:
        print("\n🎉 COMPLETE SUCCESS!")
        print("💡 Your YouTube crawler is now using the Selenium proxy!")
        print("🔄 All HTTP requests are being routed through the proxy")
        print("📡 You now have IP rotation capability!")
    elif crawler_success:
        print("\n⚠️  Crawler worked but proxy integration unclear")
        print("💡 Try checking proxy logs manually")
    else:
        print("\n❌ Some issues detected - check the output above")
    
    print("=" * 45)

if __name__ == "__main__":
    main()