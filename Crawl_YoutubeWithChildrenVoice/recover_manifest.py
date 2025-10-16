#!/usr/bin/env python3
"""
Manifest Recovery Script

This script detects orphaned audio files that exist without manifest entries
and recovers them by adding appropriate manifest records.
"""

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Add the parent directory to Python path for relative imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_config
from src.utils import get_output_manager, get_file_manager


def extract_video_id_from_filename(filename: str) -> Optional[str]:
    """Extract video ID from filename patterns."""
    # Try different patterns
    # Pattern: 0000_ABCDEF123_NoTitle.wav
    parts = filename.split('_')
    if len(parts) >= 2:
        potential_id = parts[1]
        # Video IDs are typically 11 characters
        if len(potential_id) >= 8:
            return potential_id[:11]
    return None


def scan_for_orphaned_files(config, output) -> List[Path]:
    """Scan for audio files that aren't in the manifest."""
    file_manager = get_file_manager()
    final_audio_dir = config.output.final_audio_dir

    if not final_audio_dir.exists():
        output.info("Final audio directory doesn't exist yet")
        return []

    # Load existing manifest
    manifest_file = final_audio_dir / "manifest.json"
    manifest_data = {"records": []}
    if manifest_file.exists():
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            output.info(f"Loaded manifest with {len(manifest_data.get('records', []))} records")
        except Exception as e:
            output.warning(f"Failed to load manifest: {e}")

    # Get all existing manifest paths
    manifest_paths = {record.get('output_path') for record in manifest_data.get('records', []) if record.get('output_path')}

    # Scan for audio files
    orphaned_files = []
    for file_path in final_audio_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in ['.wav', '.mp3', '.m4a']:
            if str(file_path) not in manifest_paths:
                orphaned_files.append(file_path)
                output.debug(f"Found orphaned file: {file_path}")

    output.info(f"Found {len(orphaned_files)} orphaned audio files")
    return orphaned_files


def recover_orphaned_file(file_path: Path, config, output) -> Optional[Dict]:
    """Create a manifest record for an orphaned file."""
    try:
        # Extract video ID from filename
        video_id = extract_video_id_from_filename(file_path.name)
        if not video_id:
            output.warning(f"Could not extract video ID from {file_path.name}")
            return None

        # Get file stats
        stat = file_path.stat()
        file_size = stat.st_size

        # Try to get duration (simplified - would need audio library for accurate duration)
        # For now, we'll set it to 0 and let it be updated later
        duration_seconds = 0.0

        # Create recovery record
        record = {
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "output_path": str(file_path),
            "status": "recovered",
            "timestamp": datetime.now().isoformat() + "Z",
            "duration_seconds": duration_seconds,
            "title": f"Recovered Video {video_id}",
            "language_folder": "unknown",
            "download_index": -1,  # Will be updated when manifest is loaded
            "classified": False,
            "recovered_at": datetime.now().isoformat() + "Z"
        }

        output.info(f"Created recovery record for {video_id}")
        return record

    except Exception as e:
        output.error(f"Failed to recover {file_path}: {e}")
        return None


def update_manifest_with_recoveries(manifest_file: Path, recovery_records: List[Dict], output) -> bool:
    """Update the manifest with recovered records."""
    file_manager = get_file_manager()

    # Load current manifest
    manifest_data = {"total_duration_seconds": 0.0, "records": []}
    if manifest_file.exists():
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
        except Exception as e:
            output.error(f"Failed to load manifest for recovery: {e}")
            return False

    # Update download indices for recovery records
    next_index = len(manifest_data.get('records', []))
    for record in recovery_records:
        record['download_index'] = next_index
        next_index += 1

    # Add recovery records
    manifest_data['records'].extend(recovery_records)

    # Recalculate total duration
    total_duration = sum(record.get('duration_seconds', 0) for record in manifest_data.get('records', []))
    manifest_data['total_duration_seconds'] = total_duration

    # Save manifest atomically
    if file_manager.save_json(manifest_file, manifest_data):
        output.success(f"Successfully recovered {len(recovery_records)} orphaned files")
        return True
    else:
        output.error("Failed to save recovered manifest")
        return False


def main():
    """Main recovery function."""
    parser = argparse.ArgumentParser(description="Recover orphaned audio files in manifest")
    parser.add_argument("--config", help="Path to config file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be recovered without making changes")

    args = parser.parse_args()

    # Load config
    try:
        config = load_config(config_file=args.config)
    except Exception as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 1

    output = get_output_manager()
    if config.logging.debug_mode:
        output.set_level("DEBUG")

    output.info("=== Manifest Recovery Tool ===")

    # Scan for orphaned files
    orphaned_files = scan_for_orphaned_files(config, output)

    if not orphaned_files:
        output.info("No orphaned files found")
        return 0

    # Create recovery records
    recovery_records = []
    for file_path in orphaned_files:
        if isinstance(file_path, Path):
            record = recover_orphaned_file(file_path, config, output)
            if record:
                recovery_records.append(record)

    if not recovery_records:
        output.warning("No recovery records could be created")
        return 1

    output.info(f"Would recover {len(recovery_records)} files")

    if args.dry_run:
        output.info("Dry run - not making changes")
        for record in recovery_records:
            output.info(f"  Would recover: {record['video_id']} -> {record['output_path']}")
        return 0

    # Update manifest
    manifest_file = config.output.final_audio_dir / "manifest.json"
    if update_manifest_with_recoveries(manifest_file, recovery_records, output):
        output.success("Recovery completed successfully")
        return 0
    else:
        output.error("Recovery failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())