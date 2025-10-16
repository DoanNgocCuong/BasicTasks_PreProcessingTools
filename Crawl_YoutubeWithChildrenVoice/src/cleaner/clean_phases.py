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
            output.warning(f"Manifest file not found at {manifest_file} - skipping clean phase")
            return videos

        output.info(f"Loading manifest file: {manifest_file}")
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            output.debug(f"Successfully loaded manifest with {len(manifest_data.get('records', []))} records")
        except json.JSONDecodeError as e:
            output.error(f"Failed to parse manifest JSON at {manifest_file}: {e}")
            output.error(f"Manifest file may be corrupted. Please check the file contents.")
            return videos
        except IOError as e:
            output.error(f"Failed to read manifest file at {manifest_file}: {e}")
            output.error(f"Check file permissions and disk space.")
            return videos
        except Exception as e:
            output.error(f"Unexpected error loading manifest at {manifest_file}: {e}")
            return videos

        output.info("Running manifest cleaning")
        try:
            await run_local_clean(config, manifest_file)
        except Exception as e:
            output.error(f"Local clean operation failed: {e}")
            output.error(f"Manifest file: {manifest_file}")
            output.error(f"Current working directory: {Path.cwd()}")
            import traceback
            output.error(f"Full traceback: {traceback.format_exc()}")
            return videos

        return videos

    except Exception as e:
        output.error(f"Clean phase failed: {e}")
        output.error(f"Config output dir: {config.output.final_audio_dir}")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")
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
        try:
            file_manager = get_file_manager()
            file_manager.save_json(manifest_file, manifest_data)
            output.success("Created empty manifest file")
        except Exception as e:
            output.error(f"Failed to create empty manifest file at {manifest_file}: {e}")
            output.error(f"Check file permissions and disk space.")
            import traceback
            output.error(f"Full traceback: {traceback.format_exc()}")
        return

    # Call the clean_manifest function
    try:
        output.debug(f"Calling clean_manifest function on {manifest_file}")
        clean_manifest(str(manifest_file))
        output.success("Manifest cleaning completed")
    except Exception as e:
        output.error(f"clean_manifest function failed: {e}")
        output.error(f"Manifest file: {manifest_file}")
        output.error(f"File exists: {manifest_file.exists()}")
        output.error(f"File size: {manifest_file.stat().st_size if manifest_file.exists() else 'N/A'} bytes")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")