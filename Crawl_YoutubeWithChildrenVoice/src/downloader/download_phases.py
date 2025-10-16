# downloader/download_phases.py

"""
Download Phase Implementation

This module contains the implementation of the audio download phase.
"""

import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
import re

from ..config import CrawlerConfig
from ..downloader import AudioDownloader
from ..models import VideoMetadata, VideoSource
from ..utils import get_output_manager, get_file_manager
from ..crawler.youtube_api import YouTubeAPIClient


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
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


def get_video_title(url: str, fallback_title: Optional[str] = None, manifest_data: Optional[Dict] = None, video_id: Optional[str] = None) -> Optional[str]:
    """Get video title using available methods with fallbacks."""
    try:
        from pytube import YouTube
        title = YouTube(url).title
        if title:
            return title
    except Exception:
        pass
    
    # Fallback to provided title
    if fallback_title:
        return fallback_title
    
    # Fallback to manifest
    if manifest_data and video_id:
        for record in manifest_data.get('records', []):
            if record.get('video_id') == video_id and record.get('title'):
                return record['title']
    
    return None


def to_camel_case(text: str, max_len: int = 40) -> str:
    """Convert text to camelCase."""
    try:
        words = re.split(r'[^a-z0-9]+', (text or '').lower())
        words = [w for w in words if w]
        camel = ''.join(w.capitalize() for w in words)
        return camel[:max_len] if camel else 'NoTitle'
    except Exception:
        return 'NoTitle'


def build_filename(index: int, url: str, extension: str = "wav", title: Optional[str] = None, manifest_data: Optional[Dict] = None, video_id: Optional[str] = None) -> str:
    """Build consistent filename with video info."""
    try:
        vid = extract_video_id(url)
        # Use provided title, or try to fetch it with fallbacks
        video_title = title or get_video_title(url, None, manifest_data, video_id)
        camel_title = to_camel_case(video_title) if video_title else 'NoTitle'
        short_id = (vid or 'noid')[:8]
        return f"{index:04d}_{short_id}_{camel_title}.{extension}"
    except Exception:
        return f"{index:04d}_unknown.{extension}"


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
            from ..analyzer.language_detector import LanguageDetector
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
                # Prepare file paths and manifest record BEFORE moving
                unclassified_dir = config.output.final_audio_dir / "unclassified"
                unclassified_dir.mkdir(parents=True, exist_ok=True)

                # Use new naming convention
                download_index = len(manifest_data['records'])
                new_filename = build_filename(download_index, url, "wav", video.title, manifest_data, video.video_id)
                new_path = unclassified_dir / new_filename

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
                    "title": get_video_title(url, video.title, manifest_data, video.video_id) or video.title,  # Use fetched title if available
                    "language_folder": language_info,
                    "download_index": download_index,
                    "classified": False
                }

                # Update manifest data in memory
                manifest_data['records'].append(record)
                manifest_data['total_duration_seconds'] += record['duration_seconds']

                # Save manifest BEFORE moving file (atomic operation)
                file_manager = get_file_manager()
                if not file_manager.save_json(manifest_file, manifest_data):
                    output.error(f"Failed to save manifest for {video.video_id} - skipping download")
                    # Rollback in-memory changes
                    manifest_data['records'].pop()
                    manifest_data['total_duration_seconds'] -= record['duration_seconds']
                    continue

                # Now move the file (after manifest is safely updated)
                try:
                    result.output_path.rename(new_path)
                    result.output_path = new_path
                    output.debug(f"Successfully moved file to: {new_path}")
                except Exception as e:
                    output.error(f"Failed to move file for {video.video_id}: {e}")
                    # Rollback manifest changes since file move failed
                    try:
                        manifest_data['records'].pop()
                        manifest_data['total_duration_seconds'] -= record['duration_seconds']
                        file_manager.save_json(manifest_file, manifest_data)
                        output.debug(f"Rolled back manifest changes for {video.video_id}")
                    except Exception as rollback_e:
                        output.error(f"Failed to rollback manifest for {video.video_id}: {rollback_e}")
                    continue

                # Clean up any remaining temp files in audio_outputs_dir
                try:
                    audio_outputs_dir = config.output.audio_outputs_dir
                    for temp_file in audio_outputs_dir.glob("*.mp3"):
                        try:
                            temp_file.unlink()
                            output.debug(f"Cleaned up temp file: {temp_file}")
                        except Exception as e:
                            output.warning(f"Failed to clean up temp file {temp_file}: {e}")
                except Exception as e:
                    output.warning(f"Error during temp file cleanup: {e}")

                downloaded_count += 1
                output.success(f"Downloaded and processed: {video.video_id}")
            else:
                output.warning(f"Download failed for {video.video_id}: {result.error_message}")
                
                # Clean up temp file if it exists
                if result.output_path and result.output_path.exists():
                    try:
                        result.output_path.unlink()
                        output.debug(f"Cleaned up failed download temp file: {result.output_path}")
                    except Exception as e:
                        output.warning(f"Failed to clean up failed download temp file {result.output_path}: {e}")
                
                # Create failed manifest record to prevent re-attempts
                failed_record = {
                    "video_id": video.video_id,
                    "url": url,
                    "output_path": None,
                    "status": "failed",
                    "timestamp": datetime.now().isoformat() + "Z",
                    "duration_seconds": 0.0,
                    "title": get_video_title(url, video.title, manifest_data, video.video_id) or video.title,
                    "language_folder": "unknown",
                    "download_index": len(manifest_data['records']),
                    "classified": False
                }
                
                # Update manifest with failed record
                manifest_data['records'].append(failed_record)
                
                # Save manifest atomically
                file_manager = get_file_manager()
                file_manager.save_json(manifest_file, manifest_data)

        output.success(f"Download phase completed: {downloaded_count}/{len(urls)} URLs processed")
        return downloaded_count

    except Exception as e:
        output.error(f"Download phase failed: {e}")
        
        # Clean up any remaining temp files on error
        try:
            audio_outputs_dir = config.output.audio_outputs_dir
            for temp_file in audio_outputs_dir.glob("*.mp3"):
                try:
                    temp_file.unlink()
                    output.debug(f"Cleaned up temp file on error: {temp_file}")
                except Exception as cleanup_e:
                    output.warning(f"Failed to clean up temp file {temp_file}: {cleanup_e}")
        except Exception as cleanup_e:
            output.warning(f"Error during temp file cleanup on error: {cleanup_e}")
        
        return 0