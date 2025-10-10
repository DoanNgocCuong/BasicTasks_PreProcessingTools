#!/usr/bin/env python3
"""
Test script for audio classification functionality.
This creates a few test entries in manifest to verify the classification workflow.
"""

import json
import shutil
from datetime import datetime
from pathlib import Path


def create_test_manifest():
    """Create a test manifest with some unclassified entries."""
    script_dir = Path(__file__).parent
    test_manifest_path = script_dir / "final_audio_files" / "test_manifest.json"
    original_manifest_path = script_dir / "final_audio_files" / "manifest.json"
    
    # Load original manifest
    with original_manifest_path.open('r', encoding='utf-8') as f:
        original_data = json.load(f)
    
    # Create test data with first 3 entries, mark them as unclassified
    test_data = {
        "total_duration_seconds": 0,
        "records": []
    }
    
    # Take first 3 records and mark as unclassified for testing
    for i, record in enumerate(original_data["records"][:3]):
        test_record = record.copy()
        test_record["classified"] = False  # Mark as unclassified
        if "classification_timestamp" in test_record:
            del test_record["classification_timestamp"]
        test_data["records"].append(test_record)
        test_data["total_duration_seconds"] += record.get("duration_seconds", 0)
    
    # Save test manifest
    with test_manifest_path.open('w', encoding='utf-8') as f:
        json.dump(test_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Test manifest created: {test_manifest_path}")
    print(f"📊 Test records: {len(test_data['records'])}")
    return test_manifest_path


def cleanup_test_manifest():
    """Remove test manifest file."""
    script_dir = Path(__file__).parent
    test_manifest_path = script_dir / "final_audio_files" / "test_manifest.json"
    
    if test_manifest_path.exists():
        test_manifest_path.unlink()
        print(f"🗑️  Cleaned up test manifest: {test_manifest_path}")


if __name__ == "__main__":
    print("🧪 Audio Classification Test Setup")
    print("=" * 50)
    
    # Create test manifest
    test_path = create_test_manifest()
    
    print(f"\n🎯 To test the audio classification, run:")
    print(f"python -c \"")
    print(f"from youtube_output_validator import AudioFileClassifier")
    print(f"from pathlib import Path")
    print(f"classifier = AudioFileClassifier(Path('{test_path}'), max_workers=2)")
    print(f"classifier.validate_and_classify_audio_files()\"")
    
    print(f"\n⚠️  Remember to clean up afterwards by running:")
    print(f"python {__file__} --cleanup")
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--cleanup":
        cleanup_test_manifest()