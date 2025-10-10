#!/usr/bin/env python3
"""
Test script for YouTubeOutputFilterer
Creates test scenarios by modifying manifest records
"""

import json
import shutil
from datetime import datetime
from youtube_output_filterer import YouTubeOutputFilterer

def create_test_manifest():
    """Create a test version of manifest with some unclassified records"""
    
    # Create backup first
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"final_audio_files/manifest.backup_test_{timestamp}.json"
    shutil.copy2("final_audio_files/manifest.json", backup_path)
    print(f"Created backup: {backup_path}")
    
    # Load current manifest
    with open('final_audio_files/manifest.json', 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    records = manifest.get('records', [])
    print(f"Total records: {len(records)}")
    
    # Set first 10 records to classified=false for testing
    test_records_count = min(10, len(records))
    for i in range(test_records_count):
        records[i]['classified'] = False
        # Remove classification_timestamp if it exists
        if 'classification_timestamp' in records[i]:
            del records[i]['classification_timestamp']
    
    # Save modified manifest
    with open('final_audio_files/manifest.json', 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"Set {test_records_count} records to classified=false for testing")
    return backup_path

def restore_manifest(backup_path):
    """Restore manifest from backup"""
    shutil.copy2(backup_path, "final_audio_files/manifest.json")
    print(f"Restored manifest from: {backup_path}")

def test_filterer():
    """Test the filterer functionality"""
    print("\n" + "="*50)
    print("TESTING YOUTUBE OUTPUT FILTERER")
    print("="*50)
    
    # Create test scenario
    backup_path = create_test_manifest()
    
    try:
        # Run the filterer
        print("\nRunning filterer...")
        result = YouTubeOutputFilterer.run_filterer()
        
        print(f"\nTest Results:")
        print(f"  Total processed: {result.total_processed}")
        print(f"  Files kept: {result.files_kept}")
        print(f"  Files deleted: {result.files_deleted}")
        print(f"  Files not found: {result.files_not_found}")
        print(f"  Errors: {result.errors}")
        print(f"  Processing time: {result.processing_time:.2f} seconds")
        
        if result.error_details:
            print(f"\nError details:")
            for error in result.error_details:
                print(f"  - {error}")
        
        # Check final state
        print(f"\nChecking final state...")
        with open('final_audio_files/manifest.json', 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        records = manifest.get('records', [])
        unclassified = [r for r in records if not r.get('classified', False)]
        classified_false = [r for r in records if r.get('classified') == False]
        
        print(f"Remaining unclassified records: {len(unclassified)}")
        print(f"Records with classified=false: {len(classified_false)}")
        
        if classified_false:
            print("Sample record marked as classified=false:")
            sample = classified_false[0]
            print(f"  video_id: {sample.get('video_id')}")
            print(f"  classified: {sample.get('classified')}")
            print(f"  classification_timestamp: {sample.get('classification_timestamp', 'not set')}")
        
    finally:
        # Restore original manifest
        print(f"\nRestoring original manifest...")
        restore_manifest(backup_path)
        print("Test completed!")

if __name__ == "__main__":
    test_filterer()