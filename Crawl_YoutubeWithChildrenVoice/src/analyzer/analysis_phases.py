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
            try:
                from .api_client import AnalysisAPIClient
                api_client_available = True
            except ImportError:
                api_client_available = False

            if not api_client_available:
                output.warning("Analysis API client not available - falling back to local analysis")
                return await run_local_analysis(config, manifest_data, manifest_file)

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
                    file_manager = get_file_manager()
                    file_manager.save_json(manifest_file, manifest_data)

                    output.success(f"API analysis completed: {len(results)} videos analyzed")
                else:
                    output.info("No unclassified videos found for API analysis")

                return videos

    except Exception as e:
        output.error(f"Analysis phase failed: {e}")
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
        voice_classifier = VoiceClassifier(config.analysis)
    else:
        output.warning("Voice classifier not available - skipping analysis phase")
        return []
    voice_loaded = voice_classifier.load_model()

    if not voice_loaded:
        output.warning("Voice classifier model not loaded - skipping voice analysis")
        return []

    analyzed_count = 0

    for record in manifest_data.get('records', []):
        if record.get('classified', False):
            # Already classified, skip
            continue

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
    file_manager = get_file_manager()
    file_manager.save_json(manifest_file, manifest_data)

    output.success(f"Local analysis completed: {analyzed_count} files analyzed")
    return []