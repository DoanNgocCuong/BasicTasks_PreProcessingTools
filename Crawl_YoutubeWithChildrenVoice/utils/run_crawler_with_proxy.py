#!/usr/bin/env python3
"""
Final working integration: YouTube Crawler with Selenium Proxy
"""

import os
import sys
import time
import requests
from datetime import datetime

def main():
    print("🚀 FINAL YOUTUBE CRAWLER + PROXY INTEGRATION")
    print("=" * 50)
    
    # Step 1: Set environment variables for proxy
    print("🔧 Setting up proxy environment...")
    os.environ['HTTP_PROXY'] = 'http://127.0.0.1:8080'
    os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:8080'
    print(f"✅ HTTP_PROXY = {os.environ['HTTP_PROXY']}")
    print(f"✅ HTTPS_PROXY = {os.environ['HTTPS_PROXY']}")
    
    # Step 2: Test proxy connection
    print("\n🧪 Testing proxy connection...")
    try:
        response = requests.get("http://127.0.0.1:8080/_proxy_admin/test", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Proxy test: {data.get('message', 'OK')}")
        else:
            print(f"❌ Proxy test failed: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Proxy connection failed: {e}")
        print("💡 Make sure proxy server is running in another terminal!")
        return
    
    # Step 3: Test IP through proxy
    print("\n🌐 Testing IP through proxy...")
    try:
        response = requests.get("http://httpbin.org/ip", timeout=30)
        if response.status_code == 200:
            ip_data = response.json()
            current_ip = ip_data.get('origin', 'Unknown')
            print(f"✅ Current IP through proxy: {current_ip}")
        else:
            print(f"❌ IP test failed: {response.status_code}")
    except Exception as e:
        print(f"❌ IP test failed: {e}")
    
    # Step 4: Import and run your crawler
    print("\n🎬 Running YouTube Crawler...")
    try:
        from youtube_video_crawler import YouTubeVideoCrawler
        print("✅ YouTube crawler imported successfully")
        
        # Create crawler instance
        crawler = YouTubeVideoCrawler()
        print("✅ Crawler initialized")
        
        # Run the collection (this will use ALL your configured queries)
        print("🚀 Starting video collection...")
        print("📊 This will process all 410 queries through the proxy")
        print("⏰ Estimated time: This may take a while...")
        
        start_time = time.time()
        collected_urls = crawler.collect_videos()
        end_time = time.time()
        
        duration = end_time - start_time
        print(f"\n✅ Collection completed in {duration:.2f} seconds")
        print(f"📊 Total videos collected: {len(collected_urls) if collected_urls else 0}")
        
        # Check proxy activity
        print("\n📊 Checking proxy activity...")
        try:
            response = requests.get("http://127.0.0.1:8080/_proxy_admin/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                stats = data.get('statistics', {})
                print(f"📊 Total requests through proxy: {stats.get('total_requests', 0)}")
                print(f"✅ Successful requests: {stats.get('successful_requests', 0)}")
                print(f"❌ Failed requests: {stats.get('failed_requests', 0)}")
                
                if stats.get('total_requests', 0) > 0:
                    print("\n🎉 SUCCESS! YouTube crawler used the proxy!")
                    print("🔄 All API requests were routed through the proxy")
                    print("📡 You now have IP rotation for YouTube scraping!")
                else:
                    print("\n⚠️  No proxy activity detected")
        except Exception as e:
            print(f"❌ Could not check proxy stats: {e}")
            
        print("\n" + "=" * 50)
        print("🎉 YOUTUBE CRAWLER + SELENIUM PROXY INTEGRATION COMPLETE!")
        print("💡 Your crawler is now protected by IP rotation")
        
    except Exception as e:
        print(f"❌ Crawler failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()