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


def validate_manifest_integrity(manifest_path: Path, output) -> bool:
    """
    Validate the integrity of the manifest file.
    
    Args:
        manifest_path: Path to the manifest file
        output: Output manager instance
        
    Returns:
        True if manifest is valid, False otherwise
    """
    if not manifest_path.exists():
        output.error(f"Manifest file does not exist: {manifest_path}")
        return False
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        
        # Check basic structure
        if not isinstance(manifest_data, dict):
            output.error("Manifest is not a valid JSON object")
            return False
        
        records = manifest_data.get('records', [])
        if not isinstance(records, list):
            output.error("Manifest records is not a list")
            return False
        
        # Check each record has required fields
        for i, record in enumerate(records):
            if not isinstance(record, dict):
                output.error(f"Record {i} is not a valid object")
                return False
            
            video_id = record.get('video_id')
            if not video_id or not isinstance(video_id, str):
                output.error(f"Record {i} missing or invalid video_id: {video_id}")
                return False
        
        # Validate total_duration_seconds
        total_duration = manifest_data.get('total_duration_seconds', 0)
        if not isinstance(total_duration, (int, float)):
            output.error(f"Invalid total_duration_seconds: {total_duration}")
            return False
        
        # Cross-validate total duration with records
        calculated_duration = sum(record.get('duration_seconds', 0) for record in records)
        if abs(total_duration - calculated_duration) > 0.01:  # Allow small floating point differences
            output.warning(f"Total duration mismatch: manifest={total_duration:.2f}, calculated={calculated_duration:.2f}")
            # This is a warning, not an error - fix it
            manifest_data['total_duration_seconds'] = calculated_duration
            try:
                with open(manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest_data, f, indent=2, ensure_ascii=False)
                output.info(f"Fixed total duration in manifest: {calculated_duration:.2f}")
            except Exception as e:
                output.error(f"Failed to fix total duration: {e}")
        
        output.debug(f"Manifest validation passed: {len(records)} records, {total_duration:.2f}s total duration")
        return True
        
    except json.JSONDecodeError as e:
        output.error(f"Manifest contains invalid JSON: {e}")
        return False
    except Exception as e:
        output.error(f"Failed to validate manifest: {e}")
        return False


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

        # Create backup of manifest before processing
        backup_path = manifest_path.with_suffix(manifest_path.suffix + '.backup')
        try:
            import shutil
            shutil.copy2(manifest_path, backup_path)
            output.info(f"Created manifest backup: {backup_path}")
        except Exception as e:
            output.error(f"Failed to create manifest backup: {e}")
            return False

        # Determine which videos to process
        all_records = manifest_data.get('records', [])
        if video_ids is not None:
            # Filter to specified video IDs that meet upload criteria
            videos_to_process = [r for r in all_records 
                               if r.get('video_id') in video_ids 
                               and r.get('classified', False) == True
                               and r.get('containing_children_voice', False) == True
                               and r.get('uploaded', False) == False
                               and r.get('file_available', False) == True]
            if not videos_to_process:
                output.warning(f"No eligible videos found matching the specified IDs: {video_ids}")
                output.warning("Videos must be: classified, contain children's voice, not uploaded, and have available files")
                return False
            output.info(f"Processing {len(videos_to_process)} specified eligible videos")
        else:
            # Process all videos that meet upload criteria
            videos_to_process = [r for r in all_records 
                               if r.get('classified', False) == True
                               and r.get('containing_children_voice', False) == True
                               and r.get('uploaded', False) == False
                               and r.get('file_available', False) == True]
            output.info(f"Processing all {len(videos_to_process)} eligible videos individually")

        # Process each video individually
        processed_count = 0
        failed_count = 0

        for record in videos_to_process:
            video_id = record.get('video_id')
            if not video_id:
                output.warning("Skipping record with missing video_id")
                continue

            output.info(f"Processing video: {video_id}")
            
            try:
                # Clean phase before processing each video
                output.debug(f"Clean phase for {video_id}")
                await run_clean_phase(config, [])
                
                # Phase 1: Audio Analysis
                output.debug(f"Phase 1: Audio Analysis for {video_id}")
                await run_analysis_phase(config, [], [video_id])
                
                # Validate manifest after analysis
                if not validate_manifest_integrity(manifest_path, output):
                    output.error(f"Manifest corrupted after analysis phase for {video_id}")
                    failed_count += 1
                    continue
                
                # Phase 2: Content Filtering
                output.debug(f"Phase 2: Content Filtering for {video_id}")
                await run_filtering_phase(config, [], [video_id])
                
                # Validate manifest after filtering
                if not validate_manifest_integrity(manifest_path, output):
                    output.error(f"Manifest corrupted after filtering phase for {video_id}")
                    failed_count += 1
                    continue
                
                # Phase 3: File Upload
                output.debug(f"Phase 3: File Upload for {video_id}")
                upload_count = await run_upload_phase(config, [], [video_id])
                
                # Validate manifest after upload
                if not validate_manifest_integrity(manifest_path, output):
                    output.error(f"Manifest corrupted after upload phase for {video_id}")
                    failed_count += 1
                    continue
                
                processed_count += 1
                output.info(f"Completed processing video {video_id} ({processed_count}/{len(videos_to_process)})")

            except Exception as e:
                failed_count += 1
                output.error(f"Failed to process video {video_id}: {e}")
                output.error(f"Continuing with next video...")
                # Continue processing other videos even if this one fails
                continue

        if failed_count > 0:
            output.warning(f"Processing completed with {failed_count} failed videos out of {len(videos_to_process)} total")

        output.success(f"Individual processing complete: {processed_count} videos processed successfully, {failed_count} failed")

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

        # Clean up backup on successful completion
        try:
            if backup_path.exists():
                backup_path.unlink()
                output.debug(f"Removed manifest backup after successful completion")
        except Exception as e:
            output.warning(f"Failed to remove backup file: {e}")

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

    # Track manifest path for potential restoration
    manifest_path = config.output.final_audio_dir / "manifest.json"
    backup_path = manifest_path.with_suffix(manifest_path.suffix + '.backup')

    # Run workflow with interruption handling
    try:
        success = asyncio.run(run_analysis_filtering_upload_workflow(config, video_ids))
        return 0 if success else 1
    except KeyboardInterrupt:
        output.warning("Workflow interrupted by user")
        # Restore manifest from backup if it exists
        if backup_path.exists():
            try:
                import shutil
                shutil.copy2(backup_path, manifest_path)
                output.info(f"Manifest restored from backup: {backup_path}")
                # Clean up backup
                backup_path.unlink()
                output.debug("Backup file cleaned up")
            except Exception as e:
                output.error(f"Failed to restore manifest from backup: {e}")
                output.error("Manifest may be in an inconsistent state")
        else:
            output.warning("No backup found - manifest may be in an inconsistent state")
        return 130
    except Exception as e:
        output.error(f"Unexpected error: {e}")
        # Also try to restore from backup on unexpected errors
        if backup_path.exists():
            try:
                import shutil
                shutil.copy2(backup_path, manifest_path)
                output.info(f"Manifest restored from backup due to error: {backup_path}")
            except Exception as restore_e:
                output.error(f"Failed to restore manifest from backup: {restore_e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())