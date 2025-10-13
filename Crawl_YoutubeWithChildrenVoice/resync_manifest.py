#!/usr/bin/env python3
"""
Script to resync manifest.json with actual audio files in the final_audio_files directory.
This script will:
1. Scan all .wav files recursively in the final_audio_files directory and subdirectories
2. Match filenames from the manifest with actual files found on disk
3. Update file paths in the manifest for files that have been moved (e.g., between language folders)
4. Remove manifest entries for files that no longer exist
5. Report audio files that exist but have no manifest entries
6. Create a backup of the original manifest before making changes

This is especially useful when files have been manually moved between directories
(e.g., from language-specific folders to unclassified folder) and the manifest
needs to be updated to reflect the new file locations.
"""

import json
import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set, Optional

def extract_index_from_filename(filename: str) -> Optional[int]:
    """
    Extract index number from filename pattern: {index}_{rest}.wav
    
    Args:
        filename: The audio filename
        
    Returns:
        The index number extracted from the filename, or None if not found
    """
    # Pattern: index_rest.wav (index is always at the start)
    match = re.match(r'^(\d+)_', filename)
    if match:
        return int(match.group(1))
    return None

def get_actual_audio_files(directory: str) -> Dict[str, str]:
    """
    Scan directory recursively for .wav files and map filename to full path.
    
    Args:
        directory: Path to the final_audio_files directory
        
    Returns:
        Dictionary mapping filename to full path
    """
    audio_files = {}
    directory_path = Path(directory)
    
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory {directory} does not exist")
    
    # Search recursively for .wav files
    for file_path in directory_path.rglob("*.wav"):
        filename = file_path.name
        full_path = str(file_path)
        
        # If we find duplicate filenames, delete the existing one and keep the new one
        if filename in audio_files:
            existing_path = audio_files[filename]
            print(f"Warning: Duplicate filename found: {filename}")
            print(f"  Existing: {existing_path}")
            print(f"  New: {full_path}")
            print(f"  Deleting existing file and using new path")
            try:
                Path(existing_path).unlink()
                print(f"  ✅ Deleted: {existing_path}")
            except Exception as e:
                print(f"  ❌ Failed to delete {existing_path}: {e}")
        
        audio_files[filename] = full_path
    
    return audio_files

def load_manifest(manifest_path: str) -> Dict:
    """
    Load the manifest.json file.
    
    Args:
        manifest_path: Path to the manifest.json file
        
    Returns:
        The manifest data as a dictionary
    """
    with open(manifest_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_manifest(manifest_data: Dict, manifest_path: str) -> None:
    """
    Save the manifest data to a JSON file.
    
    Args:
        manifest_data: The manifest data to save
        manifest_path: Path where to save the manifest
    """
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

def create_backup(original_path: str) -> str:
    """
    Create a backup of the original manifest file.
    
    Args:
        original_path: Path to the original manifest file
        
    Returns:
        Path to the backup file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{original_path}.backup_{timestamp}"
    shutil.copy2(original_path, backup_path)
    return backup_path

def resync_manifest(manifest_path: str, audio_directory: str) -> None:
    """
    Resync the manifest.json with actual audio files, updating file paths for moved files.
    
    Args:
        manifest_path: Path to the manifest.json file
        audio_directory: Path to the final_audio_files directory
    """
    print("Starting manifest resync process...")
    
    # Create backup
    print("Creating backup of original manifest...")
    backup_path = create_backup(manifest_path)
    print(f"Backup created: {backup_path}")
    
    # Load original manifest
    print("Loading original manifest...")
    manifest_data = load_manifest(manifest_path)
    original_count = len(manifest_data.get('records', []))
    print(f"Original manifest has {original_count} records")
    
    # Get actual audio files (filename -> full_path mapping)
    print("Scanning for actual audio files recursively...")
    actual_audio_files = get_actual_audio_files(audio_directory)
    actual_count = len(actual_audio_files)
    print(f"Found {actual_count} actual audio files")
    
    # Process manifest records and update file paths
    print("Processing manifest records...")
    filtered_records = []
    removed_count = 0
    updated_paths_count = 0
    used_audio_files = set()  # Track which audio files have been matched
    
    for record in manifest_data.get('records', []):
        original_path = record.get('output_path', '')
        if not original_path:
            print(f"Warning: Manifest record has no output_path")
            removed_count += 1
            continue
        
        # Extract just the filename from the full path
        original_filename = Path(original_path).name
        
        # Check if this exact filename exists in our actual audio files
        if original_filename in actual_audio_files:
            current_full_path = actual_audio_files[original_filename]
            
            # Update the output_path if it has changed
            if original_path != current_full_path:
                print(f"Updating path for {original_filename}:")
                print(f"  Old: {original_path}")
                print(f"  New: {current_full_path}")
                record['output_path'] = current_full_path
                updated_paths_count += 1
            
            filtered_records.append(record)
            used_audio_files.add(original_filename)
        else:
            print(f"Warning: Audio file not found: {original_filename}")
            print(f"  Original path in manifest: {original_path}")
            removed_count += 1
    
    # Update manifest data
    manifest_data['records'] = filtered_records
    manifest_data['total_duration_seconds'] = sum(record.get('duration_seconds', 0) for record in filtered_records)
    
    # Save updated manifest
    print("Saving updated manifest...")
    save_manifest(manifest_data, manifest_path)
    
    # Check for audio files without manifest records and delete them
    unused_audio_files = []
    deleted_files_count = 0
    failed_deletions = []
    
    for filename in actual_audio_files.keys():
        if filename not in used_audio_files:
            unused_audio_files.append(filename)
            file_path = actual_audio_files[filename]
            print(f"Deleting audio file without manifest record: {filename}")
            print(f"  Path: {file_path}")
            try:
                Path(file_path).unlink()
                print(f"  ✅ Deleted: {filename}")
                deleted_files_count += 1
            except Exception as e:
                print(f"  ❌ Failed to delete {filename}: {e}")
                failed_deletions.append((filename, str(e)))
    
    # Sort the unused files for better readability (for reporting)
    unused_audio_files.sort()
    
    # Print summary
    print("\n" + "="*60)
    print("RESYNC SUMMARY")
    print("="*60)
    print(f"Original records: {original_count}")
    print(f"Actual audio files: {actual_count}")
    print(f"Records after filtering: {len(filtered_records)}")
    print(f"Records removed: {removed_count}")
    print(f"File paths updated: {updated_paths_count}")
    print(f"Audio files without manifest records: {len(unused_audio_files)}")
    print(f"Audio files deleted: {deleted_files_count}")
    if failed_deletions:
        print(f"Failed deletions: {len(failed_deletions)}")
    print(f"Backup created: {backup_path}")
    print(f"Updated manifest saved: {manifest_path}")
    
    if updated_paths_count > 0:
        print("\n" + "="*60)
        print("✅ FILE PATH UPDATES")
        print("="*60)
        print(f"Successfully updated {updated_paths_count} file paths in the manifest")
        print("This handles files that were moved between language folders or directories")
        print("="*60)
    
    if unused_audio_files:
        print("\n" + "="*60)
        print("🗑️  AUDIO FILES DELETED")
        print("="*60)
        print(f"Deleted {deleted_files_count} audio files that had no manifest records:")
        for i, filename in enumerate(unused_audio_files[:20]):  # Show first 20
            if any(f[0] == filename for f in failed_deletions):
                status = "❌ FAILED"
            else:
                status = "✅ DELETED"
            full_path = actual_audio_files[filename]
            relative_path = Path(full_path).relative_to(Path(audio_directory))
            print(f"  {i+1:2d}. {filename} - {status}")
            print(f"      Location: {relative_path}")
        if len(unused_audio_files) > 20:
            print(f"  ... and {len(unused_audio_files) - 20} more files")
        
        if failed_deletions:
            print(f"\nFailed to delete {len(failed_deletions)} files:")
            for filename, error in failed_deletions:
                print(f"  • {filename}: {error}")
        print("="*60)
    
    print("="*60)

def main():
    """Main function to run the resync process."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    final_audio_files_dir = script_dir / "final_audio_files"
    manifest_path = final_audio_files_dir / "manifest.json"
    
    # Check if files exist
    if not final_audio_files_dir.exists():
        print(f"Error: Directory {final_audio_files_dir} does not exist")
        return 1
    
    if not manifest_path.exists():
        print(f"Error: Manifest file {manifest_path} does not exist")
        return 1
    
    try:
        resync_manifest(str(manifest_path), str(final_audio_files_dir))
        print("\nManifest resync completed successfully!")
        return 0
    except Exception as e:
        print(f"Error during resync: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
