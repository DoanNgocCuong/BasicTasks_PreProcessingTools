"""
Upload phase for the crawler workflow.
Handles uploading classified children voice files to the server.
"""

import json
import os
from pathlib import Path
from typing import List, Optional, Tuple

from ..config import CrawlerConfig
from ..utils import get_output_manager

# Import from local client
from .client import main as upload_main

# Global variable to store the upload folder_id for the current run
_current_upload_folder_id: Optional[str] = None


def reset_upload_session() -> None:
    """
    Reset the upload session folder ID.
    Should be called at the start of a new crawler workflow to ensure
    a fresh upload session is created.
    """
    global _current_upload_folder_id
    _current_upload_folder_id = None


def _count_uploadable_files(records: List[dict]) -> int:
    """Count the number of records that are eligible for upload."""
    return sum(1 for r in records if 
        r.get("classified") == True and 
        r.get("containing_children_voice") == True and 
        r.get("uploaded", False) == False and
        r.get("file_available", False) == True)


def _get_records_to_process(manifest_data: dict, video_ids: Optional[List[str]]) -> Tuple[List[dict], bool]:
    """Get the records to process, optionally filtered by video_ids."""
    records = manifest_data.get('records', [])
    if video_ids is not None:
        filtered_records = [r for r in records if r.get('video_id') in video_ids]
        return filtered_records, True
    return records, False


async def run_upload_phase(config: CrawlerConfig, processed_files: Optional[List[str]] = None, video_ids: Optional[List[str]] = None) -> int:
    """
    Run the upload phase: upload classified children voice files to the server.

    Args:
        config: Crawler configuration
        processed_files: List of processed file paths (unused, kept for consistency)
        video_ids: Optional list of specific video IDs to upload. If None, uploads all videos.

    Returns:
        Number of files uploaded
    """
    output = get_output_manager()
    output.info("Phase 5: File Upload")

    # Get manifest path
    manifest_path = config.output.final_audio_dir / "manifest.json"

    if not manifest_path.exists():
        output.warning(f"Manifest file not found: {manifest_path}")
        return 0

    try:
        # Check manifest can be loaded
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            output.debug(f"Successfully loaded manifest with {len(manifest_data.get('records', []))} records for upload")
        except json.JSONDecodeError as e:
            output.error(f"Failed to parse manifest JSON at {manifest_path}: {e}")
            output.error(f"Manifest file may be corrupted. Cannot proceed with upload.")
            return 0
        except IOError as e:
            output.error(f"Failed to read manifest file at {manifest_path}: {e}")
            output.error(f"Check file permissions. Cannot proceed with upload.")
            return 0
        except Exception as e:
            output.error(f"Unexpected error loading manifest at {manifest_path}: {e}")
            return 0

        # Filter records if video_ids specified
        records_to_process, is_filtered = _get_records_to_process(manifest_data, video_ids)
        to_upload_count = _count_uploadable_files(records_to_process)
        
        if is_filtered:
            output.info(f"Uploading {to_upload_count} files from {len(manifest_data.get('records', []))} total records")
            
            if not records_to_process:
                output.info("No matching videos found for upload")
                return 0
        else:
            output.info(f"Uploading {to_upload_count} files from {len(records_to_process)} total records")

        # Create temporary manifest if filtered
        upload_manifest_path = manifest_path
        temp_manifest_path = None
        if is_filtered:
            temp_manifest_data = manifest_data.copy()
            temp_manifest_data['records'] = records_to_process
            temp_manifest_path = manifest_path.with_suffix('.temp.json')
            
            try:
                with open(temp_manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(temp_manifest_data, f, indent=2, ensure_ascii=False)
                upload_manifest_path = temp_manifest_path
            except Exception as e:
                output.error(f"Failed to create temporary manifest: {e}")
                return 0

        # Call the upload client main function
        try:
            global _current_upload_folder_id
            total_uploads = 0
            
            if _current_upload_folder_id is None:
                # Start a new upload session for this run
                _current_upload_folder_id, uploads_count = upload_main(str(upload_manifest_path))
                total_uploads += uploads_count
                if _current_upload_folder_id:
                    output.success(f"Phase 5 complete: Started new upload session with folder {_current_upload_folder_id}")
                else:
                    output.warning("Phase 5: No uploads needed, no folder created")
            else:
                # Reuse existing folder for this run
                _current_upload_folder_id, uploads_count = upload_main(str(upload_manifest_path), _current_upload_folder_id)
                total_uploads += uploads_count
                output.success(f"Phase 5 complete: Used existing upload folder {_current_upload_folder_id}")
            
            # Clean up temporary manifest if created
            if temp_manifest_path is not None:
                try:
                    temp_manifest_path.unlink(missing_ok=True)
                except Exception as e:
                    output.warning(f"Failed to clean up temporary manifest: {e}")
            
            return total_uploads
        except Exception as e:
            output.error(f"Upload client failed: {e}")
            output.error(f"Manifest path: {upload_manifest_path}")
            output.error(f"Manifest exists: {upload_manifest_path.exists()}")
            if upload_manifest_path.exists():
                output.error(f"Manifest size: {upload_manifest_path.stat().st_size} bytes")
            import traceback
            output.error(f"Full traceback: {traceback.format_exc()}")
            
            # Clean up temporary manifest on error
            if temp_manifest_path is not None:
                try:
                    temp_manifest_path.unlink(missing_ok=True)
                except Exception as cleanup_error:
                    output.warning(f"Failed to clean up temporary manifest after error: {cleanup_error}")
            
            return 0
    except Exception as e:
        output.error(f"Upload phase failed: {e}")
        output.error(f"Config output dir: {config.output.final_audio_dir}")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")
        return 0
