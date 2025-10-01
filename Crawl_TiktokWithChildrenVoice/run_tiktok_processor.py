#!/usr/bin/env python3
"""
TikTok Video Processor Runner

This script runs the complete TikTok video processing pipeline:
1. Resyncs manifest.csv with actual downloaded files
2. Downloads any missing videos from the collected URLs

Usage:
    python run_tiktok_processor.py
"""

import os
import sys
from pathlib import Path

# Add current directory to path to import tiktok_video_downloader
sys.path.append(str(Path(__file__).parent))

from tiktok_video_downloader import TikTokVideoDownloader

def main():
    """Run the complete TikTok processing pipeline."""
    
    # Define paths
    script_dir = Path(__file__).parent
    manifest_path = script_dir / "final_audio_files" / "manifest.csv"
    audio_directory = script_dir / "final_audio_files"
    urls_file = script_dir / "tiktok_url_outputs" / "multi_query_collected_video_urls.txt"
    
    # Check if files exist
    if not manifest_path.exists():
        print(f"❌ Manifest file not found: {manifest_path}")
        return
    
    if not urls_file.exists():
        print(f"❌ URLs file not found: {urls_file}")
        return
    
    if not audio_directory.exists():
        print(f"❌ Audio directory not found: {audio_directory}")
        return
    
    print("🚀 Starting TikTok Video Processing Pipeline...")
    print(f"📁 Manifest: {manifest_path}")
    print(f"📁 Audio Directory: {audio_directory}")
    print(f"📁 URLs File: {urls_file}")
    print()
    
    try:
        # Initialize downloader
        downloader = TikTokVideoDownloader()
        
        # Run the full process
        downloader.run_full_process(
            manifest_path=str(manifest_path),
            audio_directory=str(audio_directory),
            urls_file=str(urls_file)
        )
        
        print("\n🎉 Processing completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
