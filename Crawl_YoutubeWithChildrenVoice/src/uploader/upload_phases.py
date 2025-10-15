"""
Upload phase for the crawler workflow.
Handles uploading classified children voice files to the server.
"""

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
        # Call the upload client main function
        upload_main(str(manifest_path))
        output.success("Phase 5 complete: Files uploaded successfully")
        return 1  # Placeholder, actual count could be returned from main
    except Exception as e:
        output.error(f"Upload phase failed: {e}")
        return 0
