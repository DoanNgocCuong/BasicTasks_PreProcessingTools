# cleaner/clean_phases.py

"""
Clean Phase Implementation

This module contains the implementation of the manifest cleaning phase.
"""

import json
from pathlib import Path
from typing import List
from datetime import datetime

from ..config import CrawlerConfig
from ..models import VideoMetadata
from ..utils import get_output_manager, get_file_manager
from .clean_manifest import clean_manifest


async def run_clean_phase(config: CrawlerConfig, videos: List[VideoMetadata]) -> List[VideoMetadata]:
    """
    Run the manifest cleaning phase.

    Args:
        config: Crawler configuration
        videos: Videos to clean (for compatibility)

    Returns:
        List of videos (unchanged)
    """
    output = get_output_manager()

    try:
        # Check if cleaning is enabled
        if not config.clean.enabled:
            output.info("Manifest cleaning disabled - skipping clean phase")
            return videos

        # Load manifest
        manifest_file = config.output.final_audio_dir / "manifest.json"
        if not manifest_file.exists():
            output.warning("Manifest file not found - skipping clean phase")
            return videos

        output.info("Running manifest cleaning")
        await run_local_clean(config, manifest_file)

        return videos

    except Exception as e:
        output.error(f"Clean phase failed: {e}")
        return videos


async def run_local_clean(config: CrawlerConfig, manifest_file: Path) -> None:
    """
    Run manifest cleaning locally.

    Args:
        config: Crawler configuration
        manifest_file: Path to manifest file
    """
    output = get_output_manager()

    # Check if manifest exists
    if not manifest_file.exists():
        output.info(f"Manifest file not found: {manifest_file} - creating empty manifest")
        # Create empty manifest
        manifest_data = {"total_duration_seconds": 0.0, "records": []}
        file_manager = get_file_manager()
        file_manager.save_json(manifest_file, manifest_data)
        output.success("Created empty manifest file")
        return

    # Call the clean_manifest function
    clean_manifest(str(manifest_file))

    output.success("Manifest cleaning completed")