#!/usr/bin/env python3
"""
Test audio downloader modification
"""

import inspect


def test_audio_downloader_modification():
    """Test that audio downloader includes classified field."""
    print("Testing audio downloader modification...")
    
    try:
        # Read the audio downloader source file directly
        with open('youtube_audio_downloader.py', 'r', encoding='utf-8') as f:
            source = f.read()
        
        if "'classified': False" in source:
            print("✅ Audio downloader includes 'classified': False for new entries")
        else:
            print("❌ Audio downloader missing classified field")
            return False
        
        # Check if it's in the right context (record creation)
        if "'classified': False  # New entries need to be classified" in source:
            print("✅ Classified field properly commented and positioned")
        else:
            print("⚠️  Classified field found but may not be in ideal location")
        
        # Also check the record structure
        if "'video_id'" in source and "'output_path'" in source:
            print("✅ Record structure includes required fields")
        else:
            print("❌ Record structure missing required fields")
            return False
            
        print("✅ Audio downloader modification verified")
        return True
        
    except Exception as e:
        print(f"❌ Audio downloader test failed: {e}")
        return False


if __name__ == "__main__":
    success = test_audio_downloader_modification()
    print(f"\nAudio downloader test: {'PASSED' if success else 'FAILED'}")