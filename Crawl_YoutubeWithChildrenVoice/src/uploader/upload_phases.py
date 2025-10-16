"""
Upload phase for the crawler workflow.
Handles uploading classified children voice files to the server.
"""

import json
import os
from pathlib import Path
from typing import List, Optional

from ..config import CrawlerConfig
from ..utils import get_output_manager

# Import from local client
from .client import main as upload_main


async def run_upload_phase(config: CrawlerConfig, processed_files: Optional[List[str]] = None) -> int:
    """
    Run the upload phase: upload classified children voice files to the server.

    Args:
        config: Crawler configuration
        processed_files: List of processed file paths (unused, kept for consistency)

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

        # Call the upload client main function
        try:
            upload_main(str(manifest_path))
            output.success("Phase 5 complete: Files uploaded successfully")
            return 1  # Placeholder, actual count could be returned from main
        except Exception as e:
            output.error(f"Upload client failed: {e}")
            output.error(f"Manifest path: {manifest_path}")
            output.error(f"Manifest exists: {manifest_path.exists()}")
            if manifest_path.exists():
                output.error(f"Manifest size: {manifest_path.stat().st_size} bytes")
            import traceback
            output.error(f"Full traceback: {traceback.format_exc()}")
            return 0
    except Exception as e:
        output.error(f"Upload phase failed: {e}")
        output.error(f"Config output dir: {config.output.final_audio_dir}")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")
        return 0
