# crawler/search_phases.py

"""
Search Phase Implementation

This module contains the implementation of the video discovery and search phase.
"""

import asyncio
from pathlib import Path
from typing import List, Optional, Callable, Awaitable

from ..config import CrawlerConfig
from ..crawler import SearchEngine
from ..downloader import AudioDownloader
from ..models import VideoMetadata
from ..utils import get_output_manager
from ..analyzer.voice_classifier import VoiceClassifier

# Optional imports for analyzers - moved inside functions to avoid loading at import time
ANALYZERS_AVAILABLE = True  # Will be set to False if import fails during runtime


async def run_search_phase(config: CrawlerConfig, batch_callback: Optional[Callable[[], Awaitable[None]]] = None) -> List[VideoMetadata]:
    """
    Run the search and discovery phase.

    Args:
        config: Crawler configuration
        batch_callback: Optional callback to run when 20 URLs are collected

    Returns:
        List of discovered videos (empty since we only collect URLs)
    """
    output = get_output_manager()

    try:
        search_engine = SearchEngine(config, config.youtube_api)

        # Create URL output file path
        url_output_file = config.output.url_outputs_dir / "discovered_urls.txt"
        url_output_file.parent.mkdir(parents=True, exist_ok=True)

        # Load existing URLs to avoid duplicates
        existing_urls = set()
        if url_output_file.exists():
            with open(url_output_file, 'r', encoding='utf-8') as f:
                existing_urls = set(line.strip() for line in f if line.strip())

        output.info(f"Loaded {len(existing_urls)} existing URLs from {url_output_file}")

        # Track URL count for batch processing
        last_batch_count = len(existing_urls)

        # Process each query
        for query in config.search.queries:
            output.info(f"Processing query: '{query}'")

            # Search for videos using this query
            videos = await search_engine._search_single_query(query)

            if not videos:
                output.warning(f"No videos found for query '{query}'")
                continue

            # Take the first video for analysis
            first_video = videos[0]
            output.info(f"Analyzing first video: {first_video.video_id} - {first_video.title}")

            # Download audio for analysis
            downloader = AudioDownloader(config.download)
            download_result = await downloader.download_video_audio(first_video)

            if not download_result.success:
                output.warning(f"Failed to download audio for {first_video.video_id}, skipping query")
                continue

            # Analyze for children's voice
            if not ANALYZERS_AVAILABLE or VoiceClassifier is None:
                output.warning("Voice classifier not available - skipping analysis")
                # Clean up downloaded audio
                if download_result.output_path and download_result.output_path.exists():
                    download_result.output_path.unlink()
                continue

            voice_classifier = VoiceClassifier(config.analysis)
            voice_loaded = voice_classifier.load_model()

            if not voice_loaded:
                output.warning("Voice classifier model not loaded - skipping analysis")
                # Clean up downloaded audio
                if download_result.output_path and download_result.output_path.exists():
                    download_result.output_path.unlink()
                continue

            # Perform voice analysis
            if download_result.output_path and download_result.output_path.exists():
                voice_result = voice_classifier.classify_audio_file(download_result.output_path)

                # Clean up downloaded audio immediately
                download_result.output_path.unlink()
                output.debug(f"Cleaned up temporary audio file for {first_video.video_id}")

                # Check if it contains children's voice
                if voice_result.is_child_voice:
                    output.success(f"Children's voice detected in {first_video.video_id} (confidence: {voice_result.confidence:.2f})")

                    # Add the first video's URL to output file
                    video_url = first_video.url
                    if video_url not in existing_urls:
                        with open(url_output_file, 'a', encoding='utf-8') as f:
                            f.write(f"{video_url}\n")
                        existing_urls.add(video_url)
                        output.info(f"Added URL to output file: {video_url}")

                    # Crawl the channel for more videos with the same query
                    channel_videos = await search_engine._search_channel_videos(
                        channel_id=first_video.channel_id,
                        query=query,
                        max_results=config.search.max_similar_videos_per_channel
                    )

                    # Add channel videos to URL output file (no duplicates)
                    new_urls_added = 0
                    for channel_video in channel_videos:
                        channel_url = channel_video.url
                        if channel_url not in existing_urls:
                            with open(url_output_file, 'a', encoding='utf-8') as f:
                                f.write(f"{channel_url}\n")
                            existing_urls.add(channel_url)
                            new_urls_added += 1

                    output.success(f"Added {new_urls_added} additional URLs from channel {first_video.channel_title}")

                    # Check if we should trigger batch processing
                    current_url_count = len(existing_urls)
                    if batch_callback and current_url_count - last_batch_count >= 20:
                        output.info(f"Collected {current_url_count - last_batch_count} new URLs, triggering batch processing")
                        await batch_callback()
                        last_batch_count = current_url_count
                else:
                    output.info(f"No children's voice detected in {first_video.video_id} (confidence: {voice_result.confidence:.2f}) - skipping query")
            else:
                output.warning(f"Audio file not found for analysis: {first_video.video_id}")
                continue

        output.success(f"Video discovery phase completed. Total URLs collected: {len(existing_urls)}")
        return []  # Return empty list since we don't need to pass videos to next phase

    except Exception as e:
        output.error(f"Search phase failed: {e}")
        return []