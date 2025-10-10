#!/usr/bin/env python3
"""
Test adding a sample record to crawler manifest and testing merge functionality.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

def create_test_record():
    """Create a test record for crawler manifest."""
    return {
        "video_id": "TEST123456789",
        "url": "https://www.youtube.com/watch?v=TEST123456789",
        "output_path": "D:\\code\\BasicTasks_PreProcessingTools\\Crawl_YoutubeWithChildrenVoice\\crawler_outputs\\audio_files\\test_audio_20250101_0001_TEST123456789.wav",
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": 60.5,
        "title": "Test Video for Dual Manifest System",
        "language_folder": "vietnamese",
        "download_index": 1,
        "classified": False
    }

def add_test_record_to_crawler_manifest():
    """Add a test record to crawler manifest."""
    script_dir = Path(__file__).parent
    crawler_manifest_path = script_dir / "crawler_outputs" / "crawler_manifest.json"
    
    print(f"📝 Adding test record to: {crawler_manifest_path}")
    
    # Load current manifest
    try:
        with open(crawler_manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error loading manifest: {e}")
        return False
    
    # Add test record
    test_record = create_test_record()
    data.setdefault('records', []).append(test_record)
    data['total_duration_seconds'] = data.get('total_duration_seconds', 0.0) + test_record['duration_seconds']
    
    # Save updated manifest
    try:
        with open(crawler_manifest_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("✅ Test record added successfully")
        print(f"   Video ID: {test_record['video_id']}")
        print(f"   Title: {test_record['title']}")
        print(f"   Duration: {test_record['duration_seconds']} seconds")
        return True
    except Exception as e:
        print(f"Error saving manifest: {e}")
        return False

def check_for_duplicates():
    """Check if test record would create duplicates."""
    script_dir = Path(__file__).parent
    main_manifest_path = script_dir / "final_audio_files" / "manifest.json"
    
    print(f"\n🔍 Checking for duplicates in main manifest...")
    
    test_record = create_test_record()
    test_video_id = test_record['video_id']
    test_url = test_record['url']
    
    # Load main manifest
    try:
        with open(main_manifest_path, 'r', encoding='utf-8') as f:
            main_data = json.load(f)
        
        main_video_ids = {r.get('video_id') for r in main_data.get('records', []) if r.get('video_id')}
        main_urls = {r.get('url') for r in main_data.get('records', []) if r.get('url')}
        
        is_duplicate_id = test_video_id in main_video_ids
        is_duplicate_url = test_url in main_urls
        
        print(f"   Test video ID '{test_video_id}' in main manifest: {is_duplicate_id}")
        print(f"   Test URL in main manifest: {is_duplicate_url}")
        
        if is_duplicate_id or is_duplicate_url:
            print("⚠️  Duplicate detected - merge should fail safely")
        else:
            print("✅ No duplicates - merge should succeed")
        
        return not (is_duplicate_id or is_duplicate_url)
        
    except Exception as e:
        print(f"Error checking duplicates: {e}")
        return False

def main():
    """Test the dual manifest system with a real record."""
    print("🧪 Testing Dual Manifest System with Test Record")
    print("=" * 50)
    
    # Add test record
    if not add_test_record_to_crawler_manifest():
        return 1
    
    # Check for duplicates
    no_duplicates = check_for_duplicates()
    
    print(f"\n📋 Test record created. Now you can test:")
    print(f"   1. Run: python merge_crawler_manifest.py --dry-run")
    print(f"   2. Check if duplicate detection works correctly")
    print(f"   3. If no duplicates, test actual merge")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())