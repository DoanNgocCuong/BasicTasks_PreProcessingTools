#!/usr/bin/env python3
"""
Test the manifest functionality with the updated TikTok crawler
"""

import sys
import os
from pathlib import Path

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tiktok_video_crawler import TikTokVideoCollector

def test_manifest():
    """Test the manifest loading functionality."""
    print("🔧 Testing manifest functionality...")
    
    try:
        # Initialize the collector
        collector = TikTokVideoCollector()
        
        # Check if manifest file exists
        manifest_file = Path("./final_audio_files/manifest.csv")
        print(f"📋 Manifest file: {manifest_file}")
        print(f"📋 Manifest exists: {manifest_file.exists()}")
        
        if manifest_file.exists():
            print(f"📋 Manifest size: {manifest_file.stat().st_size} bytes")
            
            # Try to read the manifest
            with open(manifest_file, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.strip().split('\n')
                print(f"📋 Manifest lines: {len(lines)}")
                if lines:
                    print(f"📋 Header: {lines[0]}")
                    if len(lines) > 1:
                        print(f"📋 Sample entry: {lines[1]}")
        
        # Test loaded URLs
        downloaded_urls = collector.downloaded_urls
        print(f"📊 Downloaded URLs loaded: {len(downloaded_urls)}")
        if downloaded_urls:
            print(f"📊 Sample downloaded URL: {list(downloaded_urls)[0]}")
        
        print("✅ Manifest test completed successfully!")
        
    except Exception as e:
        print(f"❌ Manifest test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_manifest()