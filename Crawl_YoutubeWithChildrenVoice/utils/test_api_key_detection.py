#!/usr/bin/env python3
"""
Quick test script to verify YouTube API key detection.
"""

import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_env_config():
    """Test env_config API key detection."""
    print("🔍 Testing env_config API key detection...")
    try:
        from env_config import config as env_config
        
        print("✅ env_config imported successfully")
        
        # Test API keys property
        try:
            api_keys = env_config.YOUTUBE_API_KEYS
            print(f"🔑 Found {len(api_keys)} API key(s):")
            for i, key in enumerate(api_keys, 1):
                print(f"   Key {i}: {key[:10]}...{key[-4:]}")
            return api_keys
        except Exception as e:
            print(f"❌ Error getting API keys: {e}")
            return []
            
    except ImportError as e:
        print(f"❌ Cannot import env_config: {e}")
        return []

def test_direct_env_vars():
    """Test direct environment variable access."""
    print("\n🔍 Testing direct environment variables...")
    
    env_vars = ['YOUTUBE_API_KEY', 'YOUTUBE_API_KEY_1', 'YOUTUBE_API_KEY_2', 'YOUTUBE_API_KEYS']
    found_keys = []
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value[:10]}...{value[-4:]}")
            found_keys.append(value)
        else:
            print(f"❌ {var}: Not found")
    
    return found_keys

def test_downloader_api_detection():
    """Test the actual downloader API detection."""
    print("\n🔍 Testing downloader API detection...")
    try:
        from youtube_audio_downloader import YoutubeAudioDownloader, Config
        
        config = Config()
        downloader = YoutubeAudioDownloader(config)
        
        if downloader.youtube_service:
            print("✅ YouTube API service initialized successfully!")
            if downloader.youtube_api_key:
                print(f"🔑 API key detected: {downloader.youtube_api_key[:10]}...{downloader.youtube_api_key[-4:]}")
            return True
        else:
            print("❌ YouTube API service not initialized")
            print(f"🔑 API key value: {downloader.youtube_api_key}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing downloader: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing YouTube API Key Detection")
    print("=" * 50)
    
    # Test 1: env_config
    env_config_keys = test_env_config()
    
    # Test 2: Direct environment variables  
    direct_env_keys = test_direct_env_vars()
    
    # Test 3: Downloader detection
    downloader_success = test_downloader_api_detection()
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"   env_config keys found: {len(env_config_keys)}")
    print(f"   Direct env vars found: {len(direct_env_keys)}")
    print(f"   Downloader API initialized: {'✅' if downloader_success else '❌'}")
    
    if downloader_success:
        print("\n🎉 API key detection is working correctly!")
    else:
        print("\n⚠️ API key detection needs troubleshooting.")
        print("💡 Check that your .env file is in the correct location")
        print("💡 Verify API key format (should start with 'AIza')")

if __name__ == "__main__":
    main()