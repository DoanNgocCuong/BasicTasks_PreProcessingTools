# analyzer/analysis_phases.py

"""
Analysis Phase Implementation

This module contains the implementation of the audio analysis phase.
"""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from ..config import CrawlerConfig
from ..models import VideoMetadata, VideoSource
from ..utils import get_output_manager, get_file_manager

# Optional imports for analyzers
try:
    from .voice_classifier import VoiceClassifier, get_voice_classifier
    VOICE_CLASSIFIER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Voice classifier not available: {e}")
    VoiceClassifier = None
    get_voice_classifier = None
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
    
    # Migrate legacy voice_analysis_confident field to voice_analysis_confidence
    if 'voice_analysis_confident' in record:
        # Use the new field if it exists, otherwise use the old one
        if 'voice_analysis_confidence' not in record or record['voice_analysis_confidence'] is None:
            record['voice_analysis_confidence'] = record['voice_analysis_confident']
        # Always remove legacy field after migration
        del record['voice_analysis_confident']
    
    return record


async def run_analysis_phase(config: CrawlerConfig, videos: List[VideoMetadata], video_ids: Optional[List[str]] = None) -> List[VideoMetadata]:
    """
    Run the audio analysis phase.

    Args:
        config: Crawler configuration
        videos: Videos to analyze
        video_ids: Optional list of specific video IDs to analyze. If None, analyzes all unanalyzed videos.

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

        # Run audio analysis locally
        output.info("Running audio analysis locally")
        try:
            return await run_local_analysis(config, manifest_data, manifest_file, video_ids)
        except Exception as e:
            output.error(f"Local analysis failed: {e}")
            import traceback
            output.error(f"Full traceback: {traceback.format_exc()}")
            return videos

    except Exception as e:
        output.error(f"Analysis phase failed: {e}")
        output.error(f"Config output dir: {config.output.final_audio_dir}")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")
        return videos


async def run_local_analysis(config: CrawlerConfig, manifest_data: dict, manifest_file: Path, video_ids: Optional[List[str]] = None) -> List[VideoMetadata]:
    """
    Run audio analysis locally based on manifest data.

    Args:
        config: Crawler configuration
        manifest_data: Manifest data
        manifest_file: Path to manifest file
        video_ids: Optional list of specific video IDs to analyze. If None, analyzes all unanalyzed videos.

    Returns:
        List of videos with analysis results (empty for compatibility)
    """
    output = get_output_manager()

    if VOICE_CLASSIFIER_AVAILABLE and VoiceClassifier is not None and get_voice_classifier is not None:
        try:
            # Use factory function to get cached singleton with preloading
            voice_classifier = get_voice_classifier(config.analysis)
            output.debug("Voice classifier initialized successfully using cached singleton")
        except Exception as e:
            output.error(f"Failed to initialize voice classifier: {e}")
            output.error(f"Analysis config: {config.analysis}")
            import traceback
            output.error(f"Full traceback: {traceback.format_exc()}")
            return []
    else:
        output.warning("Voice classifier not available - skipping analysis phase")
        return []

    analyzed_count = 0

    for record in manifest_data.get('records', []):
        video_id = record.get('video_id')
        
        # If video_ids is specified, only process those videos
        if video_ids is not None and video_id not in video_ids:
            continue
            
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

        output_path_str = record.get('output_path')

        # Skip records with missing required fields
        if not video_id or not output_path_str:
            output.warning(f"Skipping analysis for record with missing video_id or output_path: video_id={video_id}, output_path={output_path_str}")
            continue

        # Make path absolute relative to workspace root
        # Safety check: ensure manifest path has sufficient depth
        if len(manifest_file.parents) < 2:
            output.error(f"Cannot resolve workspace root for {video_id}: manifest path has insufficient depth")
            output.error(f"Manifest path parents: {list(manifest_file.parents)}")
            continue
        
        workspace_root = manifest_file.parents[2]  # manifest.json is at workspace/output/final_audio/manifest.json
        output_path = workspace_root / output_path_str

        if not output_path.exists():
            output.warning(f"Audio file not found for {video_id}: {output_path}")
            continue

        # Analyze for children's voice
        output.info(f"Analyzing audio file for {video_id}...")
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

        # Update record with classification results
        record['classified'] = True
        record['containing_children_voice'] = voice_result.is_child_voice
        record['voice_analysis_confidence'] = voice_result.confidence
        record['classification_timestamp'] = datetime.now().isoformat() + "Z"
        
        # Clean up any legacy fields
        if 'voice_analysis_confident' in record:
            del record['voice_analysis_confident']

        if voice_result.is_child_voice:
            output.info(f"✅ Children's voice detected in {video_id} (confidence: {voice_result.confidence:.2f})")
        else:
            output.info(f"⏭️ No children's voice in {video_id} (confidence: {voice_result.confidence:.2f})")

        analyzed_count += 1

        # Save manifest after every analysis for data safety
        try:
            file_manager = get_file_manager()
            success = file_manager.save_json(manifest_file, manifest_data)
            if success:
                output.debug(f"Manifest updated and saved after analysis #{analyzed_count} for {video_id}")
            else:
                output.error(f"Failed to save manifest after analyzing {video_id} (analysis #{analyzed_count})")
        except Exception as e:
            output.error(f"Exception while saving manifest after analyzing {video_id} (analysis #{analyzed_count}): {e}")
            import traceback
            output.error(f"Full traceback: {traceback.format_exc()}")

    # Final save of updated manifest
    try:
        file_manager = get_file_manager()
        success = file_manager.save_json(manifest_file, manifest_data)
        if success:
            output.success(f"✅ Local analysis completed: {analyzed_count} files analyzed and manifest saved successfully")
        else:
            output.error(f"❌ Local analysis completed but final manifest save failed for {manifest_file}")
            output.error(f"   {analyzed_count} files were analyzed but changes may not be persisted")
    except Exception as e:
        output.error(f"❌ Failed to save updated manifest after analysis: {e}")
        output.error(f"   Manifest file: {manifest_file}")
        output.error(f"   {analyzed_count} files were analyzed but changes may not be persisted")
        import traceback
        output.error(f"Full traceback: {traceback.format_exc()}")

    return []