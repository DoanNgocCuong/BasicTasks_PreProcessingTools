#!/usr/bin/env python3
"""
Simple Manifest Migration Script: Set 'classified' Field to True

This script sets the 'classified' field to True for all records in manifest.json.

Author: Le Hoang Minh
"""

import json
from pathlib import Path


def main():
    """Main function to set classified field to True for all records."""
    script_dir = Path(__file__).parent
    manifest_path = script_dir / "final_audio_files" / "manifest.json"

    if not manifest_path.exists():
        print(f"❌ Manifest file not found: {manifest_path}")
        return False

    try:
        with manifest_path.open('r', encoding='utf-8') as f:
            manifest_data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load manifest: {e}")
        return False

    records = manifest_data.get('records', [])
    for record in records:
        record['classified'] = True

    try:
        with manifest_path.open('w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Successfully set 'classified' to True for {len(records)} records")
        return True
    except Exception as e:
        print(f"❌ Failed to save manifest: {e}")
        return False


if __name__ == "__main__":
    main()
