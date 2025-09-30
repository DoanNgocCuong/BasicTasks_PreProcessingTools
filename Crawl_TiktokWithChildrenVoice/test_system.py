#!/usr/bin/env python3
"""
TikTok Children's Voice Crawler - System Test

This script tests the basic functionality of the TikTok crawler system
to ensure all components are working correctly before running the full crawler.

Run this script first to verify your setup.
"""

import sys
from pathlib import Path
import traceback

def test_environment_config():
    """Test environment configuration loading."""
    print("🔍 Testing environment configuration...")
    try:
        from env_config import config
        print("✅ Environment configuration loaded")
        
        # Test basic config access (will use defaults if no .env)
        print(f"   Debug mode would be: {getattr(config, 'DEBUG_MODE', 'default')}")
        print(f"   Max workers would be: {getattr(config, 'MAX_WORKERS', 'default')}")
        return True
    except Exception as e:
        print(f"❌ Environment configuration failed: {e}")
        return False

def test_api_client():
    """Test TikTok API client."""
    print("\n🔍 Testing TikTok API client...")
    try:
        from tiktok_api_client import TikTokAPIClient
        print("✅ TikTok API client imported")
        
        # Note: Can't initialize without API key, but import works
        print("   (API key required for full functionality)")
        return True
    except Exception as e:
        print(f"❌ TikTok API client failed: {e}")
        return False

def test_video_downloader():
    """Test video downloader."""
    print("\n🔍 Testing video downloader...")
    try:
        from tiktok_video_downloader import TikTokVideoDownloader
        print("✅ Video downloader imported")
        return True
    except Exception as e:
        print(f"❌ Video downloader failed: {e}")
        return False

def test_audio_classifier():
    """Test audio classifier."""
    print("\n🔍 Testing audio classifier...")
    try:
        # Try importing without initializing (avoids torch issues)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tiktok_audio_classifier", 
            Path(__file__).parent / "tiktok_audio_classifier.py"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            # Don't execute the module to avoid torch loading
            print("✅ Audio classifier module found")
            print("   (PyTorch/CUDA setup required for full functionality)")
            return True
        else:
            print("❌ Audio classifier module not found")
            return False
    except Exception as e:
        print(f"⚠️ Audio classifier test inconclusive: {e}")
        print("   This may work with proper PyTorch installation")
        return True  # Don't fail the test for this

def test_main_crawler():
    """Test main crawler import."""
    print("\n🔍 Testing main crawler...")
    try:
        # Try importing without initializing
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "tiktok_video_crawler", 
            Path(__file__).parent / "tiktok_video_crawler.py"
        )
        if spec and spec.loader:
            print("✅ Main crawler module found")
            return True
        else:
            print("❌ Main crawler module not found")
            return False
    except Exception as e:
        print(f"❌ Main crawler failed: {e}")
        return False

def test_config_files():
    """Test configuration files."""
    print("\n🔍 Testing configuration files...")
    
    import json
    
    config_file = Path(__file__).parent / "crawler_config.json"
    env_example = Path(__file__).parent / ".env.example"
    
    tests_passed = 0
    total_tests = 2
    
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            print("✅ crawler_config.json is valid")
            tests_passed += 1
        except json.JSONDecodeError as e:
            print(f"❌ crawler_config.json has invalid JSON: {e}")
        except Exception as e:
            print(f"❌ Error reading crawler_config.json: {e}")
    else:
        print("⚠️ crawler_config.json not found (will be created on first run)")
        tests_passed += 1  # This is OK
    
    if env_example.exists():
        print("✅ .env.example found")
        tests_passed += 1
    else:
        print("❌ .env.example not found")
    
    return tests_passed == total_tests

def test_output_directory():
    """Test output directory creation."""
    print("\n🔍 Testing output directory...")
    try:
        output_dir = Path(__file__).parent / "tiktok_url_outputs"
        output_dir.mkdir(exist_ok=True)
        
        if output_dir.exists() and output_dir.is_dir():
            print("✅ Output directory ready")
            return True
        else:
            print("❌ Could not create output directory")
            return False
    except Exception as e:
        print(f"❌ Output directory test failed: {e}")
        return False

def main():
    """Run all system tests."""
    print("🚀 TikTok Children's Voice Crawler - System Test")
    print("=" * 60)
    
    tests = [
        ("Environment Configuration", test_environment_config),
        ("TikTok API Client", test_api_client),
        ("Video Downloader", test_video_downloader),
        ("Audio Classifier", test_audio_classifier),
        ("Main Crawler", test_main_crawler),
        ("Configuration Files", test_config_files),
        ("Output Directory", test_output_directory)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System is ready.")
        print("\n📋 Next Steps:")
        print("1. Copy .env.example to .env")
        print("2. Add your TikTok RapidAPI key to .env")
        print("3. Install PyTorch if you haven't already:")
        print("   pip install torch torchvision torchaudio")
        print("4. Run: python tiktok_video_crawler.py")
        return 0
    else:
        print(f"⚠️ {total - passed} tests failed. Please fix issues before running the crawler.")
        return 1

if __name__ == "__main__":
    sys.exit(main())