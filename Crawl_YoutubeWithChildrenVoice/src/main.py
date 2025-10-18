#!/usr/bin/env python3
"""
YouTube Children's Voice Crawler - Main Entry Point

A modular, async YouTube crawler for discovering and processing children's voice content.
Provides a single entry point for the entire workflow: search -> download -> analyze -> filter.
"""

import asyncio
import sys
import argparse
import json
import signal
import tempfile
import os
from pathlib import Path
from typing import List, Optional
from contextlib import asynccontextmanager

# Handle imports for both direct execution and module execution
if __name__ == "__main__" and __package__ is None:
    # Script is being run directly (not as a module)
    # Add the parent directory to Python path for relative imports
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "src"

try:
    from .config import load_config, CrawlerConfig  # type: ignore
    from .crawler import run_search_phase  # type: ignore
    from .downloader import run_download_phase_from_urls  # type: ignore
    from .utils import get_output_manager, get_file_manager  # type: ignore
    from .analyzer.analysis_phases import run_analysis_phase  # type: ignore
    from .filterer.filtering_phases import run_filtering_phase  # type: ignore
    from .cleaner.clean_phases import run_clean_phase  # type: ignore
    from .uploader.upload_phases import run_upload_phase, reset_upload_session  # type: ignore
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    print("This script should be run as a module: python -m src.main", file=sys.stderr)
    print("Or install the package and use: yt-crawler", file=sys.stderr)
    sys.exit(1)


def atomic_write_json(file_path: Path, data: dict) -> None:
    """
    Atomically write JSON data to prevent corruption from sudden stops.

    Args:
        file_path: Path to the file to write
        data: JSON data to write
    """
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file first
    with tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        dir=file_path.parent,
        delete=False,
        suffix='.tmp'
    ) as temp_file:
        json.dump(data, temp_file, indent=2, ensure_ascii=False)
        temp_path = Path(temp_file.name)

    # Atomic rename (most filesystems guarantee this is atomic)
    temp_path.replace(file_path)


def atomic_write_text(file_path: Path, content: str) -> None:
    """
    Atomically write text content to prevent corruption from sudden stops.

    Args:
        file_path: Path to the file to write
        content: Text content to write
    """
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temporary file first
    with tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        dir=file_path.parent,
        delete=False,
        suffix='.tmp'
    ) as temp_file:
        temp_file.write(content)
        temp_path = Path(temp_file.name)

    # Atomic rename (most filesystems guarantee this is atomic)
    temp_path.replace(file_path)


def validate_json_file(file_path: Path) -> bool:
    """
    Validate that a JSON file is not corrupted.

    Args:
        file_path: Path to the JSON file to validate

    Returns:
        True if file is valid JSON, False otherwise
    """
    if not file_path.exists():
        return False

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, IOError):
        return False


def recover_corrupted_files(config: CrawlerConfig, output) -> None:
    """
    Attempt to recover from corrupted files on startup.

    Args:
        config: Crawler configuration
        output: Output manager for logging
    """
    manifest_path = config.output.final_audio_dir / "manifest.json"
    url_file_path = config.output.url_outputs_dir / "discovered_urls.txt"

    # Check and recover manifest
    if manifest_path.exists() and not validate_json_file(manifest_path):
        output.warning(f"Manifest file {manifest_path} appears corrupted, attempting recovery")

        # Look for backup files
        backup_files = list(manifest_path.parent.glob(f"{manifest_path.stem}*backup*{manifest_path.suffix}"))
        if backup_files:
            # Use the most recent backup
            latest_backup = max(backup_files, key=lambda p: p.stat().st_mtime)
            if validate_json_file(latest_backup):
                output.info(f"Recovering manifest from backup: {latest_backup}")
                latest_backup.replace(manifest_path)
            else:
                output.error(f"Backup file {latest_backup} is also corrupted")
        else:
            output.error("No valid backup found for corrupted manifest")

    # For URL file, we can't easily recover from corruption, but we can check if it's valid
    if url_file_path.exists():
        try:
            with open(url_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Basic validation - check if it looks like URLs
                lines = content.split('\n')
                if lines and not any('http' in line for line in lines[:10]):
                    output.warning(f"URL file {url_file_path} may be corrupted")
        except IOError as e:
            output.warning(f"Cannot read URL file {url_file_path}: {e}")


@asynccontextmanager
async def crawler_lifecycle_manager(config: CrawlerConfig, output):
    """
    Context manager for crawler lifecycle that handles clean shutdown and state saving.

    Args:
        config: Crawler configuration
        output: Output manager for logging
    """
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        """Handle termination signals gracefully."""
        output.warning(f"Received signal {signum}, initiating clean shutdown...")
        shutdown_event.set()

    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # On Windows, SIGBREAK might be available
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)

    try:
        yield shutdown_event
    finally:
        output.info("Crawler lifecycle manager: cleanup completed")


async def run_crawler_workflow(config: CrawlerConfig) -> bool:
    """
    Run the complete crawler workflow.

    Args:
        config: Crawler configuration

    Returns:
        True if workflow completed successfully
    """
    output = get_output_manager()
    # progress = get_progress_tracker()  # Unused - removed to clean up imports

    # Reset upload session state for fresh workflow
    reset_upload_session()

    # Recover from any corrupted files first
    recover_corrupted_files(config, output)

    async with crawler_lifecycle_manager(config, output) as shutdown_event:
        output.info("=== YouTube Children's Voice Crawler ===")
        output.info(f"Starting workflow with {len(config.search.queries)} queries")

        # Helper function to create manifest backup
        def create_manifest_backup(phase_name: str) -> None:
            """Create a backup of the manifest after a phase completes."""
            try:
                file_manager = get_file_manager()
                manifest_path = config.output.final_audio_dir / "manifest.json"
                if manifest_path.exists():
                    backup_path = file_manager.create_backup(manifest_path, suffix=f"phase_{phase_name}")
                    output.debug(f"Created manifest backup after {phase_name}: {backup_path}")
                else:
                    output.debug(f"Manifest not found for backup after {phase_name}")
            except Exception as e:
                output.warning(f"Failed to create manifest backup after {phase_name}: {e}")

        processed_counter = [0]  # Use list to allow modification in nested functions

        # Define callback for batch processing (phases 2-4)
        async def process_batch(include_upload: bool = True, max_count: Optional[int] = None):
            """Process a batch of collected URLs through phases 2-4."""
            nonlocal processed_counter

            # Check for shutdown signal
            if shutdown_event.is_set():
                output.warning("Shutdown signal received, skipping batch processing")
                return

            output.info("=== Processing Batch ===")

            # Phase 2: Audio Download
            output.info("Batch Phase 2: Audio Download")
            downloaded_count = await run_download_phase_from_urls(config, None)  # Process all URLs so far
            output.success(f"Batch Phase 2 complete: {downloaded_count} audios downloaded")
            processed_counter[0] += downloaded_count
            await run_clean_phase(config, [])
            create_manifest_backup("download")

            # Check for shutdown signal
            if shutdown_event.is_set():
                output.warning("Shutdown signal received during batch processing")
                return

            # Phase 3: Audio Analysis
            output.info("Batch Phase 3: Audio Analysis")
            await run_analysis_phase(config, [])
            output.success("Batch Phase 3 complete: Audio analysis finished")
            await run_clean_phase(config, [])
            create_manifest_backup("analysis")

            # Check for shutdown signal
            if shutdown_event.is_set():
                output.warning("Shutdown signal received during batch processing")
                return

            # Phase 4: Content Filtering
            output.info("Batch Phase 4: Content Filtering")
            await run_filtering_phase(config)
            output.success("Batch Phase 4 complete: Content filtering finished")
            await run_clean_phase(config, [])
            create_manifest_backup("filtering")

            # Check for shutdown signal
            if shutdown_event.is_set():
                output.warning("Shutdown signal received during batch processing")
                return

            # Phase 5: File Upload (only if requested)
            if include_upload:
                output.info("Batch Phase 5: File Upload")
                await run_upload_phase(config, [])
                output.success("Batch Phase 5 complete: Files uploaded")
                await run_clean_phase(config, [])
                create_manifest_backup("upload")

            output.info("=== Batch Processing Complete ===")

        try:
            # Phase 0: Manifest Cleaning
            output.info("Phase 0: Manifest Cleaning")
            await run_clean_phase(config, [])
            output.success("Phase 0 complete: Manifest cleaning finished")
            create_manifest_backup("clean")

            # Check for shutdown signal
            if shutdown_event.is_set():
                output.warning("Shutdown signal received after manifest cleaning")
                return True

            # Phase 1: Video Discovery - collects URLs, triggers batch processing every 20 URLs
            try:
                output.info("Phase 1: Video Discovery")
                await run_search_phase(config, process_batch, processed_counter)
                output.success("Phase 1 complete: URL collection finished")
                create_manifest_backup("discovery")
            except Exception as e:
                output.error(f"Phase 1 failed due to API key issues or other errors: {e}. Moving on to processing existing URLs.")

            # Check for shutdown signal
            if shutdown_event.is_set():
                output.warning("Shutdown signal received after discovery phase")
                return True

            # Final batch processing for any remaining URLs
            if config.max_processed_urls is None:
                output.info("Running final batch processing")
                await process_batch(include_upload=True)
                create_manifest_backup("final")
            else:
                # Check if there are unprocessed URLs
                def extract_video_id_from_url(url: str) -> Optional[str]:
                    try:
                        from urllib.parse import urlparse, parse_qs
                        parsed = urlparse(url)
                        if 'youtube.com' in parsed.netloc:
                            return parse_qs(parsed.query).get('v', [None])[0]
                        elif 'youtu.be' in parsed.netloc:
                            return parsed.path[1:]
                    except Exception:
                        pass
                    return None

                manifest_file = config.output.final_audio_dir / "manifest.json"
                url_file = config.output.url_outputs_dir / "discovered_urls.txt"
                unprocessed_count = 0
                if url_file.exists() and manifest_file.exists():
                    try:
                        with open(url_file, 'r', encoding='utf-8') as f:
                            discovered_urls = set(line.strip() for line in f if line.strip())
                        with open(manifest_file, 'r', encoding='utf-8') as f:
                            manifest_data = json.load(f)
                        processed_video_ids = {record['video_id'] for record in manifest_data.get('records', [])}
                        unprocessed_urls = [url for url in discovered_urls if extract_video_id_from_url(url) not in processed_video_ids]
                        unprocessed_count = len(unprocessed_urls)
                    except Exception as e:
                        output.warning(f"Failed to check unprocessed count: {e}")

                if unprocessed_count > 0 and (config.max_processed_urls is None or processed_counter[0] < config.max_processed_urls):
                    remaining = config.max_processed_urls - processed_counter[0] if config.max_processed_urls else None
                    output.info("Running final batch processing")
                    await process_batch(include_upload=True, max_count=remaining)
                    create_manifest_backup("final")
                else:
                    if config.max_processed_urls and processed_counter[0] >= config.max_processed_urls:
                        output.info(f"Already reached maximum processed URLs ({config.max_processed_urls}), skipping final batch")
                    else:
                        output.info("No unprocessed URLs found, skipping final batch")

            # Check for shutdown signal
            if shutdown_event.is_set():
                output.warning("Shutdown signal received before final summary")
                return True

            # Final Summary
            output.info("=== Workflow Complete ===")

            # Load final manifest for summary
            manifest_file = config.output.final_audio_dir / "manifest.json"
            if manifest_file.exists():
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)

                final_count = len(manifest_data.get('records', []))
                total_duration = manifest_data.get('total_duration_seconds', 0)

                output.info(f"Final collection: {final_count} children's voice files")
                output.info(f"Total duration: {total_duration:.1f} seconds")
            else:
                output.warning("Manifest file not found for final summary")

            return True

        except Exception as e:
            output.error(f"Workflow failed: {e}")
            return False


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="YouTube Children's Voice Crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Run with default configuration
  python main.py --config custom.json     # Use custom config file
  python main.py --queries kids,songs     # Override queries
  python main.py --max-videos 100         # Limit total videos
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
        "--queries",
        type=str,
        nargs="+",
        help="Search queries (overrides config)"
    )

    parser.add_argument(
        "--max-videos",
        type=int,
        help="Maximum videos to process (overrides config)"
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
        "--dry-run",
        action="store_true",
        help="Validate configuration without running workflow"
    )

    parser.add_argument(
        "--max-processed-urls",
        type=int,
        help="Maximum number of URLs to process through phases 2-5 (default: unlimited)"
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
                "queries": args.queries,
                "max_videos": args.max_videos,
                "output_dir": args.output_dir,
                "verbose": args.verbose,
                "max_processed_urls": args.max_processed_urls
            }
        )
    except Exception as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    # Set up output manager
    output = get_output_manager()
    if config.logging.debug_mode:
        output.set_level("DEBUG")

    # Dry run
    if args.dry_run:
        output.info("Dry run - validating configuration")
        output.info(f"Queries: {config.search.queries}")
        output.info(f"Max videos per query: {config.search.target_videos_per_query}")
        output.info(f"Output directory: {config.output.base_dir}")
        output.success("Configuration is valid")
        return 0

    # Run workflow
    try:
        success = asyncio.run(run_crawler_workflow(config))
        return 0 if success else 1
    except KeyboardInterrupt:
        output.warning("Workflow interrupted by user - state has been preserved")
        return 130
    except Exception as e:
        output.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())