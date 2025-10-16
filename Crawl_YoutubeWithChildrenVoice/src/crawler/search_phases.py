# crawler/search_phases.py

"""
Search Phase Implementation

This module contains the implementation of the video discovery and search phase.
"""

import asyncio
from pathlib import Path
import json
from typing import List, Optional, Dict, Any, Callable, Awaitable

from ..config import CrawlerConfig
from ..crawler import SearchEngine
from ..downloader import AudioDownloader
from ..models import VideoMetadata
from ..utils import get_output_manager
from ..analyzer.voice_classifier import VoiceClassifier
from ..crawler.youtube_api import QuotaExceededError
from constants import BATCH_PROCESSING_INTERVAL

# Optional imports for analyzers - moved inside functions to avoid loading at import time
ANALYZERS_AVAILABLE = True  # Will be set to False if import fails during runtime


async def run_search_phase(config: CrawlerConfig, batch_callback: Optional[Callable[..., Awaitable[None]]] = None, processed_counter: Optional[list] = None) -> List[VideoMetadata]:
    """
    Run the search and discovery phase.

    Args:
        config: Crawler configuration
        batch_callback: Optional callback to run when URLs are collected (every 20 for processing, every 200 for upload)

    Returns:
        List of discovered videos (empty since we only collect URLs)
    """
    output = get_output_manager()

    try:
        # Initialize search engine
        try:
            search_engine = SearchEngine(config, config.youtube_api)
            output.debug("Search engine initialized successfully")
        except Exception as e:
            output.error(f"Failed to initialize search engine: {e}")
            output.error(f"YouTube API config: {config.youtube_api}")
            import traceback
            output.error(f"Full traceback: {traceback.format_exc()}")
            return []

        # Create URL output file path
        url_output_file = config.output.url_outputs_dir / "discovered_urls.txt"
        metadata_output_file = config.output.url_outputs_dir / "discovered_videos.json"
        try:
            url_output_file.parent.mkdir(parents=True, exist_ok=True)
            output.debug(f"Created URL output directory: {url_output_file.parent}")
        except Exception as e:
            output.error(f"Failed to create URL output directory {url_output_file.parent}: {e}")
            return []

        # Load existing URLs to avoid duplicates
        existing_urls = set()
        discovered_videos = {}  # video_id -> VideoMetadata
        try:
            if url_output_file.exists():
                with open(url_output_file, 'r', encoding='utf-8') as f:
                    existing_urls = set(line.strip() for line in f if line.strip())
                output.info(f"Loaded {len(existing_urls)} existing URLs from {url_output_file}")
            else:
                output.debug(f"URL output file does not exist yet: {url_output_file}")

            # Load existing video metadata
            if metadata_output_file.exists():
                try:
                    with open(metadata_output_file, 'r', encoding='utf-8') as f:
                        metadata_list = json.load(f)
                        for video_dict in metadata_list:
                            try:
                                video = VideoMetadata.from_dict(video_dict)
                                discovered_videos[video.video_id] = video
                            except Exception as e:
                                output.warning(f"Failed to parse video metadata: {e}")
                        output.info(f"Loaded {len(discovered_videos)} existing video metadata records from {metadata_output_file}")
                except Exception as e:
                    output.error(f"Failed to load existing video metadata from {metadata_output_file}: {e}")
            else:
                output.debug(f"Metadata output file does not exist yet: {metadata_output_file}")
        except Exception as e:
            output.error(f"Failed to load existing URLs from {url_output_file}: {e}")
            output.error(f"File exists: {url_output_file.exists()}")
            return []

        # Track URL count for batch processing
        last_batch_count = len(existing_urls)

        # Process each query
        for query in config.search.queries:
            output.info(f"Processing query: '{query}'")

            # Search for videos using this query
            try:
                videos = await search_engine._search_single_query(query)
                output.debug(f"Found {len(videos)} videos for query '{query}'")
            except QuotaExceededError:
                output.error(f"YouTube API quota exceeded during search for query '{query}' - all keys exhausted")
                output.info("Search phase will stop processing additional queries")
                break  # Stop processing further queries
            except Exception as e:
                output.error(f"Failed to search for videos with query '{query}': {e}")
                output.error(f"Search engine type: {type(search_engine)}")
                import traceback
                output.error(f"Full traceback: {traceback.format_exc()}")
                continue

            if not videos:
                output.warning(f"No videos found for query '{query}'")
                continue

            # Take the first video for analysis
            first_video = videos[0]
            output.info(f"Analyzing first video: {first_video.video_id} - {first_video.title}")

            # Download audio for analysis
            try:
                downloader = AudioDownloader(config.download)
                download_result = await downloader.download_video_audio(first_video)
                output.debug(f"Download result for {first_video.video_id}: success={download_result.success}")
            except Exception as e:
                output.error(f"Failed to download audio for {first_video.video_id}: {e}")
                output.error(f"Video details: ID={first_video.video_id}, title={first_video.title}")
                import traceback
                output.error(f"Full traceback: {traceback.format_exc()}")
                continue

            if not download_result.success:
                output.warning(f"Failed to download audio for {first_video.video_id}, skipping query")
                
                # Log detailed error information from download attempts
                if download_result.attempts:
                    output.error(f"Download attempts for {first_video.video_id}:")
                    for i, attempt in enumerate(download_result.attempts, 1):
                        status = "SUCCESS" if attempt.success else "FAILED"
                        duration = f"{attempt.duration:.2f}s" if attempt.duration else "unknown"
                        output.error(f"  Attempt {i} ({attempt.method}): {status} in {duration}")
                        if attempt.error_message:
                            output.error(f"    Error: {attempt.error_message}")
                        if attempt.output_path:
                            output.error(f"    Output: {attempt.output_path} (exists: {attempt.output_path.exists()})")
                else:
                    output.error(f"No download attempts recorded for {first_video.video_id}")
                
                continue

            # Analyze for children's voice
            if not ANALYZERS_AVAILABLE or VoiceClassifier is None:
                output.warning("Voice classifier not available - skipping analysis")
                # Clean up downloaded audio
                if download_result.output_path and download_result.output_path.exists():
                    try:
                        download_result.output_path.unlink()
                        output.debug(f"Cleaned up temporary audio file for {first_video.video_id}")
                    except Exception as e:
                        output.warning(f"Failed to clean up temporary audio file {download_result.output_path}: {e}")
                continue

            # Load voice classifier
            try:
                voice_classifier = VoiceClassifier(config.analysis)
                voice_loaded = voice_classifier.load_model()
                output.debug(f"Voice classifier model loaded: {voice_loaded}")
            except Exception as e:
                output.error(f"Failed to initialize/load voice classifier: {e}")
                output.error(f"Analysis config: {config.analysis}")
                import traceback
                output.error(f"Full traceback: {traceback.format_exc()}")
                # Clean up downloaded audio
                if download_result.output_path and download_result.output_path.exists():
                    try:
                        download_result.output_path.unlink()
                    except Exception as e:
                        output.warning(f"Failed to clean up temporary audio file {download_result.output_path}: {e}")
                continue

            if not voice_loaded:
                output.warning("Voice classifier model not loaded - skipping analysis")
                # Clean up downloaded audio
                if download_result.output_path and download_result.output_path.exists():
                    try:
                        download_result.output_path.unlink()
                    except Exception as e:
                        output.warning(f"Failed to clean up temporary audio file {download_result.output_path}: {e}")
                continue

            # Perform voice analysis
            if download_result.output_path and download_result.output_path.exists():
                try:
                    voice_result = voice_classifier.classify_audio_file(download_result.output_path)
                    output.debug(f"Voice classification result for {first_video.video_id}: is_child={voice_result.is_child_voice}, confidence={voice_result.confidence}")
                except Exception as e:
                    output.error(f"Failed to classify audio for {first_video.video_id}: {e}")
                    output.error(f"Audio file path: {download_result.output_path}")
                    output.error(f"File exists: {download_result.output_path.exists()}")
                    import traceback
                    output.error(f"Full traceback: {traceback.format_exc()}")
                    # Clean up downloaded audio
                    try:
                        download_result.output_path.unlink()
                    except Exception as e:
                        output.warning(f"Failed to clean up temporary audio file {download_result.output_path}: {e}")
                    continue

                # Clean up downloaded audio immediately
                try:
                    download_result.output_path.unlink()
                    output.debug(f"Cleaned up temporary audio file for {first_video.video_id}")
                except Exception as e:
                    output.warning(f"Failed to clean up temporary audio file {download_result.output_path}: {e}")

                # Check if it contains children's voice
                if voice_result.is_child_voice:
                    output.success(f"Children's voice detected in {first_video.video_id} (confidence: {voice_result.confidence:.2f})")

                    # Add the first video's URL to output file
                    video_url = first_video.url
                    if video_url not in existing_urls:
                        try:
                            with open(url_output_file, 'a', encoding='utf-8') as f:
                                f.write(f"{video_url}\n")
                            existing_urls.add(video_url)
                            discovered_videos[first_video.video_id] = first_video
                            output.info(f"Added URL to output file: {video_url}")
                        except Exception as e:
                            output.error(f"Failed to write URL to output file {url_output_file}: {e}")
                            output.error(f"URL: {video_url}")
                            continue
                    else:
                        output.debug(f"URL already exists, skipping: {video_url}")

                    # Crawl the channel for more videos with the same query
                    try:
                        channel_videos = await search_engine._search_channel_videos(
                            channel_id=first_video.channel_id,
                            query=query,
                            max_results=config.search.max_similar_videos_per_channel
                        )
                        output.debug(f"Found {len(channel_videos)} additional videos from channel {first_video.channel_title}")
                    except QuotaExceededError:
                        output.error(f"YouTube API quota exceeded during channel search for '{query}' in channel {first_video.channel_title}")
                        output.info("Skipping channel exploration due to quota limits")
                        channel_videos = []
                    except Exception as e:
                        output.error(f"Failed to search channel videos for {first_video.channel_id}: {e}")
                        output.error(f"Channel ID: {first_video.channel_id}, Query: {query}")
                        import traceback
                        output.error(f"Full traceback: {traceback.format_exc()}")
                        channel_videos = []

                    # Add channel videos to URL output file (no duplicates)
                    new_urls_added = 0
                    for channel_video in channel_videos:
                        channel_url = channel_video.url
                        if channel_url not in existing_urls:
                            try:
                                with open(url_output_file, 'a', encoding='utf-8') as f:
                                    f.write(f"{channel_url}\n")
                                existing_urls.add(channel_url)
                                discovered_videos[channel_video.video_id] = channel_video
                                new_urls_added += 1
                            except Exception as e:
                                output.error(f"Failed to write channel URL to output file {url_output_file}: {e}")
                                output.error(f"Channel URL: {channel_url}")
                                continue

                    output.success(f"Added {new_urls_added} additional URLs from channel {first_video.channel_title}")

                    # Check if we should trigger batch processing
                    current_url_count = len(existing_urls)
                    
                    # Trigger batch processing every 20 URLs (with upload)
                    if batch_callback:
                        # Calculate remaining
                        remaining = config.max_processed_urls - processed_counter[0] if processed_counter and config.max_processed_urls else None
                        max_count = remaining if remaining and remaining > 0 else None
                        
                        if current_url_count - last_batch_count >= BATCH_PROCESSING_INTERVAL:
                            output.info(f"Collected {current_url_count - last_batch_count} new URLs, triggering batch processing (with upload)")
                            try:
                                await batch_callback(include_upload=True, max_count=max_count)
                                last_batch_count = current_url_count
                                
                                # Check if we've reached max processed URLs
                                if processed_counter and config.max_processed_urls and processed_counter[0] >= config.max_processed_urls:
                                    output.info(f"Reached maximum processed URLs ({config.max_processed_urls}), stopping discovery")
                                    break
                            except Exception as e:
                                output.error(f"Failed to execute batch callback: {e}")
                                import traceback
                                output.error(f"Full traceback: {traceback.format_exc()}")
                else:
                    output.info(f"No children's voice detected in {first_video.video_id} (confidence: {voice_result.confidence:.2f}) - skipping query")
            else:
                output.warning(f"Audio file not found for analysis: {first_video.video_id}")
                continue

        output.success(f"Video discovery phase completed. Total URLs collected: {len(existing_urls)}")
        
        # Save discovered video metadata
        if discovered_videos:
            try:
                metadata_list = [video.to_dict() for video in discovered_videos.values()]
                with open(metadata_output_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata_list, f, ensure_ascii=False, indent=2)
                output.info(f"Saved {len(discovered_videos)} video metadata records to {metadata_output_file}")
            except Exception as e:
                output.error(f"Failed to save video metadata to {metadata_output_file}: {e}")
        
        return []  # Return empty list since we don't need to pass videos to next phase

    except Exception as e:
        output.error(f"Search phase failed: {e}")
        output.error(f"Config search settings: queries={config.search.queries}, target_videos={config.search.target_videos_per_query}")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")
        return []