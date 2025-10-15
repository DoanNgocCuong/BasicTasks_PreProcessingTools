# filterer/filtering_phases.py

"""
Filtering Phase Implementation

This module contains the implementation of the content filtering phase.
"""

import json
from pathlib import Path
from typing import List

from ..config import CrawlerConfig
from ..models import VideoMetadata
from ..utils import get_output_manager


async def run_filtering_phase(config: CrawlerConfig, videos: List[VideoMetadata]) -> List[VideoMetadata]:
    """
    Run the content filtering phase.

    Args:
        config: Crawler configuration
        videos: Videos to filter

    Returns:
        List of videos that passed filtering
    """
    output = get_output_manager()

    try:
        # Load manifest
        manifest_file = config.output.final_audio_dir / "manifest.json"
        if not manifest_file.exists():
            output.warning("Manifest file not found - skipping filtering phase")
            return videos

        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)

        # Filterer always runs locally for file operations
        output.info("Running content filtering locally")
        return await run_local_filtering(config, manifest_data, manifest_file)

    except Exception as e:
        output.error(f"Filtering phase failed: {e}")
        return videos


async def run_local_filtering(config: CrawlerConfig, manifest_data: dict, manifest_file: Path) -> List[VideoMetadata]:
    """
    Run content filtering locally based on manifest data.

    Args:
        config: Crawler configuration
        manifest_data: Manifest data
        manifest_file: Path to manifest file

    Returns:
        List of videos that passed filtering
    """
    output = get_output_manager()
    records_to_keep = []
    files_moved = 0
    entries_removed = 0

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
    else:
        output.debug(f"URL output file not found: {url_file}")

    # Build a map of all existing files in final_audio_files
    final_audio_dir = config.output.final_audio_dir
    existing_files = {}
    if final_audio_dir.exists():
        for file_path in final_audio_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.wav', '.mp3', '.m4a']:
                existing_files[file_path.name] = file_path

    output.info(f"Found {len(existing_files)} audio files in {final_audio_dir}")

    for record in manifest_data.get('records', []):
        if not record.get('classified', False):
            # Not yet classified, keep for now
            records_to_keep.append(record)
            continue

        video_id = record['video_id']
        output_path = Path(record['output_path'])

        # Check if file exists at recorded path or in the file system
        file_exists = output_path.exists()
        if not file_exists and output_path.name in existing_files:
            # File exists but path is wrong, update path
            correct_path = existing_files[output_path.name]
            record['output_path'] = str(correct_path)
            output_path = correct_path
            file_exists = True
            output.debug(f"Corrected path for {video_id}: {output_path}")

        if not file_exists:
            output.warning(f"File not found for {video_id}: {output_path} - removing from manifest")
            entries_removed += 1
            continue

        # Check for children's voice
        has_children_voice = record.get('containing_children_voice', False)

        if has_children_voice:
            # Move to appropriate language folder
            language_folder = record.get('language_folder', 'unknown')
            target_dir = final_audio_dir / language_folder
            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = target_dir / output_path.name

            # Check for duplicates
            if target_path.exists():
                output.warning(f"Duplicate file detected: {target_path} - skipping")
                entries_removed += 1
                continue

            # Move file
            output_path.rename(target_path)
            record['output_path'] = str(target_path)
            records_to_keep.append(record)
            files_moved += 1
            output.debug(f"Moved {video_id} to {language_folder} folder")
        else:
            # No children's voice - remove entry and file
            try:
                output_path.unlink()
                output.debug(f"Removed file without children's voice: {video_id}")
            except Exception as e:
                output.warning(f"Failed to remove file {output_path}: {e}")
            entries_removed += 1

    # Remove duplicate entries (same video_id)
    seen_video_ids = set()
    unique_records = []
    duplicates_removed = 0

    for record in records_to_keep:
        video_id = record['video_id']
        if video_id in seen_video_ids:
            duplicates_removed += 1
            continue
        seen_video_ids.add(video_id)
        unique_records.append(record)

    # Update manifest
    manifest_data['records'] = unique_records

    # Recalculate total duration
    total_duration = sum(record.get('duration_seconds', 0) for record in unique_records)
    manifest_data['total_duration_seconds'] = total_duration

    # Save updated manifest
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    output.success(f"Local filtering completed: {files_moved} files moved, {entries_removed} entries removed, {duplicates_removed} manifest duplicates removed, {url_duplicates_removed} URL duplicates removed")
    output.info(f"Final manifest: {len(unique_records)} entries, {total_duration:.1f}s total duration")

    # Return videos that were kept (this is mainly for compatibility)
    # In practice, the manifest now contains the filtered results
    return []