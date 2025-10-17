#!/usr/bin/env python3
"""
Run Discovery Phase Script

This script runs the video discovery (search) phase independently.
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
    from src.crawler.search_phases import run_search_phase
    from src.utils import get_output_manager
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    print("This script should be run from the src/crawler directory", file=sys.stderr)
    sys.exit(1)


async def dummy_batch_processor(include_upload: bool = True, max_count: int = None):
    """Dummy batch processor for standalone discovery phase."""
    output = get_output_manager()
    output.info("Discovery phase completed - no batch processing in standalone mode")
    return


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Discovery Phase for YouTube Children's Voice Crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_discovery_phase.py                          # Run with default config
  python run_discovery_phase.py --config custom.json     # Use custom config file
  python run_discovery_phase.py --verbose                # Enable verbose logging
  python run_discovery_phase.py --queries kids,toys      # Override search queries
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
        help="Maximum videos to discover per query (overrides config)"
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
        help="Validate configuration without running discovery"
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

    # Run discovery phase
    try:
        output.info("Running discovery phase (search phase)")
        asyncio.run(run_search_phase(config, dummy_batch_processor, [0]))
        output.success("Discovery phase completed")
        return 0
    except KeyboardInterrupt:
        output.warning("Discovery phase interrupted by user")
        return 130
    except Exception as e:
        output.error(f"Discovery phase failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())