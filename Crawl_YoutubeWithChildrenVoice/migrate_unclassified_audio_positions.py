#!/usr/bin/env python3
"""
Script to migrate audio files with "classified": false from language folders to "unclassified" folder.

This script reads the manifest.json file, finds all entries where "classified" is set to false,
and moves those audio files from their current language-based folder structure to a new
"unclassified" folder.
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migrate_unclassified_audio.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_manifest(manifest_path: str) -> Dict:
    """Load the manifest.json file."""
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Manifest file not found: {manifest_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing manifest JSON: {e}")
        raise


def save_manifest(manifest_data: Dict, manifest_path: str, backup: bool = True) -> None:
    """Save the updated manifest.json file with optional backup."""
    if backup:
        backup_path = f"{manifest_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(manifest_path, backup_path)
        logger.info(f"Created backup: {backup_path}")
    
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)
    logger.info(f"Updated manifest saved to: {manifest_path}")


def find_unclassified_entries(manifest_data: Dict) -> List[Dict]:
    """Find all entries where 'classified' is false."""
    unclassified_entries = []
    
    for record in manifest_data.get('records', []):
        if record.get('classified') is False:
            unclassified_entries.append(record)
    
    return unclassified_entries


def create_unclassified_folder(base_path: str) -> str:
    """Create the unclassified folder if it doesn't exist."""
    unclassified_path = os.path.join(base_path, 'unclassified')
    os.makedirs(unclassified_path, exist_ok=True)
    logger.info(f"Ensured unclassified folder exists: {unclassified_path}")
    return unclassified_path


def get_new_file_path(original_path: str, unclassified_folder: str) -> str:
    """Generate the new file path in the unclassified folder."""
    filename = os.path.basename(original_path)
    return os.path.join(unclassified_folder, filename)


def migrate_audio_file(old_path: str, new_path: str, dry_run: bool = False) -> bool:
    """Migrate a single audio file from old path to new path."""
    try:
        if not os.path.exists(old_path):
            logger.warning(f"Source file not found: {old_path}")
            return False
        
        if os.path.exists(new_path):
            logger.warning(f"Destination file already exists: {new_path}")
            return False
        
        if dry_run:
            logger.info(f"[DRY RUN] Would move: {old_path} -> {new_path}")
            return True
        else:
            shutil.move(old_path, new_path)
            logger.info(f"Moved: {old_path} -> {new_path}")
            return True
            
    except Exception as e:
        logger.error(f"Error moving file {old_path} to {new_path}: {e}")
        return False


def update_manifest_paths(manifest_data: Dict, moved_files: Dict[str, str]) -> None:
    """Update the output_path in manifest records for moved files."""
    for record in manifest_data.get('records', []):
        old_path = record.get('output_path', '')
        if old_path in moved_files:
            record['output_path'] = moved_files[old_path]
            logger.info(f"Updated manifest path: {os.path.basename(old_path)}")


def main():
    """Main function to migrate unclassified audio files."""
    # Configuration
    script_dir = os.path.dirname(os.path.abspath(__file__))
    manifest_path = os.path.join(script_dir, 'final_audio_files', 'manifest.json')
    base_audio_path = os.path.join(script_dir, 'final_audio_files')
    
    # Command line argument parsing (simple)
    import sys
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        logger.info("Running in DRY RUN mode - no files will be moved")
    
    try:
        # Load manifest
        logger.info(f"Loading manifest from: {manifest_path}")
        manifest_data = load_manifest(manifest_path)
        
        # Find unclassified entries
        unclassified_entries = find_unclassified_entries(manifest_data)
        logger.info(f"Found {len(unclassified_entries)} unclassified entries")
        
        if not unclassified_entries:
            logger.info("No unclassified entries found. Nothing to migrate.")
            return
        
        # Create unclassified folder
        unclassified_folder = create_unclassified_folder(base_audio_path)
        
        # Track moved files for manifest update
        moved_files = {}
        successful_moves = 0
        failed_moves = 0
        
        # Process each unclassified entry
        for entry in unclassified_entries:
            old_path = entry.get('output_path', '')
            if not old_path:
                logger.warning("Entry missing output_path, skipping")
                continue
            
            new_path = get_new_file_path(old_path, unclassified_folder)
            
            if migrate_audio_file(old_path, new_path, dry_run):
                moved_files[old_path] = new_path
                successful_moves += 1
            else:
                failed_moves += 1
        
        # Update manifest if not dry run and files were moved
        if not dry_run and moved_files:
            update_manifest_paths(manifest_data, moved_files)
            save_manifest(manifest_data, manifest_path)
        
        # Summary
        logger.info(f"Migration completed:")
        logger.info(f"  - Successful moves: {successful_moves}")
        logger.info(f"  - Failed moves: {failed_moves}")
        logger.info(f"  - Total processed: {len(unclassified_entries)}")
        
        if dry_run:
            logger.info("This was a dry run. Use without --dry-run to perform actual migration.")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise


if __name__ == "__main__":
    main()