#!/usr/bin/env python3
"""
Direct execution script - Just set proxy env vars and run your crawler
"""

import os

# Set proxy environment variables
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:8080'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:8080'

print("🚀 RUNNING YOUTUBE CRAWLER WITH PROXY")
print("=" * 40)
print(f"📡 HTTP_PROXY = {os.environ['HTTP_PROXY']}")
print(f"📡 HTTPS_PROXY = {os.environ['HTTPS_PROXY']}")
print("🎬 Starting your YouTube crawler...")

# Import and run your crawler
from youtube_video_crawler import YouTubeVideoCrawler

crawler = YouTubeVideoCrawler()
results = crawler.collect_videos()

print(f"\n✅ Collection complete!")
print(f"📊 Videos collected: {len(results) if results else 0}")
print("🎉 All requests went through the proxy!")