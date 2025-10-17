#!/usr/bin/env python3
"""
Run Filtering Phase Script

This script runs the content filtering phase independently.
"""

import asyncio
import sys
import argparse
import os

# Handle imports for both direct execution and module execution
if __name__ == "__main__" and __package__ is None:
    # Script is being run directly (not as a module)
    # Add the parent directory to Python path for relative imports
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    __package__ = "src"

try:
    from src.config import load_config, CrawlerConfig
    from src.filterer.filtering_phases import run_filtering_phase
    from src.utils import get_output_manager
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    print("This script should be run from the src/filterer directory", file=sys.stderr)
    sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Filtering Phase for YouTube Children's Voice Crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_filtering_phase.py                          # Run with default config
  python run_filtering_phase.py --config custom.json     # Use custom config file
  python run_filtering_phase.py --verbose                # Enable verbose logging
  python run_filtering_phase.py --video-ids vid1,vid2    # Filter specific videos
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
        help="Comma-separated list of specific video IDs to filter (default: all unfiltered)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration without running filtering"
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

    # Run filtering phase
    try:
        if video_ids:
            output.info(f"Running filtering phase for specific videos: {video_ids}")
            asyncio.run(run_filtering_phase(config, video_ids))
        else:
            output.info("Running filtering phase for all unfiltered videos")
            asyncio.run(run_filtering_phase(config))
        output.success("Filtering phase completed")
        return 0
    except KeyboardInterrupt:
        output.warning("Filtering phase interrupted by user")
        return 130
    except Exception as e:
        output.error(f"Filtering phase failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())