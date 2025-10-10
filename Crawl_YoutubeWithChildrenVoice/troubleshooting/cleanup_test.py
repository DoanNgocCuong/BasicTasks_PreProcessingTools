#!/usr/bin/env python3
"""
Clean up test records from the dual manifest system test.
"""

import json
from pathlib import Path

def clean_test_record():
    """Remove test record from main manifest and clear crawler manifest."""
    script_dir = Path(__file__).parent
    main_manifest_path = script_dir / "final_audio_files" / "manifest.json"
    crawler_manifest_path = script_dir / "crawler_outputs" / "crawler_manifest.json"
    
    print("🧹 Cleaning up test records...")
    
    # Clean main manifest
    try:
        with open(main_manifest_path, 'r', encoding='utf-8') as f:
            main_data = json.load(f)
        
        original_count = len(main_data.get('records', []))
        
        # Remove test record
        main_data['records'] = [
            r for r in main_data.get('records', [])
            if r.get('video_id') != 'TEST123456789'
        ]
        
        # Update totals
        new_count = len(main_data['records'])
        main_data['total_duration_seconds'] = sum(
            r.get('duration_seconds', 0) for r in main_data['records']
        )
        
        with open(main_manifest_path, 'w', encoding='utf-8') as f:
            json.dump(main_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Cleaned main manifest: {original_count} → {new_count} records")
        
    except Exception as e:
        print(f"❌ Error cleaning main manifest: {e}")
    
    # Clear crawler manifest
    try:
        empty_data = {
            "total_duration_seconds": 0.0,
            "records": []
        }
        
        with open(crawler_manifest_path, 'w', encoding='utf-8') as f:
            json.dump(empty_data, f, ensure_ascii=False, indent=2)
        
        print("✅ Cleared crawler manifest")
        
    except Exception as e:
        print(f"❌ Error clearing crawler manifest: {e}")

if __name__ == "__main__":
    clean_test_record()
    print("\n🎉 Test cleanup completed!")
    print("📋 The dual manifest system is now ready for production use.")