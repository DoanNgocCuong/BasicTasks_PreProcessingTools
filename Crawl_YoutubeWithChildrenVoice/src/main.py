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
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# Handle imports for both direct execution and module execution
if __name__ == "__main__" and __package__ is None:
    # Script is being run directly (not as a module)
    # Add the parent directory to Python path for relative imports
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    __package__ = "src"

from .config import load_config, CrawlerConfig
from .crawler import SearchEngine, run_search_phase
from .downloader import AudioDownloader, run_download_phase_from_urls
from .models import VideoMetadata, VideoSource
from .utils import get_output_manager, get_progress_tracker
from .crawler.youtube_api import YouTubeAPIClient
from .analyzer.analysis_phases import run_analysis_phase, run_local_analysis
from .filterer.filtering_phases import run_filtering_phase, run_local_filtering

# Optional import for transcript API
# Import is handled inside functions to avoid linter errors for optional dependencies


async def run_crawler_workflow(config: CrawlerConfig) -> bool:
    """
    Run the complete crawler workflow.

    Args:
        config: Crawler configuration

    Returns:
        True if workflow completed successfully
    """
    output = get_output_manager()
    progress = get_progress_tracker()

    output.info("=== YouTube Children's Voice Crawler ===")
    output.info(f"Starting workflow with {len(config.search.queries)} queries")

    # Define callback for batch processing (phases 2-4)
    async def process_batch():
        """Process a batch of collected URLs through phases 2-4."""
        output.info("=== Processing Batch ===")

        # Phase 2: Audio Download
        output.info("Batch Phase 2: Audio Download")
        downloaded_count = await run_download_phase_from_urls(config)
        output.success(f"Batch Phase 2 complete: {downloaded_count} audios downloaded")

        # Phase 3: Audio Analysis
        output.info("Batch Phase 3: Audio Analysis")
        await run_analysis_phase(config, [])
        output.success("Batch Phase 3 complete: Audio analysis finished")

        # Phase 4: Content Filtering
        output.info("Batch Phase 4: Content Filtering")
        await run_filtering_phase(config, [])
        output.success("Batch Phase 4 complete: Content filtering finished")

        output.info("=== Batch Processing Complete ===")

    try:
        # Phase 1: Video Discovery - collects URLs, triggers batch processing every 20 URLs
        output.info("Phase 1: Video Discovery")
        await run_search_phase(config, process_batch)
        output.success("Phase 1 complete: URL collection finished")

        # Final batch processing for any remaining URLs
        output.info("Running final batch processing")
        await process_batch()

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
  python main.py                          # Run offline (local analysis & filtering)
  python main.py --online                  # Run online (use API servers)
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
        "--online",
        action="store_true",
        help="Enable online mode (use API server for analysis instead of local processing)"
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
                "online": args.online
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
        output.warning("Workflow interrupted by user")
        return 130
    except Exception as e:
        output.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())