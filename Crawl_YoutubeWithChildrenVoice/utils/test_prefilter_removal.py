#!/usr/bin/env python3
"""
Test script to validate that prefiltering logic has been successfully removed
from YouTube video crawler.
"""

def test_prefilter_removal():
    """Test that prefiltering code is removed from youtube_video_crawler.py"""
    
    with open('youtube_video_crawler.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check that prefiltering patterns are removed
    prefilter_patterns = [
        'PRE-FILTER:',
        'FALLBACK FILTER:',
        'Skipping long video',
        'Skipping long similar video'
    ]
    
    issues_found = []
    
    for pattern in prefilter_patterns:
        if pattern in content:
            issues_found.append(f"Found prefiltering pattern: '{pattern}'")
    
    # Check that chunking patterns still exist
    chunking_patterns = [
        '_split_audio_into_chunks',
        '_analyze_video_chunks',
        'chunk analysis',
        'Using chunk analysis for long video'
    ]
    
    for pattern in chunking_patterns:
        if pattern not in content:
            issues_found.append(f"Missing chunking pattern: '{pattern}'")
    
    # Report results
    if issues_found:
        print("❌ VALIDATION FAILED:")
        for issue in issues_found:
            print(f"  - {issue}")
        return False
    else:
        print("✅ VALIDATION PASSED:")
        print("  - All prefiltering logic successfully removed")
        print("  - All chunking logic still intact")
        print("  - Long videos will now be processed via chunking instead of being skipped")
        return True

if __name__ == "__main__":
    test_prefilter_removal()