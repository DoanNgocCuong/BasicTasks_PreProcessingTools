#!/usr/bin/env python3
"""
Test manifest structure validation
"""
import json
from pathlib import Path

def test_manifest_structure():
    """Test manifest structure and fields."""
    print("Testing manifest structure...")
    
    # Load manifest and check structure
    manifest_path = Path('final_audio_files/manifest.json')
    with manifest_path.open('r', encoding='utf-8') as f:
        data = json.load(f)

    records = data.get('records', [])
    total = len(records)
    classified = sum(1 for r in records if r.get('classified', False))
    unclassified = total - classified

    print('✅ Manifest structure valid:')
    print(f'   Total records: {total}')
    print(f'   Classified: {classified}')
    print(f'   Unclassified: {unclassified}')
    print(f'   Total duration: {data.get("total_duration_seconds", 0):.1f}s')

    # Check first record structure
    if records:
        sample = records[0]
        required_fields = ['video_id', 'url', 'output_path', 'status', 'timestamp', 'duration_seconds', 'title', 'classified']
        missing = [f for f in required_fields if f not in sample]
        if missing:
            print(f'❌ Missing fields in sample record: {missing}')
            return False
        else:
            print('✅ Sample record has all required fields')
            print(f'   Sample classified: {sample.get("classified")}')
            print(f'   Sample has classification_timestamp: {"classification_timestamp" in sample}')
            return True
    
    return False

if __name__ == "__main__":
    test_manifest_structure()