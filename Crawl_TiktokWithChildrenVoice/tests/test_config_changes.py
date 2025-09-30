#!/usr/bin/env python3
"""
Quick verification script to test the download method configuration changes.
"""

import json
from pathlib import Path

def test_config_changes():
    """Test that configuration changes were applied correctly."""
    print("🧪 Testing Configuration Changes...")
    
    # Test 1: Check crawler_config.json file
    config_file = Path("crawler_config.json")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        download_method = config_data.get('download_method', 'unknown')
        print(f"✅ crawler_config.json download_method: '{download_method}'")
        
        if download_method == "yt_dlp":
            print("✅ Configuration file correctly uses yt-dlp as default")
        else:
            print(f"❌ Expected 'yt_dlp', found '{download_method}'")
    else:
        print("❌ crawler_config.json not found")
    
    # Test 2: Check default values in code
    print("\n🔍 Checking code defaults...")
    
    try:
        with open("tiktok_video_crawler.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check dataclass default
        if 'download_method: str = "yt_dlp"' in content:
            print("✅ CrawlerConfig dataclass default: yt_dlp")
        else:
            print("❌ CrawlerConfig dataclass still has old default")
        
        # Check config loading default
        if "'download_method', 'yt_dlp'" in content:
            print("✅ Config loading default: yt_dlp")
        else:
            print("❌ Config loading still has old default")
        
        # Check default config creation
        if '"download_method": "yt_dlp"' in content:
            print("✅ Default config creation: yt_dlp")
        else:
            print("❌ Default config creation still has old value")
            
    except Exception as e:
        print(f"❌ Error reading crawler file: {e}")
    
    # Test 3: Check downloader priority changes
    print("\n🔍 Checking downloader priority...")
    
    try:
        with open("tiktok_video_downloader.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check method priority in comments and logs
        if "Method 1: yt-dlp" in content and "Method 2: TikTok API23" in content:
            print("✅ Download method priority: yt-dlp first, API23 fallback")
        else:
            print("❌ Download method priority not updated correctly")
            
        # Check docstring
        if "1. yt-dlp (primary method" in content:
            print("✅ Docstring updated with new priority")
        else:
            print("❌ Docstring not updated")
            
    except Exception as e:
        print(f"❌ Error reading downloader file: {e}")
    
    print("\n🎯 Summary:")
    print("The configuration has been updated to use yt-dlp as the primary download method")
    print("with TikTok API23 as the fallback, instead of the previous order.")

if __name__ == "__main__":
    test_config_changes()