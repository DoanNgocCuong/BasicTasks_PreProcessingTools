#!/usr/bin/env python3
"""
Debug script to investigate the integration between youtube_video_crawler.py and youtube_audio_downloader.py
"""

import os
import sys
import json
import subprocess
from pathlib import Path

def check_files_and_paths():
    """Check all relevant files and paths"""
    base_dir = Path(__file__).parent
    
    print("=== FILE SYSTEM CHECK ===")
    print(f"Base directory: {base_dir}")
    
    # Check crawler script
    crawler_path = base_dir / "youtube_video_crawler.py"
    print(f"Crawler script exists: {crawler_path.exists()} - {crawler_path}")
    
    # Check downloader script
    downloader_path = base_dir / "youtube_audio_downloader.py"
    print(f"Downloader script exists: {downloader_path.exists()} - {downloader_path}")
    
    # Check URLs directory and file
    urls_dir = base_dir / "youtube_url_outputs"
    urls_file = urls_dir / "collected_video_urls.txt"
    print(f"URLs directory exists: {urls_dir.exists()} - {urls_dir}")
    print(f"URLs file exists: {urls_file.exists()} - {urls_file}")
    
    if urls_file.exists():
        with open(urls_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip().startswith('http')]
        print(f"Number of URLs in file: {len(urls)}")
        if urls:
            print("First few URLs:")
            for i, url in enumerate(urls[:3]):
                print(f"  {i+1}. {url}")
    
    # Check final audio files directory
    final_audio_dir = base_dir / "final_audio_files"
    print(f"Final audio directory exists: {final_audio_dir.exists()} - {final_audio_dir}")
    
    if final_audio_dir.exists():
        # Check language subdirectories
        vietnamese_dir = final_audio_dir / "vietnamese"
        unknown_dir = final_audio_dir / "unknown"
        print(f"Vietnamese dir exists: {vietnamese_dir.exists()} - {vietnamese_dir}")
        print(f"Unknown dir exists: {unknown_dir.exists()} - {unknown_dir}")
        
        # Check manifests
        main_manifest = final_audio_dir / "manifest.json"
        vietnamese_manifest = vietnamese_dir / "manifest.json" if vietnamese_dir.exists() else None
        unknown_manifest = unknown_dir / "manifest.json" if unknown_dir.exists() else None
        
        print(f"Main manifest exists: {main_manifest.exists()} - {main_manifest}")
        if vietnamese_manifest:
            print(f"Vietnamese manifest exists: {vietnamese_manifest.exists()} - {vietnamese_manifest}")
        if unknown_manifest:
            print(f"Unknown manifest exists: {unknown_manifest.exists()} - {unknown_manifest}")
        
        # Count audio files
        if vietnamese_dir.exists():
            audio_files = list(vietnamese_dir.glob("*.wav"))
            print(f"Vietnamese audio files: {len(audio_files)}")
        if unknown_dir.exists():
            audio_files = list(unknown_dir.glob("*.wav"))
            print(f"Unknown audio files: {len(audio_files)}")

def test_downloader_directly():
    """Test running the downloader script directly"""
    base_dir = Path(__file__).parent
    downloader_path = base_dir / "youtube_audio_downloader.py"
    
    print("\n=== TESTING DOWNLOADER DIRECTLY ===")
    
    if not downloader_path.exists():
        print("❌ Downloader script not found")
        return
    
    # Create a test language mapping
    test_mapping = {
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ": "unknown"  # Rick Roll for testing
    }
    
    mapping_file = base_dir / "test_language_mapping.json"
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(test_mapping, f, indent=2, ensure_ascii=False)
    
    print(f"Created test mapping file: {mapping_file}")
    
    # Test with --help to see if script is working
    print("\n--- Testing downloader with --help ---")
    try:
        result = subprocess.run([sys.executable, str(downloader_path), '--help'], 
                              capture_output=True, text=True, timeout=30)
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout[:500])
        if result.stderr:
            print("STDERR:")
            print(result.stderr[:500])
    except subprocess.TimeoutExpired:
        print("❌ Downloader script timed out")
    except Exception as e:
        print(f"❌ Error running downloader: {e}")
    
    # Test with language mapping
    print("\n--- Testing downloader with language mapping ---")
    try:
        result = subprocess.run([sys.executable, str(downloader_path), '--language-mapping', str(mapping_file)], 
                              capture_output=True, text=True, timeout=60)
        print(f"Return code: {result.returncode}")
        if result.stdout:
            print("STDOUT:")
            print(result.stdout[:1000])
        if result.stderr:
            print("STDERR:")
            print(result.stderr[:1000])
    except subprocess.TimeoutExpired:
        print("❌ Downloader script timed out")
    except Exception as e:
        print(f"❌ Error running downloader: {e}")
    
    # Clean up
    try:
        mapping_file.unlink()
        print(f"Cleaned up test mapping file")
    except:
        pass

def analyze_crawler_downloader_flow():
    """Analyze the flow between crawler and downloader"""
    print("\n=== ANALYZING CRAWLER-DOWNLOADER FLOW ===")
    
    # Read the crawler script to understand the flow
    base_dir = Path(__file__).parent
    crawler_path = base_dir / "youtube_video_crawler.py"
    
    if not crawler_path.exists():
        print("❌ Crawler script not found")
        return
    
    # Look for the _run_audio_downloader_script method
    with open(crawler_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find where the counter is incremented
    print("Checking where _check_and_run_downloader is called:")
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '_check_and_run_downloader()' in line:
            print(f"Line {i+1}: {line.strip()}")
            # Show context
            start = max(0, i-2)
            end = min(len(lines), i+3)
            print("  Context:")
            for j in range(start, end):
                marker = ">>>" if j == i else "   "
                print(f"  {marker} {j+1}: {lines[j]}")
            print()

def main():
    """Main function"""
    print("YouTube Crawler-Downloader Integration Debug Tool")
    print("=" * 60)
    
    check_files_and_paths()
    test_downloader_directly()
    analyze_crawler_downloader_flow()
    
    print("\n=== RECOMMENDATIONS ===")
    print("1. Check if the downloader script has proper permissions")
    print("2. Verify that all required dependencies are installed")
    print("3. Check if the working directory is correct when the script is called")
    print("4. Verify that the URLs file is being written correctly by the crawler")
    print("5. Check if there are any import errors in the downloader script")

if __name__ == "__main__":
    main()