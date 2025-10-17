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
from ..constants import DEFAULT_MAX_FILENAME_LENGTH


def migrate_legacy_classification_fields(record: Dict) -> Dict:
    """
    Migrate legacy classification fields to current naming convention.
    
    Args:
        record: Manifest record dictionary
        
    Returns:
        Updated record with migrated fields
    """
    # Migrate legacy has_children_voice field to containing_children_voice
    if 'has_children_voice' in record and record['has_children_voice'] is not None:
        if 'containing_children_voice' not in record or record['containing_children_voice'] is None:
            record['containing_children_voice'] = record['has_children_voice']
        # Remove legacy field after migration
        del record['has_children_voice']
    
    return record


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


def to_camel_case(text: str, max_len: int = DEFAULT_MAX_FILENAME_LENGTH) -> str:
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


async def run_download_phase_from_urls(config: CrawlerConfig, max_count: Optional[int] = None) -> int:
    """
    Run the audio download phase by reading URLs from the discovered URLs file.

    Args:
        config: Crawler configuration
        max_count: Maximum number of URLs to process (None for unlimited)

    Returns:
        Number of successfully downloaded audios
    """
    output = get_output_manager()

    try:
        # Load URLs from the file created in search phase
        url_file = config.output.url_outputs_dir / "discovered_urls.txt"
        metadata_file = config.output.url_outputs_dir / "discovered_videos.json"
        
        # Load video metadata from discovery phase
        video_metadata = {}  # video_id -> VideoMetadata
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_list = json.load(f)
                    for video_dict in metadata_list:
                        try:
                            video = VideoMetadata.from_dict(video_dict)
                            video_metadata[video.video_id] = video
                        except Exception as e:
                            output.warning(f"Failed to parse video metadata: {e}")
                    output.info(f"Loaded {len(video_metadata)} video metadata records from discovery phase")
            except Exception as e:
                output.error(f"Failed to load video metadata from {metadata_file}: {e}")
                output.warning("Will create minimal metadata from URLs")
        else:
            output.warning(f"Video metadata file not found: {metadata_file} - will create minimal metadata from URLs")

        if not url_file.exists():
            output.warning(f"URL file not found: {url_file} - skipping download phase")
            return 0

        try:
            with open(url_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            output.info(f"Found {len(urls)} URLs to download")
        except Exception as e:
            output.error(f"Failed to read URL file {url_file}: {e}")
            output.error(f"File exists: {url_file.exists()}")
            if url_file.exists():
                output.error(f"File size: {url_file.stat().st_size} bytes")
            return 0

        if not urls:
            output.warning("No URLs found in file - skipping download phase")
            return 0

        # Load existing manifest
        manifest_file = config.output.final_audio_dir / "manifest.json"
        try:
            manifest_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            output.error(f"Failed to create manifest directory {manifest_file.parent}: {e}")
            return 0

        manifest_data = {"total_duration_seconds": 0.0, "records": []}
        if manifest_file.exists():
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                # Migrate legacy classification fields in all records
                for record in manifest_data.get('records', []):
                    migrate_legacy_classification_fields(record)
                output.info(f"Loaded existing manifest with {len(manifest_data.get('records', []))} records")
            except json.JSONDecodeError as e:
                output.error(f"Failed to parse existing manifest JSON at {manifest_file}: {e}")
                output.error(f"Manifest file may be corrupted. Starting with empty manifest.")
            except IOError as e:
                output.error(f"Failed to read existing manifest file at {manifest_file}: {e}")
                output.error(f"Check file permissions. Starting with empty manifest.")
            except Exception as e:
                output.error(f"Unexpected error loading existing manifest at {manifest_file}: {e}")
                output.error(f"Starting with empty manifest.")

        existing_records = {record['video_id']: record for record in manifest_data.get('records', []) if record.get('video_id')}

        # Initialize downloader
        try:
            downloader = AudioDownloader(config.download)
            output.debug("Audio downloader initialized successfully")
        except Exception as e:
            output.error(f"Failed to initialize audio downloader: {e}")
            output.error(f"Download config: {config.download}")
            import traceback
            output.error(f"Full traceback: {traceback.format_exc()}")
            return 0

        # Initialize language detector for transcript analysis
        language_detector = None
        if hasattr(config.analysis, 'enable_language_detection') and config.analysis.enable_language_detection:
            try:
                from ..analyzer.language_detector import LanguageDetector
                language_detector = LanguageDetector(config.analysis)
                lang_loaded = language_detector.load_model()
                if not lang_loaded:
                    output.warning("Language detector model not loaded - transcript analysis disabled")
                    language_detector = None
                else:
                    output.debug("Language detector initialized successfully")
            except Exception as e:
                output.error(f"Failed to initialize language detector: {e}")
                output.error(f"Analysis config: {config.analysis}")
                language_detector = None

        downloaded_count = 0
        processed_count = 0

        for url in urls:
            # Extract video ID from URL
            video_id = None
            try:
                if 'youtube.com/watch?v=' in url:
                    video_id = url.split('v=')[1].split('&')[0]
                elif 'youtu.be/' in url:
                    video_id = url.split('youtu.be/')[1].split('?')[0]
            except Exception as e:
                output.warning(f"Failed to extract video ID from URL {url}: {e}")
                continue

            if not video_id:
                output.warning(f"Could not extract video ID from URL: {url}")
                continue

            # Check if already in manifest and if we should redownload
            should_redownload = False
            existing_record = None
            classification_incomplete = False
            if video_id in existing_records:
                existing_record = existing_records[video_id]
                classified = existing_record.get('classified', False)
                uploaded = existing_record.get('uploaded', False)
                file_available = existing_record.get('file_available', True)  # Default to True for old records
                all_downloads_failed = existing_record.get('all_downloads_failed', False)
                containing_children_voice = existing_record.get('containing_children_voice')
                
                # Skip if all downloads have already failed
                if all_downloads_failed:
                    output.debug(f"Video {video_id} has all_downloads_failed=true, skipping")
                    continue
                
                # Skip videos that were classified as not containing children voice
                if classified and containing_children_voice == False:
                    output.debug(f"Video {video_id} classified as not containing children voice, skipping redownload")
                    continue
                
                # Check if classification data is incomplete (classified=true but missing key fields)
                classification_incomplete = (classified and 
                    (existing_record.get('classification_timestamp') is None or 
                     existing_record.get('containing_children_voice') is None))
                
                # Conditions for redownload
                if not classified and not file_available:
                    should_redownload = True
                elif classified and not uploaded and not file_available:
                    should_redownload = True
                elif classification_incomplete:
                    # Redownload if classification data is incomplete, regardless of file availability
                    should_redownload = True
                    output.info(f"Redownloading {video_id} due to incomplete classification data (classified: {classified}, timestamp: {existing_record.get('classification_timestamp')}, children_voice: {existing_record.get('containing_children_voice')})")
                
                if not should_redownload:
                    output.debug(f"Video {video_id} already processed and meets skip conditions, skipping")
                    continue
                else:
                    if not classification_incomplete:
                        output.info(f"Redownloading {video_id} due to missing file (classified: {classified}, uploaded: {uploaded}, file_available: {file_available})")
            else:
                # New video, download
                should_redownload = True

            # Get video metadata from discovery phase or create minimal metadata
            if video_id in video_metadata:
                video = video_metadata[video_id]
                output.debug(f"Using metadata from discovery phase for {video_id}: {video.title}")
            else:
                # Create minimal VideoMetadata if not found in discovery metadata
                video = VideoMetadata(
                    video_id=video_id,
                    title=f'Video {video_id}',
                    channel_id='',
                    channel_title='',
                    description='',
                    source=VideoSource.MANUAL
                )
                output.debug(f"Created minimal video metadata for {video_id} (not found in discovery metadata)")

            # Download audio
            try:
                result = await downloader.download_video_audio(video)
                output.debug(f"Download result for {video_id}: success={result.success}, duration={result.duration}")
            except Exception as e:
                output.error(f"Download operation failed for {video_id}: {e}")
                output.error(f"Video details: ID={video_id}, title={video.title}")
                import traceback
                output.error(f"Full traceback: {traceback.format_exc()}")
                result = None

            if result and result.success and result.output_path:
                # Prepare file paths and manifest record BEFORE moving
                unclassified_dir = config.output.final_audio_dir / "unclassified"
                try:
                    unclassified_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    output.error(f"Failed to create unclassified directory {unclassified_dir}: {e}")
                    # Clean up temp file
                    if result.output_path.exists():
                        try:
                            result.output_path.unlink()
                        except Exception as cleanup_e:
                            output.warning(f"Failed to clean up temp file {result.output_path}: {cleanup_e}")
                    continue

                # Use new naming convention
                download_index = existing_record.get('download_index', len(manifest_data['records'])) if existing_record else len(manifest_data['records'])
                try:
                    new_filename = build_filename(download_index, url, "wav", video.title, manifest_data, video.video_id)
                    new_path = unclassified_dir / new_filename
                    output.debug(f"Generated filename: {new_filename}")
                except Exception as e:
                    output.error(f"Failed to build filename for {video_id}: {e}")
                    output.error(f"Download index: {download_index}, URL: {url}, Title: {video.title}")
                    # Clean up temp file
                    if result.output_path.exists():
                        try:
                            result.output_path.unlink()
                        except Exception as cleanup_e:
                            output.warning(f"Failed to clean up temp file {result.output_path}: {cleanup_e}")
                    continue

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

                # Create or update manifest record
                if existing_record:
                    # Reset classification fields if we're redownloading due to incomplete classification
                    update_data = {
                        "output_path": str(new_path),
                        "status": "success",
                        "timestamp": datetime.now().isoformat() + "Z",
                        "duration_seconds": result.duration or 0.0,
                        "title": get_video_title(url, video.title, manifest_data, video.video_id) or video.title,
                        "language_folder": language_info,
                        "file_available": True
                    }
                    
                    # Reset classification if it was incomplete
                    if 'classification_incomplete' in locals() and classification_incomplete:
                        update_data.update({
                            "classified": False,
                            "classification_timestamp": None,
                            "containing_children_voice": None,
                            "voice_analysis_confidence": 0.0
                        })
                        output.debug(f"Reset classification fields for {video_id} due to incomplete data")
                    
                    existing_record.update(update_data)
                    # Update total duration if duration changed
                    old_duration = existing_record.get('duration_seconds', 0.0) or 0.0
                    manifest_data['total_duration_seconds'] -= old_duration
                    manifest_data['total_duration_seconds'] += result.duration or 0.0
                    record = existing_record
                else:
                    # Create new record
                    record = {
                        "video_id": video.video_id,
                        "url": video.url,
                        "output_path": str(new_path),
                        "status": "success",
                        "timestamp": datetime.now().isoformat() + "Z",
                        "duration_seconds": result.duration or 0.0,
                        "title": get_video_title(url, video.title, manifest_data, video.video_id) or video.title,
                        "language_folder": language_info,
                        "download_index": download_index,
                        "classified": False,
                        "file_available": True
                    }
                    # Update manifest data in memory
                    manifest_data['records'].append(record)
                    manifest_data['total_duration_seconds'] += record['duration_seconds']

                # Save manifest BEFORE moving file (atomic operation)
                try:
                    file_manager = get_file_manager()
                    if not file_manager.save_json(manifest_file, manifest_data):
                        output.error(f"Failed to save manifest for {video_id} - skipping download")
                        # Rollback in-memory changes
                        manifest_data['records'].pop()
                        manifest_data['total_duration_seconds'] -= record['duration_seconds']
                        # Clean up temp file
                        if result.output_path.exists():
                            try:
                                result.output_path.unlink()
                            except Exception as cleanup_e:
                                output.warning(f"Failed to clean up temp file {result.output_path}: {cleanup_e}")
                        continue
                except Exception as e:
                    output.error(f"Failed to save manifest for {video_id}: {e}")
                    # Rollback in-memory changes
                    manifest_data['records'].pop()
                    manifest_data['total_duration_seconds'] -= record['duration_seconds']
                    # Clean up temp file
                    if result.output_path.exists():
                        try:
                            result.output_path.unlink()
                        except Exception as cleanup_e:
                            output.warning(f"Failed to clean up temp file {result.output_path}: {cleanup_e}")
                    continue

                # Now move the file (after manifest is safely updated)
                try:
                    if new_path.exists():
                        new_path.unlink()  # Remove existing file
                        output.debug(f"Removed existing file: {new_path}")
                    result.output_path.rename(new_path)
                    result.output_path = new_path
                    output.debug(f"Successfully moved file to: {new_path}")
                except Exception as e:
                    output.error(f"Failed to move file for {video_id}: {e}")
                    output.error(f"Source: {result.output_path}, Target: {new_path}")
                    # Rollback manifest changes since file move failed
                    try:
                        manifest_data['records'].pop()
                        manifest_data['total_duration_seconds'] -= record['duration_seconds']
                        file_manager.save_json(manifest_file, manifest_data)
                        output.debug(f"Rolled back manifest changes for {video_id}")
                    except Exception as rollback_e:
                        output.error(f"Failed to rollback manifest for {video_id}: {rollback_e}")
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
                
                processed_count += 1
                # Check if we've reached the maximum count
                if max_count is not None and processed_count >= max_count:
                    output.info(f"Reached maximum download count ({max_count}), stopping download phase")
                    break
            else:
                error_msg = result.error_message if result else "Unknown download error"
                output.warning(f"Download failed for {video_id}: {error_msg}")
                
                # Log detailed error information from all attempts
                if result and result.attempts:
                    for i, attempt in enumerate(result.attempts):
                        output.warning(f"  Attempt {i+1} ({attempt.method}): {'SUCCESS' if attempt.success else 'FAILED'}")
                        if not attempt.success and attempt.error_message:
                            # Log the full error details from the downloader
                            output.warning(f"    Error details: {attempt.error_message}")
                            # If it's a yt-dlp error, it might contain multiple lines - log them separately
                            if '\n' in attempt.error_message:
                                for line in attempt.error_message.split('\n'):
                                    if line.strip():
                                        output.warning(f"    {line.strip()}")
                        if attempt.completed and attempt.end_time:
                            duration = attempt.end_time - attempt.start_time
                            output.warning(f"    Duration: {duration:.2f}s")
                
                # Clean up temp file if it exists
                if result and result.output_path and result.output_path.exists():
                    try:
                        result.output_path.unlink()
                        output.debug(f"Cleaned up failed download temp file: {result.output_path}")
                    except Exception as e:
                        output.warning(f"Failed to clean up failed download temp file {result.output_path}: {e}")
                
                # Create failed manifest record to prevent re-attempts
                if existing_record:
                    # Update existing record to failed
                    existing_record.update({
                        "status": "failed",
                        "file_available": False,
                        "all_downloads_failed": True
                    })
                else:
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
                        "classified": False,
                        "file_available": False,
                        "all_downloads_failed": True
                    }
                    
                    # Update manifest with failed record
                    manifest_data['records'].append(failed_record)
                
                # Save manifest atomically
                file_manager = get_file_manager()
                file_manager.save_json(manifest_file, manifest_data)
                
                processed_count += 1
                # Check if we've reached the maximum count
                if max_count is not None and processed_count >= max_count:
                    output.info(f"Reached maximum download count ({max_count}), stopping download phase")
                    break

        output.success(f"Download phase completed: {downloaded_count}/{len(urls)} URLs processed")
        return downloaded_count

    except Exception as e:
        output.error(f"Download phase failed: {e}")
        output.error(f"Config output dirs: final_audio={config.output.final_audio_dir}, url_outputs={config.output.url_outputs_dir}")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")
        
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