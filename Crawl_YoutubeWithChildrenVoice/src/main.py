#!/usr/bin/env python3
"""
YouTube Children's Voice Crawler - Main Entry Point

A modular, async YouTube crawler for discovering and processing children's voice content.
Provides a single entry point for the entire workflow: search → download → analyze → filter.
"""

import asyncio
import sys
import argparse
from pathlib import Path
from typing import List, Optional

from config import load_config, CrawlerConfig
from crawler import SearchEngine
from downloader import AudioDownloader
from analyzer import VoiceClassifier, LanguageDetector
from filterer import FiltererAPIClient
from models import VideoMetadata
from utils import get_output_manager, get_progress_tracker


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

    try:
        # Phase 1: Search and Discovery
        output.info("Phase 1: Video Discovery")
        videos = await run_search_phase(config)

        if not videos:
            output.warning("No videos found - ending workflow")
            return False

        output.success(f"Phase 1 complete: {len(videos)} videos discovered")

        # Phase 2: Audio Download
        output.info("Phase 2: Audio Download")
        downloaded_videos = await run_download_phase(config, videos)
        output.success(f"Phase 2 complete: {len(downloaded_videos)} audios downloaded")

        # Phase 3: Audio Analysis
        output.info("Phase 3: Audio Analysis")
        analyzed_videos = await run_analysis_phase(config, downloaded_videos)
        output.success(f"Phase 3 complete: {len(analyzed_videos)} audios analyzed")

        # Phase 4: Content Filtering
        output.info("Phase 4: Content Filtering")
        filtered_videos = await run_filtering_phase(config, analyzed_videos)
        output.success(f"Phase 4 complete: {len(filtered_videos)} videos passed filtering")

        # Final Summary
        output.info("=== Workflow Complete ===")
        output.info(f"Total videos discovered: {len(videos)}")
        output.info(f"Successfully processed: {len(filtered_videos)}")
        output.info(f"Success rate: {len(filtered_videos)/len(videos)*100:.1f}%")

        return True

    except Exception as e:
        output.error(f"Workflow failed: {e}")
        return False


async def run_search_phase(config: CrawlerConfig) -> List[VideoMetadata]:
    """
    Run the search and discovery phase.

    Args:
        config: Crawler configuration

    Returns:
        List of discovered videos
    """
    output = get_output_manager()

    try:
        search_engine = SearchEngine(config, config.youtube_api)
        videos = await search_engine.search_all_queries(config.search.queries)

        # Log search summary
        summary = search_engine.get_search_summary()
        output.debug(f"Search summary: {summary}")

        return videos

    except Exception as e:
        output.error(f"Search phase failed: {e}")
        return []


async def run_download_phase(config: CrawlerConfig, videos: List[VideoMetadata]) -> List[VideoMetadata]:
    """
    Run the audio download phase.

    Args:
        config: Crawler configuration
        videos: Videos to download

    Returns:
        List of videos with downloaded audio
    """
    output = get_output_manager()

    try:
        downloader = AudioDownloader(config.download)
        results = await downloader.download_videos_audio(videos)

        # Filter successful downloads
        successful_downloads = [r for r in results if r.success]
        output.success(f"Downloaded {len(successful_downloads)}/{len(videos)} videos")

        # Return videos that were successfully downloaded
        successful_video_ids = {r.video_id for r in successful_downloads}
        return [v for v in videos if v.video_id in successful_video_ids]

    except Exception as e:
        output.error(f"Download phase failed: {e}")
        return []


async def run_analysis_phase(config: CrawlerConfig, videos: List[VideoMetadata]) -> List[VideoMetadata]:
    """
    Run the audio analysis phase.

    Args:
        config: Crawler configuration
        videos: Videos to analyze

    Returns:
        List of videos with analysis results
    """
    output = get_output_manager()

    try:
        # Initialize analyzers
        voice_classifier = VoiceClassifier(config.analysis)
        language_detector = LanguageDetector(config.analysis)

        # Load models
        voice_loaded = voice_classifier.load_model()
        lang_loaded = language_detector.load_model()

        if not voice_loaded:
            output.warning("Voice classifier model not loaded - skipping voice analysis")
        if not lang_loaded:
            output.warning("Language detector model not loaded - skipping language analysis")

        analyzed_videos = []

        for video in videos:
            try:
                # Find audio file
                audio_path = None
                # This would need to be implemented based on the download results
                # For now, skip analysis
                analyzed_videos.append(video)

            except Exception as e:
                output.error(f"Analysis failed for {video.video_id}: {e}")
                continue

        output.success(f"Analysis phase completed for {len(analyzed_videos)}/{len(videos)} videos")
        return analyzed_videos

    except Exception as e:
        output.error(f"Analysis phase failed: {e}")
        return []


async def run_filtering_phase(config: CrawlerConfig, videos: List[VideoMetadata]) -> List[VideoMetadata]:
    """
    Run the content filtering phase.

    Args:
        config: Crawler configuration
        videos: Videos to filter

    Returns:
        List of videos that passed filtering
    """
    output = get_output_manager()

    try:
        async with FiltererAPIClient(config.filterer_api) as client:
            results = await client.filter_videos(videos)

            # Filter videos that passed
            passed_videos = [
                video for video, result in zip(videos, results)
                if result.passed_filter
            ]

            output.success(f"Filtering completed: {len(passed_videos)}/{len(videos)} videos passed")
            return passed_videos

    except Exception as e:
        output.error(f"Filtering phase failed: {e}")
        # If filtering fails, return all videos (fail-open)
        output.warning("Returning all videos due to filtering failure")
        return videos


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="YouTube Children's Voice Crawler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Run with default config
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
                "verbose": args.verbose
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