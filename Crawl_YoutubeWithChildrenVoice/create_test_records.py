#!/usr/bin/env python3
"""Create more test records for better concurrent testing"""
import json

try:
    with open('final_audio_files/manifest.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    records = data.get('records', [])
    
    # Create 10 unclassified test records
    count = 0
    for i, record in enumerate(records):
        if count >= 10:
            break
        record['classified'] = False
        record.pop('has_children_voice', None)
        record.pop('classification_timestamp', None)
        count += 1
    
    # Save back
    with open('final_audio_files/manifest.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Created {count} unclassified test records")
    
    # Verify
    unclassified = [r for r in records if not r.get('classified', False)]
    print(f"Total unclassified records: {len(unclassified)}")
    
except Exception as e:
    print(f"Error: {e}")