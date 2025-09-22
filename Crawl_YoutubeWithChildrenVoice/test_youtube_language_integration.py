#!/usr/bin/env python3
"""
Test script for YouTube Language Classifier integration

This script tests the integration of the YouTube transcript-based language detection
with the existing audio classifier system.

Author: Le Hoang Minh
"""

import sys
from pathlib import Path
from youtube_language_classifier import YouTubeLanguageClassifier
from youtube_audio_classifier import AudioClassifier


def test_youtube_language_classifier():
    """Test the standalone YouTube language classifier."""
    print("=" * 60)
    print("TESTING YOUTUBE LANGUAGE CLASSIFIER")
    print("=" * 60)
    
    classifier = YouTubeLanguageClassifier()
    
    # Test with a known Vietnamese video (example)
    test_urls = [
        "https://www.youtube.com/watch?v=FcFypeosrJk",  # Vietnamese children video
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # English video (Rick Roll)
    ]
    
    for url in test_urls:
        print(f"\n🔍 Testing URL: {url}")
        result = classifier.detect_language_from_url(url)
        
        if result['error']:
            print(f"❌ Error: {result['error']}")
        else:
            print(f"✅ Video ID: {result['video_id']}")
            print(f"   Language: {result['detected_language']}")
            print(f"   Is Vietnamese: {result['is_vietnamese']}")
            print(f"   Confidence: {result['confidence']}")
            print(f"   Method: {result['method']}")


def test_integrated_classifier():
    """Test the integrated audio classifier with YouTube URL support."""
    print("\n" + "=" * 60)
    print("TESTING INTEGRATED AUDIO CLASSIFIER")
    print("=" * 60)
    
    # Test if the integration works without errors
    try:
        classifier = AudioClassifier()
        print("✅ AudioClassifier initialized successfully")
        
        # Test YouTube URL language detection method
        test_url = "https://www.youtube.com/watch?v=FcFypeosrJk"
        print(f"\n🔍 Testing transcript detection for: {test_url}")
        
        result = classifier.is_vietnamese_from_youtube_url(test_url)
        print(f"✅ Transcript detection result: {result}")
        print("   (Note: Returns True when transcripts unavailable, as per new behavior)")
            
    except Exception as e:
        print(f"❌ Error in integrated classifier: {e}")
        return False
    
    return True


def test_combined_prediction_integration():
    """Test the combined prediction with YouTube URL parameter."""
    print("\n" + "=" * 60)
    print("TESTING COMBINED PREDICTION INTEGRATION")
    print("=" * 60)
    
    try:
        classifier = AudioClassifier()
        
        # Create a dummy audio file path for testing (won't actually process)
        dummy_audio_path = "test_audio.wav"
        test_url = "https://www.youtube.com/watch?v=FcFypeosrJk"
        
        print(f"🔍 Testing combined prediction interface...")
        print(f"   Audio path: {dummy_audio_path}")
        print(f"   YouTube URL: {test_url}")
        
        # This will fail at audio loading but should show the YouTube URL parameter is accepted
        try:
            result = classifier.get_combined_prediction(dummy_audio_path, youtube_url=test_url)
            print(f"✅ Method accepts YouTube URL parameter")
            if 'error' in result:
                print(f"⚠️ Expected error (no audio file): {result['error']}")
        except TypeError as e:
            if "youtube_url" in str(e):
                print(f"❌ YouTube URL parameter not properly integrated: {e}")
                return False
            else:
                print(f"✅ Method accepts YouTube URL parameter (other error: {e})")
        
    except Exception as e:
        print(f"❌ Error in combined prediction test: {e}")
        return False
    
    return True


def main():
    """Main test function."""
    print("YouTube Language Classifier Integration Test")
    print("=" * 60)
    
    success_count = 0
    total_tests = 3
    
    try:
        # Test 1: Standalone YouTube language classifier
        test_youtube_language_classifier()
        success_count += 1
        print("\n✅ Test 1 passed: YouTube language classifier")
    except Exception as e:
        print(f"\n❌ Test 1 failed: {e}")
    
    try:
        # Test 2: Integrated audio classifier
        if test_integrated_classifier():
            success_count += 1
            print("\n✅ Test 2 passed: Integrated audio classifier")
        else:
            print("\n❌ Test 2 failed: Integrated audio classifier")
    except Exception as e:
        print(f"\n❌ Test 2 failed: {e}")
    
    try:
        # Test 3: Combined prediction integration
        if test_combined_prediction_integration():
            success_count += 1
            print("\n✅ Test 3 passed: Combined prediction integration")
        else:
            print("\n❌ Test 3 failed: Combined prediction integration")
    except Exception as e:
        print(f"\n❌ Test 3 failed: {e}")
    
    # Final results
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All tests passed! Integration successful.")
        return 0
    else:
        print("⚠️ Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
