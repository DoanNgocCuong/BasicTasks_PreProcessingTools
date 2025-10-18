# filterer/filtering_phases.py

"""
Filtering Phase Implementation

This module contains the implementation of the content filtering phase.
"""

import json
from pathlib import Path
from typing import List, Optional

from ..config import CrawlerConfig
from ..models import VideoMetadata
from ..utils import get_output_manager, get_file_manager


async def run_filtering_phase(config: CrawlerConfig, video_ids: Optional[List[str]] = None) -> List[VideoMetadata]:
    """
    Run the content filtering phase.

    Args:
        config: Crawler configuration
        video_ids: Optional list of specific video IDs to filter. If None, filters all videos.

    Returns:
        List of videos that passed filtering
    """
    output = get_output_manager()

    try:
        # Load manifest
        manifest_file = config.output.final_audio_dir / "manifest.json"
        if not manifest_file.exists():
            output.warning("Manifest file not found - skipping filtering phase")
            return []

        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            output.debug(f"Successfully loaded manifest with {len(manifest_data.get('records', []))} records")
        except json.JSONDecodeError as e:
            output.error(f"Failed to parse manifest JSON at {manifest_file}: {e}")
            output.error(f"Manifest file may be corrupted. Please check the file contents.")
            return []
        except IOError as e:
            output.error(f"Failed to read manifest file at {manifest_file}: {e}")
            output.error(f"Check file permissions and disk space.")
            return []
        except Exception as e:
            output.error(f"Unexpected error loading manifest at {manifest_file}: {e}")
            return []

        # Filterer always runs locally for file operations
        output.info("Running content filtering locally")
        try:
            return await run_local_filtering(config, manifest_data, manifest_file, video_ids)
        except Exception as e:
            output.error(f"Local filtering failed: {e}")
            import traceback
            output.error(f"Full traceback: {traceback.format_exc()}")
            return []

    except Exception as e:
        output.error(f"Filtering phase failed: {e}")
        output.error(f"Config output dir: {config.output.final_audio_dir}")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")
        return []


async def run_local_filtering(config: CrawlerConfig, manifest_data: dict, manifest_file: Path, video_ids: Optional[List[str]] = None) -> List[VideoMetadata]:
    """
    Run content filtering locally based on manifest data.

    Args:
        config: Crawler configuration
        manifest_data: Manifest data
        manifest_file: Path to manifest file
        video_ids: Optional list of specific video IDs to filter. If None, filters all videos.

    Returns:
        List of videos that passed filtering
    """
    output = get_output_manager()
    records_to_keep = []
    files_moved = 0
    entries_removed = 0

    # Get records to process
    all_records = manifest_data.get('records', [])
    if video_ids is not None:
        # Filter to only specified video IDs
        records_to_process = [r for r in all_records if r.get('video_id') in video_ids]
        output.info(f"Filtering {len(records_to_process)} specific videos from {len(all_records)} total records")
    else:
        # Process all records
        records_to_process = all_records
        output.info(f"Filtering all {len(records_to_process)} records")

    # First, clean up URL output file by removing duplicates
    url_file = config.output.url_outputs_dir / "discovered_urls.txt"
    url_duplicates_removed = 0

    if url_file.exists():
        output.info("Checking URL output file for duplicates")
        try:
            with open(url_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]

            original_count = len(urls)
            # Remove duplicates while preserving order
            seen_urls = set()
            unique_urls = []

            for url in urls:
                if url not in seen_urls:
                    seen_urls.add(url)
                    unique_urls.append(url)
                else:
                    url_duplicates_removed += 1

            # Save cleaned URLs back to file
            with open(url_file, 'w', encoding='utf-8') as f:
                for url in unique_urls:
                    f.write(f"{url}\n")

            if url_duplicates_removed > 0:
                output.info(f"Removed {url_duplicates_removed} duplicate URLs from {url_file}")
            else:
                output.debug(f"No duplicate URLs found in {url_file}")

        except Exception as e:
            output.warning(f"Failed to clean up URL file {url_file}: {e}")
            output.warning(f"File exists: {url_file.exists()}")
            if url_file.exists():
                output.warning(f"File size: {url_file.stat().st_size} bytes")
    else:
        output.debug(f"URL output file not found: {url_file}")

    # Build a map of all existing files in final_audio_files
    final_audio_dir = config.output.final_audio_dir
    existing_files = {}  # Maps filename -> path (for quick lookup by name)
    try:
        if final_audio_dir.exists():
            for file_path in final_audio_dir.rglob("*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.wav', '.mp3', '.m4a']:
                    file_name = file_path.name
                    # Check if this filename already exists (duplicate detected)
                    if file_name in existing_files:
                        existing_path = existing_files[file_name]
                        output.warning(f"Duplicate filename found: '{file_name}' exists in multiple locations:")
                        output.warning(f"  - {existing_path}")
                        output.warning(f"  - {file_path}")
                        output.warning(f"  Using first occurrence, but this may cause issues")
                    else:
                        existing_files[file_name] = file_path
        output.info(f"Found {len(existing_files)} unique audio files in {final_audio_dir}")
    except Exception as e:
        output.error(f"Failed to scan final audio directory {final_audio_dir}: {e}")
        output.error(f"Directory exists: {final_audio_dir.exists()}")
        return []

    for record in records_to_process:
        if not record.get('classified', False):
            # Not yet classified, keep for now
            # But validate it has required fields
            video_id = record.get('video_id')
            if not video_id:
                output.warning(f"Skipping unclassified record with missing video_id: {record}")
                entries_removed += 1
                continue
            records_to_keep.append(record)
            continue

        video_id = record.get('video_id')
        output_path_str = record.get('output_path')

        # Skip records with missing required fields
        if not video_id or not output_path_str:
            output.warning(f"Skipping filtering for record with missing video_id or output_path: video_id={video_id}, output_path={output_path_str}")
            entries_removed += 1
            continue

        # Convert to absolute path if relative (manifest.json is at workspace/output/final_audio/manifest.json)
        output_path = Path(output_path_str)
        if not output_path.is_absolute():
            # Safety check: ensure we can resolve workspace root
            if len(manifest_file.parents) < 2:
                output.error(f"Cannot resolve workspace root from manifest path: {manifest_file}")
                output.error(f"Manifest path has insufficient parents: {manifest_file.parents}")
                entries_removed += 1
                continue
            workspace_root = manifest_file.parents[2]  # Go up 2 levels from final_audio/manifest.json
            output_path = workspace_root / output_path_str

        # Check if file exists at recorded path or in the file system
        file_exists = output_path.exists()
        if not file_exists and output_path.name in existing_files:
            # File exists but path is wrong, update path
            correct_path = existing_files[output_path.name]
            # Convert back to relative path for consistency with original manifest format
            try:
                # Safety check: ensure workspace root is accessible
                if len(manifest_file.parents) < 2:
                    output.warning(f"Could not convert to relative path for {video_id}: insufficient manifest path depth")
                    record['output_path'] = str(correct_path)
                else:
                    relative_path = correct_path.relative_to(manifest_file.parents[2])
                    record['output_path'] = str(relative_path)
            except ValueError:
                # If relative_to fails, store absolute path
                output.warning(f"Could not convert to relative path for {video_id}: {correct_path}")
                record['output_path'] = str(correct_path)
            output_path = correct_path
            file_exists = True
            output.debug(f"Corrected path for {video_id}: {output_path}")

        if not file_exists:
            output.warning(f"File not found for {video_id}: {output_path} - marking as unavailable")
            record['file_available'] = False
            records_to_keep.append(record)
            continue

        # CRITICAL FIX #3: Validate that classified records have ALL required classification fields
        containing_children_voice = record.get('containing_children_voice')
        classification_timestamp = record.get('classification_timestamp')
        
        # Check if classification is complete
        if containing_children_voice is None or classification_timestamp is None:
            output.warning(f"Skipping {video_id}: classified=True but missing required fields (containing_children_voice={containing_children_voice}, classification_timestamp={classification_timestamp})")
            record['file_available'] = False
            records_to_keep.append(record)
            continue

        # Check for children's voice
        if containing_children_voice:
            # Move to appropriate language folder
            language_folder = record.get('language_folder', 'unknown')
            
            # SECURITY FIX: Sanitize language_folder to prevent path traversal attacks
            # Remove any path separators and suspicious characters
            language_folder = language_folder.replace('\\', '').replace('/', '').replace('..', '').strip()
            if not language_folder:
                language_folder = 'unknown'
            
            target_dir = final_audio_dir / language_folder
            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = target_dir / output_path.name

            # Handle potential race condition: check and remove target if exists
            if target_path.exists():
                try:
                    target_path.unlink()  # Remove existing file to allow overwrite
                    output.debug(f"Removed existing file at target: {target_path}")
                except Exception as e:
                    output.error(f"Failed to remove existing target file for {video_id}: {e}")
                    output.error(f"Target path: {target_path}")
                    record['file_available'] = False
                    records_to_keep.append(record)
                    continue

            # Move file with error handling
            if not output_path.exists():
                # File might have been moved by another process
                output.warning(f"Source file disappeared during processing for {video_id}: {output_path}")
                record['file_available'] = False
                records_to_keep.append(record)
                continue

            try:
                output_path.rename(target_path)
                # Convert to relative path for consistency with original manifest format
                try:
                    # Safety check: ensure workspace root is accessible
                    if len(manifest_file.parents) < 2:
                        output.warning(f"Could not convert target path to relative for {video_id}: insufficient manifest path depth")
                        record['output_path'] = str(target_path)
                    else:
                        relative_target_path = target_path.relative_to(manifest_file.parents[2])
                        record['output_path'] = str(relative_target_path)
                except ValueError:
                    # If relative_to fails, store absolute path
                    output.warning(f"Could not convert target path to relative for {video_id}: {target_path}")
                    record['output_path'] = str(target_path)
                records_to_keep.append(record)
                files_moved += 1
                output.debug(f"Moved {video_id} to {language_folder} folder")
            except Exception as e:
                output.error(f"Failed to move file for {video_id}: {e}")
                output.error(f"Source: {output_path}, Target: {target_path}")
                output.error(f"Source exists: {output_path.exists()}, Target exists: {target_path.exists()}")
                record['file_available'] = False
                records_to_keep.append(record)
                continue
        else:
            # No children's voice - move file to backup/trash instead of permanently deleting
            # Re-check that file still exists before moving (in case it was moved by concurrent process)
            if output_path.exists():
                try:
                    # Move to backup directory for no-children-voice files
                    backup_dir = final_audio_dir / "backups" / "no_children_voice"
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    backup_path = backup_dir / output_path.name
                    
                    # If file already exists in backup, remove old copy first
                    if backup_path.exists():
                        try:
                            backup_path.unlink()
                        except Exception as e:
                            output.warning(f"Failed to remove old backup copy for {video_id}: {e}")
                    
                    output_path.rename(backup_path)
                    
                    # Update record to point to backup location (as relative path)
                    try:
                        # Convert backup path to relative for consistency
                        if len(manifest_file.parents) < 2:
                            output.warning(f"Could not convert backup path to relative for {video_id}: insufficient manifest path depth")
                            record['output_path'] = str(backup_path)
                        else:
                            relative_backup_path = backup_path.relative_to(manifest_file.parents[2])
                            record['output_path'] = str(relative_backup_path)
                    except ValueError:
                        # If relative_to fails, store absolute path
                        output.warning(f"Could not convert backup path to relative for {video_id}: {backup_path}")
                        record['output_path'] = str(backup_path)
                    
                    output.debug(f"Moved file without children's voice to backup: {video_id} -> {backup_path}")
                except Exception as e:
                    backup_target = final_audio_dir / "backups" / "no_children_voice" / output_path.name
                    output.warning(f"Failed to move file to backup for {video_id}: {e}")
                    output.warning(f"Source: {output_path}, Backup target: {backup_target}")
                    output.warning(f"Source exists: {output_path.exists()}")
            else:
                output.debug(f"File already missing for {video_id}, skipping backup move")
            record['file_available'] = False
            records_to_keep.append(record)

    seen_video_ids = set()
    unique_records = []
    duplicates_removed = 0

    for record in records_to_keep:
        video_id = record.get('video_id')
        if video_id is None or video_id == '':
            # Skip records with null or empty video_id
            output.warning(f"Skipping record with null or empty video_id during deduplication")
            continue
        if video_id in seen_video_ids:
            duplicates_removed += 1
            output.debug(f"Removing duplicate record for video_id: {video_id}")
            continue
        seen_video_ids.add(video_id)
        unique_records.append(record)

    # Update manifest - handle partial updates when video_ids is specified
    if video_ids is not None:
        # When filtering specific videos, ensure we don't introduce duplicates
        # Create map of all processed video_ids for quick lookup
        processed_video_ids = {record.get('video_id') for record in unique_records}
        
        # Build final records list:
        # 1. Keep processed records (with updates)
        # 2. Keep non-processed records (unchanged)
        # But remove ANY duplicates by video_id
        final_seen_ids = set()
        final_records = []
        
        # First add all processed records
        for record in unique_records:
            video_id = record.get('video_id')
            if video_id and video_id not in final_seen_ids:
                final_records.append(record)
                final_seen_ids.add(video_id)
        
        # Then add non-processed records that aren't duplicates
        for record in all_records:
            video_id = record.get('video_id')
            if video_id not in processed_video_ids and video_id not in final_seen_ids and video_id:
                final_records.append(record)
                final_seen_ids.add(video_id)
        
        manifest_data['records'] = final_records
        output.debug(f"Partial update: {len(unique_records)} records processed, {len(all_records) - len(unique_records)} records unchanged, total {len(final_records)}")
    else:
        # Full update when processing all records
        manifest_data['records'] = unique_records
        output.debug(f"Full update: {len(unique_records)} records after deduplication")

    # Recalculate total duration from all records
    all_current_records = manifest_data.get('records', [])
    # Safely sum durations - handle non-numeric values
    total_duration = 0
    for record in all_current_records:
        duration = record.get('duration_seconds', 0)
        # Safely convert to float, defaulting to 0 if invalid
        try:
            if duration is None:
                total_duration += 0
            else:
                total_duration += float(duration)
        except (ValueError, TypeError):
            # Invalid duration value, skip it
            output.warning(f"Invalid duration_seconds for video_id {record.get('video_id')}: {duration}")
            continue
    manifest_data['total_duration_seconds'] = total_duration

    # Save updated manifest
    try:
        file_manager = get_file_manager()
        file_manager.save_json(manifest_file, manifest_data)
        output.success(f"Local filtering completed: {files_moved} files moved, {entries_removed} entries removed, {duplicates_removed} manifest duplicates removed, {url_duplicates_removed} URL duplicates removed")
        output.info(f"Final manifest: {len(all_current_records)} entries, {total_duration:.1f}s total duration")
    except Exception as e:
        output.error(f"Failed to save updated manifest after filtering: {e}")
        output.error(f"Manifest file: {manifest_file}")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")

    # Return videos that were kept (this is mainly for compatibility)
    # In practice, the manifest now contains the filtered results
    return []