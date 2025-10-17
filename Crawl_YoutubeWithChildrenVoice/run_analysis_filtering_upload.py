#!/usr/bin/env python3
"""
Analysis-Filtering-Upload Script

Runs only the analysis, filtering, and upload phases of the YouTube Children's Voice Crawler.
This script processes existing audio files in the manifest and uploads classified children's voice files.
"""

import asyncio
import sys
import argparse
import json
from pathlib import Path
from typing import Optional, List

# Handle imports for both direct execution and module execution
if __name__ == "__main__" and __package__ is None:
    # Script is being run directly (not as a module)
    # Add the parent directory to Python path for relative imports
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "src"

try:
    from src.config import load_config, CrawlerConfig
    from src.analyzer.analysis_phases import run_analysis_phase
    from src.filterer.filtering_phases import run_filtering_phase
    from src.uploader.upload_phases import run_upload_phase
    from src.cleaner.clean_phases import run_clean_phase
    from src.utils import get_output_manager
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    print("This script should be run from the project root directory", file=sys.stderr)
    sys.exit(1)


async def run_analysis_filtering_upload_workflow(config: CrawlerConfig, video_ids: Optional[List[str]] = None) -> bool:
    """
    Run the analysis, filtering, and upload phases.

    Args:
        config: Crawler configuration
        video_ids: Optional list of specific video IDs to process. If None, processes all videos.

    Returns:
        True if workflow completed successfully
    """
    output = get_output_manager()

    try:
        output.info("=== Analysis-Filtering-Upload Workflow ===")

        # Check if manifest exists
        manifest_path = config.output.final_audio_dir / "manifest.json"
        if not manifest_path.exists():
            output.error(f"Manifest file not found: {manifest_path}")
            output.error("Please ensure audio files have been downloaded and processed first.")
            return False

        # Load manifest to get video IDs
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
        except Exception as e:
            output.error(f"Failed to load manifest: {e}")
            return False

        # Determine which videos to process
        all_records = manifest_data.get('records', [])
        if video_ids is not None:
            # Filter to specified video IDs
            videos_to_process = [r for r in all_records if r.get('video_id') in video_ids]
            if not videos_to_process:
                output.warning(f"No videos found matching the specified IDs: {video_ids}")
                return False
            output.info(f"Processing {len(videos_to_process)} specified videos")
        else:
            # Process all videos
            videos_to_process = all_records
            output.info(f"Processing all {len(videos_to_process)} videos individually")

        # Process each video individually
        processed_count = 0
        for record in videos_to_process:
            video_id = record.get('video_id')
            if not video_id:
                output.warning("Skipping record with missing video_id")
                continue

            output.info(f"Processing video: {video_id}")
            
            # Phase 0: Manifest Cleaning (optional, but good practice)
            output.debug(f"Phase 0: Manifest Cleaning for {video_id}")
            await run_clean_phase(config, [])
            
            # Phase 1: Audio Analysis
            output.debug(f"Phase 1: Audio Analysis for {video_id}")
            await run_analysis_phase(config, [], [video_id])
            
            # Phase 2: Content Filtering
            output.debug(f"Phase 2: Content Filtering for {video_id}")
            await run_filtering_phase(config, [], [video_id])
            
            # Phase 3: File Upload
            output.debug(f"Phase 3: File Upload for {video_id}")
            upload_count = await run_upload_phase(config, [], [video_id])
            
            processed_count += 1
            output.info(f"Completed processing video {video_id} ({processed_count}/{len(videos_to_process)})")

        output.success(f"Individual processing complete: {processed_count} videos processed")

        # Final Summary
        output.info("=== Workflow Complete ===")

        # Load final manifest for summary
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    final_manifest_data = json.load(f)

                final_count = len(final_manifest_data.get('records', []))
                total_duration = final_manifest_data.get('total_duration_seconds', 0)

                output.info(f"Final collection: {final_count} children's voice files")
                output.info(f"Total duration: {total_duration:.1f} seconds")
            except Exception as e:
                output.warning(f"Could not load final manifest for summary: {e}")
        else:
            output.warning("Manifest file not found for final summary")

        return True

    except Exception as e:
        output.error(f"Workflow failed: {e}")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")
        return False


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Analysis-Filtering-Upload Script for YouTube Children's Voice Crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_analysis_filtering_upload.py                          # Run with default config
  python run_analysis_filtering_upload.py --config custom.json     # Use custom config file
  python run_analysis_filtering_upload.py --verbose                # Enable verbose logging
        """
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration file (JSON)"
    )

    parser.add_argument(
        "--env-file",
        type=str,
        help="Path to environment file"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory (overrides config)"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--video-ids",
        type=str,
        help="Comma-separated list of specific video IDs to process (e.g., 'vid1,vid2,vid3')"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without running workflow"
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    # Load configuration
    try:
        config = load_config(
            config_file=args.config,
            env_file=args.env_file,
            cli_overrides={
                "output_dir": args.output_dir,
                "verbose": args.verbose,
            }
        )
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    # Parse video IDs if provided
    video_ids = None
    if args.video_ids:
        video_ids = [vid.strip() for vid in args.video_ids.split(',') if vid.strip()]
        if not video_ids:
            print("Error: --video-ids argument provided but no valid IDs found", file=sys.stderr)
            return 1

    # Set up output manager
    output = get_output_manager()
    if config.logging.debug_mode:
        output.set_level("DEBUG")

    # Dry run
    if args.dry_run:
        output.info("Dry run - validating configuration")
        output.info(f"Output directory: {config.output.base_dir}")
        output.success("Configuration is valid")
        return 0

    # Run workflow
    try:
        success = asyncio.run(run_analysis_filtering_upload_workflow(config, video_ids))
        return 0 if success else 1
    except KeyboardInterrupt:
        output.warning("Workflow interrupted by user")
        return 130
    except Exception as e:
        output.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())