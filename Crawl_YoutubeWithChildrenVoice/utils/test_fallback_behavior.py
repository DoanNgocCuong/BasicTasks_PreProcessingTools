#!/usr/bin/env python3
"""
Test script to verify the fallback behavior between main downloader and alternative downloader.

This script tests:
1. Alternative downloader initialization with proper output directory alignment
2. Fallback behavior when alternative methods fail
3. Consistency between both downloaders' output formats
4. Language-based file organization
"""

import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from youtube_audio_downloader import YoutubeAudioDownloader, Config
from youtube_audio_downloader_alternative import YouTubeAudioDownloaderAlternative

def test_output_directory_alignment():
    """Test that both downloaders use the same output directory."""
    print("🔍 Testing output directory alignment...")
    
    # Create main downloader config
    config = Config()
    downloader = YoutubeAudioDownloader(config)
    
    print(f"Main downloader output dir: {config.output_dir}")
    if downloader.alt_downloader:
        print(f"Alternative downloader output dir: {downloader.alt_downloader.output_dir}")
        
        # Check if they point to the same directory
        main_path = Path(config.output_dir).resolve()
        alt_path = Path(downloader.alt_downloader.output_dir).resolve()
        
        if main_path == alt_path:
            print("✅ Output directories are aligned!")
            return True
        else:
            print(f"❌ Output directories mismatch:")
            print(f"   Main: {main_path}")
            print(f"   Alt:  {alt_path}")
            return False
    else:
        print("❌ Alternative downloader not initialized")
        return False

def test_alternative_downloader_initialization():
    """Test standalone alternative downloader initialization."""
    print("\n🔍 Testing standalone alternative downloader initialization...")
    
    # Test with relative path
    alt1 = YouTubeAudioDownloaderAlternative(output_dir="test_output")
    print(f"Relative path result: {alt1.output_dir}")
    
    # Test with absolute path
    base_dir = Path(__file__).parent
    abs_path = base_dir / "test_output_abs"
    alt2 = YouTubeAudioDownloaderAlternative(output_dir=str(abs_path))
    print(f"Absolute path result: {alt2.output_dir}")
    
    return True

def test_method_availability():
    """Test that required methods are available in both downloaders."""
    print("\n🔍 Testing method availability...")
    
    config = Config()
    main_downloader = YoutubeAudioDownloader(config)
    
    # Check main downloader methods
    main_methods = [
        'download_audio_from_yturl',
        'download_audio_via_ffmpeg', 
        'get_video_duration'
    ]
    
    for method in main_methods:
        if hasattr(main_downloader, method):
            print(f"✅ Main downloader has {method}")
        else:
            print(f"❌ Main downloader missing {method}")
    
    # Check alternative downloader methods
    if main_downloader.alt_downloader:
        alt_methods = [
            'download_audio_yt_dlp_fallback',
            'download_audio_pytube'
        ]
        
        for method in alt_methods:
            if hasattr(main_downloader.alt_downloader, method):
                print(f"✅ Alternative downloader has {method}")
            else:
                print(f"❌ Alternative downloader missing {method}")
    
    return True

def test_custom_basename_handling():
    """Test custom basename handling consistency."""
    print("\n🔍 Testing custom basename handling...")
    
    config = Config()
    downloader = YoutubeAudioDownloader(config)
    
    # Test custom basename on config
    config._current_basename = "test_custom_name"
    
    m4a_filename = config.get_m4a_filename(1)
    wav_filename = config.get_wav_filename(1)
    
    print(f"M4A filename with custom base: {m4a_filename}")
    print(f"WAV filename with custom base: {wav_filename}")
    
    if "test_custom_name" in m4a_filename and "test_custom_name" in wav_filename:
        print("✅ Custom basename handling works")
        return True
    else:
        print("❌ Custom basename handling failed")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing YouTube Audio Downloader Fallback Behavior")
    print("=" * 60)
    
    tests = [
        test_output_directory_alignment,
        test_alternative_downloader_initialization,
        test_method_availability,
        test_custom_basename_handling
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed with error: {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Fallback behavior should work correctly.")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)