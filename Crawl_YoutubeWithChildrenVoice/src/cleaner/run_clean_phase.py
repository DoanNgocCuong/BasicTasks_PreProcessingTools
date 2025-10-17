#!/usr/bin/env python3
"""
Run Clean Phase Script

This script runs the manifest cleaning phase independently.
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
    from src.cleaner.clean_phases import run_clean_phase
    from src.utils import get_output_manager
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    print("This script should be run from the src/cleaner directory", file=sys.stderr)
    sys.exit(1)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Clean Phase for YouTube Children's Voice Crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_clean_phase.py                          # Run with default config
  python run_clean_phase.py --config custom.json     # Use custom config file
  python run_clean_phase.py --verbose                # Enable verbose logging
  python run_clean_phase.py --dry-run                # Validate configuration without running clean
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
        "--dry-run",
        action="store_true",
        help="Validate configuration without running clean"
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

    # Run clean phase
    try:
        output.info("Running clean phase for manifest")
        asyncio.run(run_clean_phase(config, []))
        output.success("Clean phase completed")
        return 0
    except KeyboardInterrupt:
        output.warning("Clean phase interrupted by user")
        return 130
    except Exception as e:
        output.error(f"Clean phase failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())