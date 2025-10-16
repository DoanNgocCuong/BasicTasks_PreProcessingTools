# analyzer/analysis_phases.py

"""
Analysis Phase Implementation

This module contains the implementation of the audio analysis phase.
"""

import json
from pathlib import Path
from typing import List
from datetime import datetime

from ..config import CrawlerConfig
from ..models import VideoMetadata, VideoSource
from ..utils import get_output_manager, get_file_manager

# Optional imports for analyzers
try:
    from .voice_classifier import VoiceClassifier
    VOICE_CLASSIFIER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Voice classifier not available: {e}")
    VoiceClassifier = None
    VOICE_CLASSIFIER_AVAILABLE = False


def migrate_legacy_classification_fields(record: dict) -> dict:
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

        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            # Migrate legacy classification fields in all records
            for record in manifest_data.get('records', []):
                migrate_legacy_classification_fields(record)
            output.debug(f"Successfully loaded manifest with {len(manifest_data.get('records', []))} records")
        except json.JSONDecodeError as e:
            output.error(f"Failed to parse manifest JSON at {manifest_file}: {e}")
            output.error(f"Manifest file may be corrupted. Please check the file contents.")
            return videos
        except IOError as e:
            output.error(f"Failed to read manifest file at {manifest_file}: {e}")
            output.error(f"Check file permissions and disk space.")
            return videos
        except Exception as e:
            output.error(f"Unexpected error loading manifest at {manifest_file}: {e}")
            return videos

        # Check if we should run locally or use API
        run_locally = not config.analysis_api.enabled or config.analysis_api.server_url == "local"

        if run_locally:
            output.info("Running audio analysis locally")
            try:
                return await run_local_analysis(config, manifest_data, manifest_file)
            except Exception as e:
                output.error(f"Local analysis failed: {e}")
                import traceback
                output.error(f"Full traceback: {traceback.format_exc()}")
                return videos
        else:
            output.info("Running audio analysis via API")
            # API-based analysis
            try:
                from .api_client import AnalysisAPIClient
                api_client_available = True
            except ImportError as e:
                output.warning(f"Analysis API client not available: {e} - falling back to local analysis")
                api_client_available = False

            if not api_client_available:
                output.warning("Analysis API client not available - falling back to local analysis")
                try:
                    return await run_local_analysis(config, manifest_data, manifest_file)
                except Exception as e:
                    output.error(f"Fallback local analysis failed: {e}")
                    import traceback
                    output.error(f"Full traceback: {traceback.format_exc()}")
                    return videos

            try:
                from .api_client import AnalysisAPIClient
                async with AnalysisAPIClient(config.analysis_api) as client:
                    # Convert manifest records to VideoMetadata objects for API
                    api_videos = []
                    api_audio_paths = []
                    for record in manifest_data.get('records', []):
                        if not record.get('classified', False):
                            video_id = record.get('video_id')
                            output_path_str = record.get('output_path')
                            
                            # Skip records with missing required fields
                            if not video_id or not output_path_str:
                                output.warning(f"Skipping API analysis for record with missing video_id or output_path: video_id={video_id}, output_path={output_path_str}")
                                continue
                                
                            # Create minimal VideoMetadata for unclassified records
                            video = VideoMetadata(
                                video_id=video_id,
                                title=record.get('title', f"Video {video_id}"),
                                channel_id='',
                                channel_title='',
                                description='',
                                source=VideoSource.MANUAL
                            )
                            api_videos.append(video)
                            api_audio_paths.append(output_path_str)

                    if api_videos:
                        try:
                            results = await client.analyze_videos(api_videos)
                            output.debug(f"API analysis returned {len(results)} results")
                        except Exception as e:
                            output.error(f"API analysis request failed: {e}")
                            output.error(f"API server URL: {config.analysis_api.server_url}")
                            import traceback
                            output.error(f"Full traceback: {traceback.format_exc()}")
                            return videos

                        # Update manifest with API results
                        try:
                            for result in results:
                                for record in manifest_data.get('records', []):
                                    if record['video_id'] == result.video_id:
                                        record['classified'] = True
                                        record['containing_children_voice'] = result.is_child_voice
                                        record['voice_analysis_confidence'] = result.confidence
                                        record['classification_timestamp'] = datetime.now().isoformat() + "Z"
                                        break

                            # Save updated manifest
                            file_manager = get_file_manager()
                            file_manager.save_json(manifest_file, manifest_data)

                            output.success(f"API analysis completed: {len(results)} videos analyzed")
                        except Exception as e:
                            output.error(f"Failed to update manifest with API results: {e}")
                            output.error(f"Manifest file: {manifest_file}")
                            import traceback
                            output.error(f"Full traceback: {traceback.format_exc()}")
                            return videos
                    else:
                        output.info("No unclassified videos found for API analysis")

                return videos
            except Exception as e:
                output.error(f"API analysis setup failed: {e}")
                output.error(f"Analysis API config: {config.analysis_api}")
                import traceback
                output.error(f"Full traceback: {traceback.format_exc()}")
                return videos

    except Exception as e:
        output.error(f"Analysis phase failed: {e}")
        output.error(f"Config output dir: {config.output.final_audio_dir}")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")
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

    if VOICE_CLASSIFIER_AVAILABLE and VoiceClassifier is not None:
        try:
            voice_classifier = VoiceClassifier(config.analysis)
            output.debug("Voice classifier initialized successfully")
        except Exception as e:
            output.error(f"Failed to initialize voice classifier: {e}")
            output.error(f"Analysis config: {config.analysis}")
            import traceback
            output.error(f"Full traceback: {traceback.format_exc()}")
            return []
    else:
        output.warning("Voice classifier not available - skipping analysis phase")
        return []
    
    try:
        voice_loaded = voice_classifier.load_model()
        output.debug(f"Voice classifier model loaded: {voice_loaded}")
    except Exception as e:
        output.error(f"Failed to load voice classifier model: {e}")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")
        return []

    if not voice_loaded:
        output.warning("Voice classifier model not loaded - skipping voice analysis")
        return []

    analyzed_count = 0

    for record in manifest_data.get('records', []):
        classified = record.get('classified', False)
        classification_timestamp = record.get('classification_timestamp')
        containing_children_voice = record.get('containing_children_voice')
        
        # Skip if already fully classified (has all required classification fields)
        has_complete_classification = (
            classified and 
            classification_timestamp is not None and
            containing_children_voice is not None
        )
        if has_complete_classification:
            continue
        
        # Re-analyze if classified but missing key fields
        has_incomplete_classification = (
            classified and 
            (classification_timestamp is None or containing_children_voice is None)
        )
        if has_incomplete_classification:
            output.info(f"Re-analyzing {record.get('video_id')} due to incomplete classification data (timestamp: {classification_timestamp}, children_voice: {containing_children_voice})")

        video_id = record.get('video_id')
        output_path_str = record.get('output_path')

        # Skip records with missing required fields
        if not video_id or not output_path_str:
            output.warning(f"Skipping analysis for record with missing video_id or output_path: video_id={video_id}, output_path={output_path_str}")
            continue

        output_path = Path(output_path_str)

        if not output_path.exists():
            output.warning(f"Audio file not found for {video_id}: {output_path}")
            continue

        # Analyze for children's voice
        try:
            voice_result = voice_classifier.classify_audio_file(output_path)
            output.debug(f"Voice classification result for {video_id}: is_child={voice_result.is_child_voice}, confidence={voice_result.confidence}")
        except Exception as e:
            output.error(f"Failed to classify audio for {video_id}: {e}")
            output.error(f"Audio file path: {output_path}")
            output.error(f"File exists: {output_path.exists()}")
            if output_path.exists():
                output.error(f"File size: {output_path.stat().st_size} bytes")
            import traceback
            output.error(f"Full traceback: {traceback.format_exc()}")
            continue

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
    try:
        file_manager = get_file_manager()
        file_manager.save_json(manifest_file, manifest_data)
        output.success(f"Local analysis completed: {analyzed_count} files analyzed")
    except Exception as e:
        output.error(f"Failed to save updated manifest after analysis: {e}")
        output.error(f"Manifest file: {manifest_file}")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")

    return []