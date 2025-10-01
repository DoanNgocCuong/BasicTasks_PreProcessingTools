#!/usr/bin/env python3
"""
Script to resync manifest.json with actual audio files in the final_audio_files directory.
This script will:
1. Scan all .wav files in the final_audio_files directory
2. Extract video IDs from the filenames
3. Update the manifest.json to only include records for files that actually exist
4. Create a backup of the original manifest before making changes
"""

import json
import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set

def extract_index_from_filename(filename: str) -> int:
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

def get_actual_audio_files(directory: str) -> Dict[int, str]:
    """
    Scan directory for .wav files and extract index numbers.
    
    Args:
        directory: Path to the final_audio_files directory
        
    Returns:
        Dictionary mapping index to filename
    """
    audio_files = {}
    directory_path = Path(directory)
    
    if not directory_path.exists():
        raise FileNotFoundError(f"Directory {directory} does not exist")
    
    for file_path in directory_path.glob("*.wav"):
        index = extract_index_from_filename(file_path.name)
        if index is not None:
            audio_files[index] = file_path.name
        else:
            print(f"Warning: Could not extract index from filename: {file_path.name}")
    
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
    Resync the manifest.json with actual audio files.
    
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
    
    # Get actual audio files
    print("Scanning for actual audio files...")
    actual_audio_files = get_actual_audio_files(audio_directory)
    actual_count = len(actual_audio_files)
    print(f"Found {actual_count} actual audio files")
    
    # Create mapping from index to filename
    index_to_filename = {}
    for index, filename in actual_audio_files.items():
        index_to_filename[index] = filename
    
    # Filter manifest records to only include those with actual audio files
    print("Filtering manifest records...")
    filtered_records = []
    removed_count = 0
    used_audio_files = set()  # Track which audio files have been matched
    
    # Create a set of actual filenames for fast lookup
    actual_filenames = set(actual_audio_files.values())
    
    # Process each manifest record and check if the corresponding audio file exists
    for record in manifest_data.get('records', []):
        original_path = record.get('output_path', '')
        if original_path:
            # Extract just the filename from the full path
            original_filename = Path(original_path).name
            
            # Check if this exact filename exists in our actual audio files
            if original_filename in actual_filenames:
                # Update the output_path to the current directory structure
                record['output_path'] = str(Path(audio_directory) / original_filename)
                filtered_records.append(record)
                used_audio_files.add(original_filename)
            else:
                print(f"Warning: Audio file not found: {original_filename}")
                removed_count += 1
        else:
            print(f"Warning: Manifest record has no output_path")
            removed_count += 1
    
    # Update manifest data
    manifest_data['records'] = filtered_records
    manifest_data['total_duration_seconds'] = sum(record.get('duration_seconds', 0) for record in filtered_records)
    
    # Save updated manifest
    print("Saving updated manifest...")
    save_manifest(manifest_data, manifest_path)
    
    # Check for audio files without manifest records
    # Find audio files that weren't matched to any manifest record
    unused_audio_files = []
    for filename in actual_filenames:
        if filename not in used_audio_files:
            unused_audio_files.append(filename)
    
    # Sort the unused files for better readability
    unused_audio_files.sort()
    
    # Print summary
    print("\n" + "="*50)
    print("RESYNC SUMMARY")
    print("="*50)
    print(f"Original records: {original_count}")
    print(f"Actual audio files: {actual_count}")
    print(f"Records after filtering: {len(filtered_records)}")
    print(f"Records removed: {removed_count}")
    print(f"Audio files without manifest records: {len(unused_audio_files)}")
    print(f"Backup created: {backup_path}")
    print(f"Updated manifest saved: {manifest_path}")
    
    if unused_audio_files:
        print("\n" + "="*50)
        print("⚠️  WARNING: AUDIO FILES WITHOUT MANIFEST RECORDS")
        print("="*50)
        print(f"Found {len(unused_audio_files)} audio files without corresponding manifest records:")
        for i, filename in enumerate(unused_audio_files[:20]):  # Show first 20
            print(f"  {i+1:2d}. {filename}")
        if len(unused_audio_files) > 20:
            print(f"  ... and {len(unused_audio_files) - 20} more files")
        print("="*50)
    
    print("="*50)

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
