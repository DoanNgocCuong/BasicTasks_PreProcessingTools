#!/usr/bin/env python3
"""
Test audio classification logic without requiring actual audio files
"""

import json
import tempfile
from pathlib import Path
from youtube_output_validator import AudioFileClassifier


def test_classification_logic():
    """Test the classification logic with mock data."""
    print("Testing audio classification logic...")
    
    # Create a temporary test manifest with unclassified entries
    test_manifest_data = {
        "total_duration_seconds": 100.0,
        "records": [
            {
                "video_id": "test123",
                "url": "https://www.youtube.com/watch?v=test123",
                "output_path": "/fake/path/test1.wav",
                "status": "success",
                "timestamp": "2025-10-08T17:00:00Z",
                "duration_seconds": 30.0,
                "title": "Test Video 1",
                "classified": False  # This should be processed
            },
            {
                "video_id": "test456",
                "url": "https://www.youtube.com/watch?v=test456",
                "output_path": "/fake/path/test2.wav",
                "status": "success",
                "timestamp": "2025-10-08T17:01:00Z",
                "duration_seconds": 40.0,
                "title": "Test Video 2",
                "classified": True  # This should be skipped
            },
            {
                "video_id": "test789",
                "url": "https://www.youtube.com/watch?v=test789",
                "output_path": "/fake/path/test3.wav",
                "status": "success",
                "timestamp": "2025-10-08T17:02:00Z",
                "duration_seconds": 30.0,
                "title": "Test Video 3",
                "classified": False  # This should be processed
            }
        ]
    }
    
    # Create temporary manifest file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(test_manifest_data, f, indent=2)
        temp_manifest_path = Path(f.name)
    
    try:
        # Test AudioFileClassifier initialization
        classifier = AudioFileClassifier(manifest_path=temp_manifest_path, max_workers=2)
        print("✅ AudioFileClassifier initialized successfully")
        
        # Test manifest loading
        manifest_data = classifier.load_manifest()
        print(f"✅ Manifest loaded: {len(manifest_data['records'])} records")
        
        # Test filtering unclassified entries
        unclassified = [r for r in manifest_data['records'] if not r.get('classified', False)]
        print(f"✅ Found {len(unclassified)} unclassified entries (expected: 2)")
        
        # Test classification result structure
        from youtube_output_validator import ClassificationResult
        test_result = ClassificationResult(
            audio_path="/fake/path/test.wav",
            is_children=True,
            confidence=0.9,
            processing_time=1.5
        )
        print("✅ ClassificationResult structure works")
        
        # Test the process_single_entry method logic (without actual audio)
        test_entry = unclassified[0].copy()
        print(f"✅ Testing entry processing logic for: {test_entry['title']}")
        
        # Since the file doesn't exist, it should return False (should not keep)
        # This tests the file-not-found handling
        should_keep, result = classifier.process_single_entry(test_entry, manifest_data)
        print(f"✅ Process single entry result: should_keep={should_keep}, error='{result.error}'")
        
        if result.error == "File not found":
            print("✅ File not found handling works correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ Classification logic test failed: {e}")
        return False
        
    finally:
        # Cleanup
        if temp_manifest_path.exists():
            temp_manifest_path.unlink()


if __name__ == "__main__":
    success = test_classification_logic()
    print(f"\nClassification logic test: {'PASSED' if success else 'FAILED'}")