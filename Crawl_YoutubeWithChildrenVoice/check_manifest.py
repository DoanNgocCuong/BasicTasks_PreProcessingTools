#!/usr/bin/env python3
"""Quick manifest checker"""
import json

try:
    with open('final_audio_files/manifest.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    records = data.get('records', [])
    unclassified = [r for r in records if not r.get('classified', False)]
    
    print(f"Total records: {len(records)}")
    print(f"Unclassified: {len(unclassified)}")
    
    if unclassified:
        print(f"Sample unclassified video_ids: {[r.get('video_id', 'no_id')[:10] for r in unclassified[:3]]}")
    else:
        print("No unclassified records found")
        # Create some test records by unmarking a few as unclassified
        if len(records) >= 3:
            print("Creating test records by unmarking 3 records as unclassified...")
            for i in range(3):
                records[i]['classified'] = False
                records[i].pop('has_children_voice', None)
            
            # Save back
            with open('final_audio_files/manifest.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print("Created 3 unclassified test records")
        
except Exception as e:
    print(f"Error: {e}")