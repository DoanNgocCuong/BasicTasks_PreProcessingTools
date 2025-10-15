#!/usr/bin/env python3
"""
YouTube Children's Voice Crawler - Main Entry Point

A modular, async YouTube crawler for discovering and processing children's voice content.
Provides a single entry point for the entire workflow: search → download → analyze → filter.
"""

import asyncio
import sys
import argparse
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from .config import load_config, CrawlerConfig
from .crawler import SearchEngine
from .downloader import AudioDownloader
from .filterer import FiltererAPIClient
from .models import VideoMetadata, VideoSource
from .utils import get_output_manager, get_progress_tracker
from .crawler.youtube_api import YouTubeAPIClient

# Optional imports for analyzers
try:
    from .analyzer import VoiceClassifier, LanguageDetector
    from .analyzer.api_client import AnalysisAPIClient
    ANALYZERS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Analyzers not available: {e}")
    VoiceClassifier = None
    LanguageDetector = None
    AnalysisAPIClient = None
    ANALYZERS_AVAILABLE = False

# Optional import for transcript API
# Import is handled inside functions to avoid linter errors for optional dependencies


async def get_video_transcript(video_id: str) -> Optional[str]:
    """
    Get transcript from YouTube video.

    Args:
        video_id: YouTube video ID

    Returns:
        Transcript text or None if not available
    """
    try:
        import youtube_transcript_api  # type: ignore

        transcript_list = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([item['text'] for item in transcript_list])
        return transcript_text
    except ImportError:
        # youtube-transcript-api not available
        return None
    except Exception as e:
        # Transcript not available or other error
        return None


async def run_download_phase_from_urls(config: CrawlerConfig) -> int:
    """
    Run the audio download phase by reading URLs from the discovered URLs file.

    Args:
        config: Crawler configuration

    Returns:
        Number of successfully downloaded audios
    """
    output = get_output_manager()

    try:
        # Load URLs from the file created in search phase
        url_file = config.output.url_outputs_dir / "discovered_urls.txt"
        if not url_file.exists():
            output.warning(f"URL file not found: {url_file} - skipping download phase")
            return 0

        with open(url_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]

        if not urls:
            output.warning("No URLs found in file - skipping download phase")
            return 0

        output.info(f"Found {len(urls)} URLs to download")

        # Load existing manifest
        manifest_file = config.output.final_audio_dir / "manifest.json"
        manifest_file.parent.mkdir(parents=True, exist_ok=True)

        manifest_data = {"total_duration_seconds": 0.0, "records": []}
        if manifest_file.exists():
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                output.info(f"Loaded existing manifest with {len(manifest_data.get('records', []))} records")
            except Exception as e:
                output.warning(f"Failed to load existing manifest: {e} - starting fresh")

        existing_video_ids = {record['video_id'] for record in manifest_data.get('records', [])}

        downloader = AudioDownloader(config.download)

        # Initialize language detector for transcript analysis
        language_detector = None
        if hasattr(config.analysis, 'enable_language_detection') and config.analysis.enable_language_detection:
            from .analyzer.language_detector import LanguageDetector
            language_detector = LanguageDetector(config.analysis)
            lang_loaded = language_detector.load_model()
            if not lang_loaded:
                output.warning("Language detector model not loaded - transcript analysis disabled")
                language_detector = None

        downloaded_count = 0

        for url in urls:
            # Extract video ID from URL
            video_id = None
            if 'youtube.com/watch?v=' in url:
                video_id = url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in url:
                video_id = url.split('youtu.be/')[1].split('?')[0]

            if not video_id:
                output.warning(f"Could not extract video ID from URL: {url}")
                continue

            # Check if already in manifest
            if video_id in existing_video_ids:
                output.debug(f"Video {video_id} already processed, skipping")
                continue

            # Create VideoMetadata object for this URL
            # We'll need to get basic info from YouTube API
            try:
                # Get video details from YouTube API
                youtube_api = YouTubeAPIClient(config.youtube_api)
                video_details = youtube_api.get_video_details_batch([video_id])

                if video_id in video_details:
                    video_metadata = video_details[video_id]
                    video = VideoMetadata(
                        video_id=video_metadata.video_id,
                        title=video_metadata.title,
                        channel_id=video_metadata.channel_id,
                        channel_title=video_metadata.channel_title,
                        description=video_metadata.description,
                        published_at=video_metadata.published_at,
                        duration_seconds=video_metadata.duration_seconds,
                        view_count=video_metadata.view_count,
                        source=VideoSource.MANUAL
                    )
                else:
                    # Create minimal VideoMetadata
                    video = VideoMetadata(
                        video_id=video_id,
                        title=f'Video {video_id}',
                        channel_id='',
                        channel_title='',
                        description='',
                        source=VideoSource.MANUAL
                    )

            except Exception as e:
                output.warning(f"Failed to get video details for {video_id}: {e}")
                # Create minimal VideoMetadata
                video = VideoMetadata(
                    video_id=video_id,
                    title=f'Video {video_id}',
                    channel_id='',
                    channel_title='',
                    description='',
                    source=VideoSource.MANUAL
                )

            # Download audio
            result = await downloader.download_video_audio(video)

            if result.success and result.output_path:
                # Move file to unclassified folder
                unclassified_dir = config.output.final_audio_dir / "unclassified"
                unclassified_dir.mkdir(parents=True, exist_ok=True)

                new_filename = f"{video.video_id}_{Path(result.output_path).name}"
                new_path = unclassified_dir / new_filename

                # Move the file
                result.output_path.rename(new_path)
                result.output_path = new_path

                # Detect language using transcript (preferred method from working example)
                language_info = "unknown"
                if language_detector:
                    try:
                        # Use transcript-based detection (much more accurate)
                        transcript_result = language_detector.detect_language_from_youtube_transcript(video.video_id)
                        if transcript_result.is_successful:
                            language_info = transcript_result.detected_language.value
                            output.debug(f"Transcript language detection: {language_info} (confidence: {transcript_result.confidence:.2f})")
                        else:
                            # Fallback to transcript text analysis if available
                            transcript = await get_video_transcript(video.video_id)
                            if transcript:
                                text_result = language_detector.detect_language_from_text(transcript)
                                if text_result.is_successful:
                                    language_info = text_result.detected_language.value
                                    output.debug(f"Text language detection: {language_info} (confidence: {text_result.confidence:.2f})")
                    except Exception as e:
                        output.debug(f"Language detection failed for {video.video_id}: {e}")

                # Create manifest record
                record = {
                    "video_id": video.video_id,
                    "url": video.url,
                    "output_path": str(new_path),
                    "status": "success",
                    "timestamp": datetime.now().isoformat() + "Z",
                    "duration_seconds": result.duration or 0.0,
                    "title": video.title,
                    "language_folder": language_info,
                    "download_index": len(manifest_data['records']),
                    "classified": False
                }

                # Update manifest
                manifest_data['records'].append(record)
                manifest_data['total_duration_seconds'] += record['duration_seconds']

                # Save manifest
                with open(manifest_file, 'w', encoding='utf-8') as f:
                    json.dump(manifest_data, f, indent=2, ensure_ascii=False)

                downloaded_count += 1
                output.success(f"Downloaded and processed: {video.video_id}")
            else:
                output.warning(f"Download failed for {video.video_id}: {result.error_message}")

        output.success(f"Download phase completed: {downloaded_count}/{len(urls)} URLs processed")
        return downloaded_count

    except Exception as e:
        output.error(f"Download phase failed: {e}")
        return 0


async def run_search_phase(config: CrawlerConfig) -> List[VideoMetadata]:
    """
    Run the search and discovery phase.

    Args:
        config: Crawler configuration

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
        # Load manifest
        manifest_file = config.output.final_audio_dir / "manifest.json"
        if not manifest_file.exists():
            output.warning("Manifest file not found - skipping analysis phase")
            return videos

        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)

        # Check if we should run locally or use API
        run_locally = not config.analysis_api.enabled or config.analysis_api.server_url == "local"

        if run_locally:
            output.info("Running audio analysis locally")
            return await run_local_analysis(config, manifest_data, manifest_file)
        else:
            output.info("Running audio analysis via API")
            # API-based analysis
            if not AnalysisAPIClient:
                output.warning("Analysis API client not available - falling back to local analysis")
                return await run_local_analysis(config, manifest_data, manifest_file)

            async with AnalysisAPIClient(config.analysis_api) as client:
                # Convert manifest records to VideoMetadata objects for API
                api_videos = []
                for record in manifest_data.get('records', []):
                    if not record.get('classified', False):
                        # Create minimal VideoMetadata for unclassified records
                        video = VideoMetadata(
                            video_id=record['video_id'],
                            title=record.get('title', f"Video {record['video_id']}"),
                            channel_id='',
                            channel_title='',
                            description='',
                            source=VideoSource.MANUAL
                        )
                        # Add audio path if available
                        if 'output_path' in record:
                            video.audio_path = Path(record['output_path'])
                        api_videos.append(video)

                if api_videos:
                    results = await client.analyze_videos(api_videos)

                    # Update manifest with API results
                    for result in results:
                        for record in manifest_data.get('records', []):
                            if record['video_id'] == result.video_id:
                                record['classified'] = True
                                record['containing_children_voice'] = result.is_child_voice
                                record['voice_analysis_confidence'] = result.confidence
                                record['classification_timestamp'] = datetime.now().isoformat() + "Z"
                                break

                    # Save updated manifest
                    with open(manifest_file, 'w', encoding='utf-8') as f:
                        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

                    output.success(f"API analysis completed: {len(results)} videos analyzed")
                else:
                    output.info("No unclassified videos found for API analysis")

                return videos

    except Exception as e:
        output.error(f"Analysis phase failed: {e}")
        return videos


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
        # Load manifest
        manifest_file = config.output.final_audio_dir / "manifest.json"
        if not manifest_file.exists():
            output.warning("Manifest file not found - skipping filtering phase")
            return videos

        with open(manifest_file, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)

        # Filterer always runs locally for file operations
        output.info("Running content filtering locally")
        return await run_local_filtering(config, manifest_data, manifest_file)

    except Exception as e:
        output.error(f"Filtering phase failed: {e}")
        return videos


async def run_local_analysis(config: CrawlerConfig, manifest_data: dict, manifest_file: Path) -> List[VideoMetadata]:
    """
    Run audio analysis locally based on manifest data.

    Args:
        config: Crawler configuration
        manifest_data: Manifest data
        manifest_file: Path to manifest file

    Returns:
        List of videos with analysis results (empty for compatibility)
    """
    output = get_output_manager()

    # Initialize voice classifier
    if not ANALYZERS_AVAILABLE or VoiceClassifier is None:
        output.warning("Voice classifier not available - skipping analysis phase")
        return []

    voice_classifier = VoiceClassifier(config.analysis)
    voice_loaded = voice_classifier.load_model()

    if not voice_loaded:
        output.warning("Voice classifier model not loaded - skipping voice analysis")
        return []

    analyzed_count = 0

    for record in manifest_data.get('records', []):
        if record.get('classified', False):
            # Already classified, skip
            continue

        video_id = record['video_id']
        output_path = Path(record['output_path'])

        if not output_path.exists():
            output.warning(f"Audio file not found for {video_id}: {output_path}")
            continue

        # Analyze for children's voice
        voice_result = voice_classifier.classify_audio_file(output_path)

        # Update record
        record['classified'] = True
        record['containing_children_voice'] = voice_result.is_child_voice
        record['voice_analysis_confidence'] = voice_result.confidence
        record['classification_timestamp'] = datetime.now().isoformat() + "Z"

        if voice_result.is_child_voice:
            output.info(f"Children's voice detected in {video_id} (confidence: {voice_result.confidence:.2f})")
        else:
            output.debug(f"No children's voice in {video_id} (confidence: {voice_result.confidence:.2f})")

        analyzed_count += 1

    # Save updated manifest
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    output.success(f"Local analysis completed: {analyzed_count} files analyzed")
    return []


async def run_local_filtering(config: CrawlerConfig, manifest_data: dict, manifest_file: Path) -> List[VideoMetadata]:
    """
    Run content filtering locally based on manifest data.

    Args:
        config: Crawler configuration
        manifest_data: Manifest data
        manifest_file: Path to manifest file

    Returns:
        List of videos that passed filtering
    """
    output = get_output_manager()
    records_to_keep = []
    files_moved = 0
    entries_removed = 0

    # Build a map of all existing files in final_audio_files
    final_audio_dir = config.output.final_audio_dir
    existing_files = {}
    if final_audio_dir.exists():
        for file_path in final_audio_dir.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.wav', '.mp3', '.m4a']:
                existing_files[file_path.name] = file_path

    output.info(f"Found {len(existing_files)} audio files in {final_audio_dir}")

    for record in manifest_data.get('records', []):
        if not record.get('classified', False):
            # Not yet classified, keep for now
            records_to_keep.append(record)
            continue

        video_id = record['video_id']
        output_path = Path(record['output_path'])

        # Check if file exists at recorded path or in the file system
        file_exists = output_path.exists()
        if not file_exists and output_path.name in existing_files:
            # File exists but path is wrong, update path
            correct_path = existing_files[output_path.name]
            record['output_path'] = str(correct_path)
            output_path = correct_path
            file_exists = True
            output.debug(f"Corrected path for {video_id}: {output_path}")

        if not file_exists:
            output.warning(f"File not found for {video_id}: {output_path} - removing from manifest")
            entries_removed += 1
            continue

        # Check for children's voice
        has_children_voice = record.get('containing_children_voice', False)

        if has_children_voice:
            # Move to appropriate language folder
            language_folder = record.get('language_folder', 'unknown')
            target_dir = final_audio_dir / language_folder
            target_dir.mkdir(parents=True, exist_ok=True)

            target_path = target_dir / output_path.name

            # Check for duplicates
            if target_path.exists():
                output.warning(f"Duplicate file detected: {target_path} - skipping")
                entries_removed += 1
                continue

            # Move file
            output_path.rename(target_path)
            record['output_path'] = str(target_path)
            records_to_keep.append(record)
            files_moved += 1
            output.debug(f"Moved {video_id} to {language_folder} folder")
        else:
            # No children's voice - remove entry and file
            try:
                output_path.unlink()
                output.debug(f"Removed file without children's voice: {video_id}")
            except Exception as e:
                output.warning(f"Failed to remove file {output_path}: {e}")
            entries_removed += 1

    # Remove duplicate entries (same video_id)
    seen_video_ids = set()
    unique_records = []
    duplicates_removed = 0

    for record in records_to_keep:
        video_id = record['video_id']
        if video_id in seen_video_ids:
            duplicates_removed += 1
            continue
        seen_video_ids.add(video_id)
        unique_records.append(record)

    # Update manifest
    manifest_data['records'] = unique_records

    # Recalculate total duration
    total_duration = sum(record.get('duration_seconds', 0) for record in unique_records)
    manifest_data['total_duration_seconds'] = total_duration

    # Save updated manifest
    with open(manifest_file, 'w', encoding='utf-8') as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    output.success(f"Local filtering completed: {files_moved} files moved, {entries_removed} entries removed, {duplicates_removed} duplicates removed")
    output.info(f"Final manifest: {len(unique_records)} entries, {total_duration:.1f}s total duration")

    # Return videos that were kept (this is mainly for compatibility)
    # In practice, the manifest now contains the filtered results
    return []


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
        # Phase 1: Video Discovery - collects URLs, no videos returned
        output.info("Phase 1: Video Discovery")
        await run_search_phase(config)
        output.success("Phase 1 complete: URL collection finished")

        # Phase 2: Audio Download - downloads based on URLs, updates manifest
        output.info("Phase 2: Audio Download")
        # We don't pass videos from phase 1 since it returns empty list
        # Instead, download phase reads URLs from the file created in phase 1
        downloaded_count = await run_download_phase_from_urls(config)
        output.success(f"Phase 2 complete: {downloaded_count} audios downloaded")

        # Phase 3: Audio Analysis - analyzes downloaded files, updates manifest
        output.info("Phase 3: Audio Analysis")
        await run_analysis_phase(config, [])  # Empty list since analysis works with manifest
        output.success("Phase 3 complete: Audio analysis finished")

        # Phase 4: Content Filtering - filters and organizes files
        output.info("Phase 4: Content Filtering")
        await run_filtering_phase(config, [])  # Empty list since filtering works with manifest
        output.success("Phase 4 complete: Content filtering finished")

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