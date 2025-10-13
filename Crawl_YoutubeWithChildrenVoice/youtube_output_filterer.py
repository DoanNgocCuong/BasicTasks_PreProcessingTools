#!/usr/bin/env python3
"""
YouTube Output Filterer

This module filters downloaded audio files based on children's voice detection,
managing the manifest accordingly and supporting concurrent execution.

Features:
    - Processes audio files using paths from manifest.json
    - Uses chunked audio analysis (like the crawler) for efficiency
    - Analyzes only the first 3 chunks with early exit on positive detection
    - Uses chunk duration from MAX_AUDIO_DURATION_SECONDS in .env config
    - Uses AudioClassifier for children's voice detection
    - Removes files without children's voices and updates manifest
    - Marks processed files to avoid reprocessing
    - Supports concurrent execution with thread safety
    - Handles missing files and error cases gracefully

Author: Generated for YouTube Audio Crawler
Version: 2.0 - Added chunked processing
"""

import json
import logging
import os
import threading
import time
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import shutil

# Audio processing imports
try:
    import librosa
    import soundfile as sf
    AUDIO_LIBS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Audio processing libraries not available: {e}")
    print("Running in test mode without audio processing")
    AUDIO_LIBS_AVAILABLE = False
    # Mock librosa and soundfile
    class MockLibrosa:
        @staticmethod
        def load(path, sr=None):
            return [0] * 1000, sr or 16000
    
    class MockSoundfile:
        @staticmethod
        def write(path, data, sr):
            pass
    
    librosa = MockLibrosa()
    sf = MockSoundfile()

# Import the existing AudioClassifier and env config
AudioClassifier = None
try:
    from youtube_audio_classifier import AudioClassifier
except (ImportError, OSError) as e:
    print(f"Warning: Could not import AudioClassifier: {e}")
    print("Using mock AudioClassifier for testing")
    try:
        from youtube_audio_classifier_mock import AudioClassifier
    except ImportError:
        # Create a simple inline mock if the mock file isn't available
        class AudioClassifier:
            def __init__(self):
                pass
            def is_child_audio(self, path):
                return False
from env_config import config

# Import QueueManager for inter-instance coordination
try:
    from queue_manager import QueueManager, create_queue_manager
    QUEUE_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import QueueManager: {e}")
    print("Running without queue coordination (single instance mode)")
    QUEUE_MANAGER_AVAILABLE = False
    QueueManager = None
    create_queue_manager = None


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a single audio file record."""
    record_id: str
    has_children_voice: bool
    action_taken: str  # "kept", "deleted", "error", "skipped", "file_not_found"
    error_message: Optional[str]
    processing_time: float
    chunks_analyzed: Optional[int] = None
    positive_chunk_index: Optional[int] = None
    was_chunked: bool = False


@dataclass
class FilterResult:
    """Overall result of the filtering operation."""
    total_processed: int
    files_kept: int
    files_deleted: int
    files_not_found: int
    errors: int
    processing_time: float
    error_details: List[str]


class YouTubeOutputFilterer:
    """Main filterer class for processing downloaded audio files."""
    
    def __init__(self, manifest_path: str, audio_classifier: Optional[AudioClassifier] = None, instance_id: Optional[str] = None, use_queue: bool = False):
        """
        Initialize the filterer.
        
        Args:
            manifest_path: Path to the manifest.json file
            audio_classifier: Optional AudioClassifier instance (creates new if None)
            instance_id: Optional unique identifier for this instance (generated if None)
            use_queue: Whether to use queue-based coordination (default: False, due to file locking issues)
        """
        self.manifest_path = Path(manifest_path)
        self.audio_classifier = audio_classifier or AudioClassifier()
        self.use_queue = use_queue and QUEUE_MANAGER_AVAILABLE
        self._lock = threading.Lock()  # For thread-safe manifest updates
        
        # Initialize queue manager if enabled
        if self.use_queue and create_queue_manager is not None:
            try:
                self.queue_manager = create_queue_manager(str(self.manifest_path), instance_id)
                self.instance_id = self.queue_manager.instance_id
                logger.info(f"Initialized with queue coordination (instance: {self.instance_id})")
            except Exception as e:
                logger.warning(f"Failed to initialize queue manager: {e}")
                logger.warning("Falling back to single-instance mode")
                self.queue_manager = None
                self.use_queue = False
                self.instance_id = instance_id or f"filterer_{os.getpid()}_{datetime.now().strftime('%H%M%S')}"
        else:
            self.instance_id = instance_id or f"filterer_{os.getpid()}_{datetime.now().strftime('%H%M%S')}"
            self.queue_manager = None
            self.use_queue = False
            logger.info(f"Initialized without queue coordination (instance: {self.instance_id})")
        
        # Validate manifest file exists
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {self.manifest_path}")
        
        logger.info(f"YouTubeOutputFilterer initialized with manifest: {self.manifest_path}")
    
    def _split_audio_into_chunks(self, audio_file_path: str, chunk_duration_seconds: int) -> List[str]:
        """
        Split audio file into chunks of specified duration.
        
        Args:
            audio_file_path (str): Path to the audio file to split
            chunk_duration_seconds (int): Duration of each chunk in seconds
            
        Returns:
            List[str]: List of paths to chunk files
        """
        chunk_files = []
        temp_dir = None
        
        try:
            # Create temporary directory for chunks
            temp_dir = tempfile.mkdtemp(prefix="filterer_audio_chunks_")
            
            # Load audio file
            logger.info(f"📄 Loading audio file for chunking: {audio_file_path}")
            audio, sr = librosa.load(audio_file_path, sr=16000)  # Standard 16kHz for analysis
            total_duration = len(audio) / sr
            
            logger.info(f"📏 Audio duration: {total_duration:.1f}s, chunk size: {chunk_duration_seconds}s")
            
            # Calculate number of chunks
            num_chunks = int(total_duration / chunk_duration_seconds) + (1 if total_duration % chunk_duration_seconds > 0 else 0)
            logger.info(f"📊 Will create {num_chunks} chunks")
            
            # Create chunks
            for i in range(num_chunks):
                start_time = i * chunk_duration_seconds
                end_time = min((i + 1) * chunk_duration_seconds, total_duration)
                
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                
                chunk_audio = audio[start_sample:end_sample]
                
                # Skip very short chunks (less than 1 second)
                if len(chunk_audio) < sr:
                    logger.info(f"⏭️  Skipping chunk {i+1} (too short: {len(chunk_audio)/sr:.1f}s)")
                    continue
                
                # Save chunk
                chunk_path = os.path.join(temp_dir, f"chunk_{i+1:03d}.wav")
                sf.write(chunk_path, chunk_audio, sr)
                chunk_files.append(chunk_path)
                
                chunk_duration = len(chunk_audio) / sr
                logger.info(f"📋 Created chunk {i+1}: {start_time:.1f}s-{end_time:.1f}s ({chunk_duration:.1f}s) -> {chunk_path}")
            
            logger.info(f"✅ Successfully created {len(chunk_files)} audio chunks")
            return chunk_files
            
        except Exception as e:
            logger.error(f"❌ Error splitting audio into chunks: {e}")
            # Cleanup on error
            if chunk_files:
                for chunk_file in chunk_files:
                    try:
                        if os.path.exists(chunk_file):
                            os.remove(chunk_file)
                    except Exception:
                        pass
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception:
                    pass
            return []
    
    def _cleanup_chunk_files(self, chunk_files: List[str]) -> None:
        """
        Clean up temporary chunk files and their directory.
        
        Args:
            chunk_files (List[str]): List of chunk file paths to clean up
        """
        if not chunk_files:
            return
            
        try:
            # Get the directory containing the chunks
            chunk_dir = os.path.dirname(chunk_files[0])
            
            # Remove all chunk files
            for chunk_file in chunk_files:
                try:
                    if os.path.exists(chunk_file):
                        os.remove(chunk_file)
                        logger.debug(f"Cleaned up chunk file: {chunk_file}")
                except Exception as e:
                    logger.debug(f"Could not clean up chunk file {chunk_file}: {e}")
            
            # Remove the temporary directory if empty
            try:
                if os.path.exists(chunk_dir) and not os.listdir(chunk_dir):
                    os.rmdir(chunk_dir)
                    logger.debug(f"Cleaned up chunk directory: {chunk_dir}")
            except Exception as e:
                logger.debug(f"Could not clean up chunk directory {chunk_dir}: {e}")
                
        except Exception as e:
            logger.debug(f"Error during chunk cleanup: {e}")
    
    def _analyze_audio_chunks(self, audio_file_path: str) -> tuple[bool, int, Optional[int]]:
        """
        Analyze audio by splitting it into chunks and processing up to the first 3 chunks with early exit.
        
        Args:
            audio_file_path (str): Path to the audio file to analyze
            
        Returns:
            tuple[bool, int, Optional[int]]: (has_children_voice, chunks_analyzed, positive_chunk_index)
        """
        chunk_files = []
        
        try:
            # Get chunk duration from config (same as crawler)
            chunk_duration = config.MAX_AUDIO_DURATION_SECONDS
            if chunk_duration is None:
                # Fallback to default chunk size if no limit configured
                chunk_duration = 300  # 5 minutes
            
            # Get audio duration first
            try:
                audio, sr = librosa.load(audio_file_path, sr=16000)
                audio_duration = len(audio) / sr
            except Exception as e:
                logger.error(f"Failed to get audio duration: {e}")
                return False, 0, None
            
            logger.info(f"🧩 Starting chunk analysis for {audio_duration:.1f}s audio")
            logger.info(f"📏 Chunk size: {chunk_duration}s ({chunk_duration//60}m {chunk_duration%60}s)")
            logger.info(f"🎯 Will analyze up to the first 3 chunks with early exit on success")
            
            # Split audio into chunks
            chunk_files = self._split_audio_into_chunks(audio_file_path, chunk_duration)
            
            if not chunk_files:
                logger.error("❌ Failed to create audio chunks")
                return False, 0, None
            
            total_chunks = len(chunk_files)
            # Limit to first 3 chunks
            chunks_to_analyze = min(3, total_chunks)
            logger.info(f"📊 Created {total_chunks} chunks, will analyze first {chunks_to_analyze}")
            
            # Analyze chunks sequentially with early exit
            for chunk_index in range(chunks_to_analyze):
                chunk_file = chunk_files[chunk_index]
                logger.info(f"🔍 Analyzing chunk {chunk_index + 1}/{chunks_to_analyze} for children's voice...")
                
                try:
                    # Perform children's voice detection
                    children_voice_result = self.audio_classifier.is_child_audio(chunk_file)
                    
                    # Check for critical errors in children's voice detection
                    if children_voice_result is None:
                        logger.error(f"❌ Chunk {chunk_index + 1} children's voice detection failed")
                        continue  # Try next chunk
                    
                    logger.info(f"📋 Chunk {chunk_index + 1} children's voice detection: {children_voice_result}")
                    
                    if children_voice_result:
                        remaining_chunks = chunks_to_analyze - (chunk_index + 1)
                        logger.info(f"🎯 SUCCESS! Chunk {chunk_index + 1} contains children's voice")
                        logger.info(f"⚡ Early exit: Found positive match in {chunk_index + 1}/{chunks_to_analyze} chunks")
                        if remaining_chunks > 0:
                            logger.info(f"⏭️  Skipping {remaining_chunks} remaining chunks")
                        
                        # Clean up chunk files
                        self._cleanup_chunk_files(chunk_files)
                        
                        # Return positive result
                        return True, chunk_index + 1, chunk_index + 1
                    else:
                        # This chunk doesn't contain children's voice
                        logger.info(f"❌ Chunk {chunk_index + 1}: no children's voice detected")
                        
                except Exception as e:
                    logger.error(f"❌ Error analyzing chunk {chunk_index + 1}: {e}")
                    continue  # Try next chunk
            
            logger.info(f"📊 CHUNK ANALYSIS SUMMARY:")
            logger.info(f"   └─ Analyzed {chunks_to_analyze}/{total_chunks} chunks")
            logger.info(f"   └─ Result: No children's voice detected in any analyzed chunk")
            
            # Clean up chunk files
            self._cleanup_chunk_files(chunk_files)
            
            return False, chunks_to_analyze, None
            
        except Exception as e:
            logger.error(f"❌ Error in chunk analysis: {e}")
            
            # Clean up chunk files on error
            if chunk_files:
                self._cleanup_chunk_files(chunk_files)
            
            return False, 0, None
    
    def filter_audio_files(self) -> FilterResult:
        """
        Main method to filter audio files based on children's voice detection.
        
        Returns:
            FilterResult containing processing statistics
        """
        start_time = time.time()
        logger.info("Starting audio file filtering...")
        
        # Initialize counters
        total_processed = 0
        files_kept = 0
        files_deleted = 0
        files_not_found = 0
        errors = 0
        error_details = []
        
        try:
            if self.use_queue and self.queue_manager:
                # Queue-based processing
                return self._filter_with_queue()
            else:
                # Legacy single-instance processing
                return self._filter_legacy()
        
        except Exception as e:
            logger.error(f"Fatal error during filtering: {e}")
            error_details.append(f"Fatal error: {str(e)}")
            errors += 1
        
        processing_time = time.time() - start_time
        
        # Create final result
        result = FilterResult(
            total_processed=total_processed,
            files_kept=files_kept,
            files_deleted=files_deleted,
            files_not_found=files_not_found,
            errors=errors,
            processing_time=processing_time,
            error_details=error_details
        )
        
        # Log summary
        self._log_summary(result)
        
        return result
    
    def _filter_with_queue(self) -> FilterResult:
        """
        Filter audio files using queue-based coordination.
        
        Returns:
            FilterResult containing processing statistics
        """
        if not self.queue_manager:
            raise RuntimeError("Queue manager not available for queue-based filtering")
            
        start_time = time.time()
        logger.info("Starting queue-based audio file filtering...")
        
        # Initialize counters
        total_processed = 0
        files_kept = 0
        files_deleted = 0
        files_not_found = 0
        errors = 0
        error_details = []
        
        try:
            # Populate queue from manifest if needed
            added_count = self.queue_manager.populate_queue_from_manifest()
            if added_count > 0:
                logger.info(f"Added {added_count} records to processing queue")
            
            # Process records in batches
            batch_size = 5  # Process 5 records at a time
            heartbeat_interval = 30  # Send heartbeat every 30 seconds
            last_heartbeat = time.time()
            
            while True:
                # Send heartbeat if needed
                current_time = time.time()
                if current_time - last_heartbeat >= heartbeat_interval:
                    self.queue_manager.heartbeat()
                    last_heartbeat = current_time
                
                # Claim a batch of records
                claim_result = self.queue_manager.claim_records(batch_size)
                batch_records = claim_result.claimed_records
                
                if not batch_records:
                    # No more records to process
                    logger.info("No more records to process in queue")
                    break
                
                logger.info(f"Processing batch of {len(batch_records)} records")
                
                # Process each record in the batch
                for record in batch_records:
                    video_id = record.get('video_id', 'unknown')
                    logger.info(f"Processing record: {video_id}")
                    
                    try:
                        result = self.process_single_record(record)
                        
                        # Update counters based on result
                        if result.action_taken == "kept":
                            files_kept += 1
                            self.queue_manager.complete_record(video_id)
                        elif result.action_taken == "deleted":
                            files_deleted += 1
                            self.queue_manager.complete_record(video_id)
                        elif result.action_taken == "file_not_found":
                            files_not_found += 1
                            self.queue_manager.complete_record(video_id)  # Still mark as complete
                        elif result.action_taken == "error":
                            errors += 1
                            if result.error_message:
                                error_details.append(result.error_message)
                            self.queue_manager.fail_record(video_id)  # Re-queue for retry
                        
                        total_processed += 1
                        
                        # Log result
                        if result.action_taken == "file_not_found":
                            logger.warning(f"File does not exist: {record.get('output_path', 'unknown')}")
                        elif result.action_taken == "error":
                            logger.error(f"Error processing {video_id}: {result.error_message}")
                        else:
                            chunk_info = ""
                            if result.was_chunked and result.chunks_analyzed is not None:
                                if result.positive_chunk_index is not None:
                                    chunk_info = f" (found in chunk {result.positive_chunk_index}/{result.chunks_analyzed})"
                                else:
                                    chunk_info = f" (analyzed {result.chunks_analyzed} chunks)"
                            logger.info(f"Record {video_id} -> {result.action_taken}{chunk_info}")
                    
                    except Exception as e:
                        logger.error(f"Unexpected error processing {video_id}: {e}")
                        errors += 1
                        error_details.append(f"Record {video_id}: {str(e)}")
                        self.queue_manager.fail_record(video_id)
                        total_processed += 1
                
                # Check queue status
                status = claim_result.queue_status
                logger.info(f"Queue status: {status.total_pending} pending, {status.total_processing} processing, {status.active_instances} active instances")
                
                # Small delay between batches to prevent tight looping
                time.sleep(0.1)
            
            # Final heartbeat
            self.queue_manager.heartbeat()
            
        except Exception as e:
            logger.error(f"Fatal error during queue-based filtering: {e}")
            error_details.append(f"Fatal error: {str(e)}")
            errors += 1
        
        processing_time = time.time() - start_time
        
        # Create final result
        result = FilterResult(
            total_processed=total_processed,
            files_kept=files_kept,
            files_deleted=files_deleted,
            files_not_found=files_not_found,
            errors=errors,
            processing_time=processing_time,
            error_details=error_details
        )
        
        return result
    
    def _filter_legacy(self) -> FilterResult:
        """
        Filter audio files using legacy single-instance processing.
        
        Returns:
            FilterResult containing processing statistics
        """
        start_time = time.time()
        logger.info("Starting legacy single-instance audio file filtering...")
        
        # Initialize counters
        total_processed = 0
        files_kept = 0
        files_deleted = 0
        files_not_found = 0
        errors = 0
        error_details = []
        
        try:
            # Get unclassified records
            unclassified_records = self.get_unclassified_records()
            total_processed = len(unclassified_records)
            
            if total_processed == 0:
                logger.info("No unclassified records found. Nothing to process.")
                return FilterResult(
                    total_processed=0,
                    files_kept=0,
                    files_deleted=0,
                    files_not_found=0,
                    errors=0,
                    processing_time=time.time() - start_time,
                    error_details=[]
                )
            
            logger.info(f"Found {total_processed} unclassified records to process")
            
            # Process each record
            for i, record in enumerate(unclassified_records, 1):
                logger.info(f"Processing record {i}/{total_processed}: {record.get('video_id', 'unknown')}")
                
                result = self.process_single_record(record)
                
                # Update counters based on result
                if result.action_taken == "kept":
                    files_kept += 1
                elif result.action_taken == "deleted":
                    files_deleted += 1
                elif result.action_taken == "file_not_found":
                    files_not_found += 1
                elif result.action_taken == "error":
                    errors += 1
                    if result.error_message:
                        error_details.append(result.error_message)
                
                # Log result
                if result.action_taken == "file_not_found":
                    logger.warning(f"File does not exist: {record.get('output_path', 'unknown')}")
                elif result.action_taken == "error":
                    logger.error(f"Error processing {record.get('video_id', 'unknown')}: {result.error_message}")
                else:
                    chunk_info = ""
                    if result.was_chunked and result.chunks_analyzed is not None:
                        if result.positive_chunk_index is not None:
                            chunk_info = f" (found in chunk {result.positive_chunk_index}/{result.chunks_analyzed})"
                        else:
                            chunk_info = f" (analyzed {result.chunks_analyzed} chunks)"
                    logger.info(f"Record {record.get('video_id', 'unknown')} -> {result.action_taken}{chunk_info}")
        
        except Exception as e:
            logger.error(f"Fatal error during legacy filtering: {e}")
            error_details.append(f"Fatal error: {str(e)}")
            errors += 1
        
        processing_time = time.time() - start_time
        
        # Create final result
        result = FilterResult(
            total_processed=total_processed,
            files_kept=files_kept,
            files_deleted=files_deleted,
            files_not_found=files_not_found,
            errors=errors,
            processing_time=processing_time,
            error_details=error_details
        )
        
        return result
    
    def get_unclassified_records(self) -> List[Dict]:
        """
        Get records that haven't been classified yet.
        
        Returns:
            List of unclassified record dictionaries
        """
        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            records = manifest_data.get('records', [])
            unclassified = []
            
            for record in records:
                # Check if record needs classification
                classified = record.get('classified', False)
                if not classified:
                    unclassified.append(record)
            
            logger.info(f"Found {len(unclassified)} unclassified records out of {len(records)} total")
            return unclassified
        
        except Exception as e:
            logger.error(f"Error reading manifest: {e}")
            raise
    
    def process_single_record(self, record: Dict) -> ProcessingResult:
        """
        Process a single audio file record.
        
        Args:
            record: Dictionary containing record information
            
        Returns:
            ProcessingResult with processing outcome
        """
        start_time = time.time()
        video_id = record.get('video_id', 'unknown')
        output_path = record.get('output_path', '')
        
        try:
            # Check if file exists
            if not output_path or not os.path.exists(output_path):
                # Mark as classified=false for missing files
                self._update_record_classification(record, classified=False, has_children_voice=False)
                return ProcessingResult(
                    record_id=video_id,
                    has_children_voice=False,
                    action_taken="file_not_found",
                    error_message=f"File does not exist: {output_path}",
                    processing_time=time.time() - start_time,
                    chunks_analyzed=0,
                    positive_chunk_index=None,
                    was_chunked=False
                )
            
            # Re-check if record was classified by another instance
            current_record = self._get_current_record(record)
            if current_record and current_record.get('classified', False):
                return ProcessingResult(
                    record_id=video_id,
                    has_children_voice=current_record.get('has_children_voice', False),
                    action_taken="skipped",
                    error_message="Already classified by another instance",
                    processing_time=time.time() - start_time,
                    chunks_analyzed=0,
                    positive_chunk_index=None,
                    was_chunked=False
                )
            
            # Classify audio using chunked analysis (similar to crawler)
            logger.info(f"Classifying audio: {output_path}")
            has_children_voice, chunks_analyzed, positive_chunk_index = self._analyze_audio_chunks(output_path)
            
            if chunks_analyzed == 0:
                # Classification error - mark as classified but keep file
                self._update_record_classification(record, classified=True, has_children_voice=False)
                return ProcessingResult(
                    record_id=video_id,
                    has_children_voice=False,
                    action_taken="error",
                    error_message="Audio classification failed",
                    processing_time=time.time() - start_time,
                    chunks_analyzed=0,
                    positive_chunk_index=None,
                    was_chunked=True
                )
            
            if has_children_voice:
                # Move file to language folder and mark as classified
                new_path = self._move_to_language_folder(record)
                
                self._update_record_classification(record, classified=True, has_children_voice=True, new_path=new_path)
                return ProcessingResult(
                    record_id=video_id,
                    has_children_voice=True,
                    action_taken="kept",
                    error_message=None,
                    processing_time=time.time() - start_time,
                    chunks_analyzed=chunks_analyzed,
                    positive_chunk_index=positive_chunk_index,
                    was_chunked=True
                )
            else:
                # Delete file and remove from manifest
                self._delete_file_and_update_manifest(record)
                return ProcessingResult(
                    record_id=video_id,
                    has_children_voice=False,
                    action_taken="deleted",
                    error_message=None,
                    processing_time=time.time() - start_time,
                    chunks_analyzed=chunks_analyzed,
                    positive_chunk_index=None,
                    was_chunked=True
                )
        
        except Exception as e:
            logger.error(f"Error processing record {video_id}: {e}")
            # On error, mark as classified and keep file
            try:
                self._update_record_classification(record, classified=True, has_children_voice=False)
            except:
                pass  # Don't fail on manifest update error
            
            return ProcessingResult(
                record_id=video_id,
                has_children_voice=False,
                action_taken="error",
                error_message=str(e),
                processing_time=time.time() - start_time,
                chunks_analyzed=0,
                positive_chunk_index=None,
                was_chunked=False
            )
    
    def _get_current_record(self, target_record: Dict) -> Optional[Dict]:
        """
        Get current state of a record from manifest (for concurrent safety).
        
        Args:
            target_record: Record to find
            
        Returns:
            Current record state or None if not found
        """
        try:
            with self._lock:
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                
                records = manifest_data.get('records', [])
                target_video_id = target_record.get('video_id')
                
                for record in records:
                    if record.get('video_id') == target_video_id:
                        return record
                
                return None
        except Exception as e:
            logger.error(f"Error getting current record state: {e}")
            return None
    
    def _move_to_language_folder(self, record: Dict) -> Optional[str]:
        """
        Move audio file from unclassified folder to its corresponding language folder.
        
        Args:
            record: Record containing language_folder and output_path information
            
        Returns:
            New file path if successful, None if failed
        """
        current_path = record.get('output_path', '')
        language_folder = record.get('language_folder', 'unknown')
        
        if not current_path or not os.path.exists(current_path):
            logger.warning(f"Cannot move file - source file does not exist: {current_path}")
            return None
        
        try:
            # Get the base directory (should be final_audio_files)
            current_file_path = Path(current_path)
            base_dir = current_file_path.parent.parent  # Go up from unclassified to final_audio_files
            
            # Determine target directory based on language_folder
            target_dir = base_dir / language_folder
            target_dir.mkdir(exist_ok=True)
            
            # Create target file path
            target_path = target_dir / current_file_path.name
            
            # Check if file is already in the correct location
            if current_path == str(target_path):
                logger.debug(f"File already in correct language folder: {language_folder}")
                return current_path
            
            # Move the file
            shutil.move(current_path, target_path)
            logger.info(f"Moved file to language folder ({language_folder}): {current_file_path.name}")
            logger.info(f"  From: {current_path}")
            logger.info(f"  To: {target_path}")
            
            return str(target_path)
            
        except Exception as e:
            logger.error(f"Error moving file to language folder: {e}")
            logger.error(f"  Source: {current_path}")
            logger.error(f"  Target language: {language_folder}")
            return None
    
    def _update_record_classification(self, record: Dict, classified: bool, has_children_voice: bool, new_path: Optional[str] = None) -> None:
        """
        Update a single record's classification status in the manifest.
        
        Args:
            record: Record to update
            classified: Whether record has been classified
            has_children_voice: Whether children's voice was detected
            new_path: Optional new file path if file was moved
        """
        video_id = record.get('video_id')
        updates = [{
            'video_id': video_id,
            'classified': classified,
            'has_children_voice': has_children_voice,
            'classification_timestamp': datetime.now().isoformat()
        }]
        
        # Include path update if provided
        if new_path:
            updates[0]['output_path'] = new_path
            
        self.update_manifest_safely(updates)
    
    def _delete_file_and_update_manifest(self, record: Dict) -> None:
        """
        Delete audio file and remove record from manifest.
        
        Args:
            record: Record to delete
        """
        output_path = record.get('output_path', '')
        video_id = record.get('video_id')
        
        # Delete the file
        try:
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
                logger.info(f"Deleted file: {output_path}")
        except Exception as e:
            logger.error(f"Error deleting file {output_path}: {e}")
            # Continue with manifest update even if file deletion fails
        
        # Remove from manifest
        updates = [{
            'video_id': video_id,
            'action': 'remove'
        }]
        self.update_manifest_safely(updates)
    
    def update_manifest_safely(self, updates: List[Dict]) -> None:
        """
        Safely update manifest with concurrent access protection.
        
        Args:
            updates: List of update dictionaries
        """
        max_retries = 3
        retry_delay = 0.1  # 100ms
        
        for attempt in range(max_retries):
            try:
                with self._lock:
                    # Create backup first
                    backup_path = self.backup_manifest()
                    
                    # Load current manifest
                    with open(self.manifest_path, 'r', encoding='utf-8') as f:
                        manifest_data = json.load(f)
                    
                    records = manifest_data.get('records', [])
                    
                    # Apply updates
                    for update in updates:
                        video_id = update.get('video_id')
                        action = update.get('action', 'update')
                        
                        if action == 'remove':
                            # Remove record
                            records = [r for r in records if r.get('video_id') != video_id]
                        else:
                            # Update record
                            for i, record in enumerate(records):
                                if record.get('video_id') == video_id:
                                    # Update fields
                                    if 'classified' in update:
                                        record['classified'] = update['classified']
                                    if 'has_children_voice' in update:
                                        record['has_children_voice'] = update['has_children_voice']
                                    if 'classification_timestamp' in update:
                                        record['classification_timestamp'] = update['classification_timestamp']
                                    if 'output_path' in update:
                                        record['output_path'] = update['output_path']
                                    break
                    
                    # Update records in manifest
                    manifest_data['records'] = records
                    
                    # Recalculate total duration if records were removed
                    if any(u.get('action') == 'remove' for u in updates):
                        total_duration = sum(r.get('duration_seconds', 0) for r in records)
                        manifest_data['total_duration_seconds'] = total_duration
                    
                    # Write updated manifest
                    with open(self.manifest_path, 'w', encoding='utf-8') as f:
                        json.dump(manifest_data, f, indent=2, ensure_ascii=False)
                    
                    logger.debug(f"Manifest updated successfully (backup: {backup_path})")
                    return
            
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} to update manifest failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"Failed to update manifest after {max_retries} attempts")
                    raise
    
    def backup_manifest(self) -> str:
        """
        Create a backup of the manifest file.
        
        Returns:
            Path to the backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.manifest_path.parent / f"manifest.backup_filterer_{timestamp}.json"
        
        try:
            shutil.copy2(self.manifest_path, backup_path)
            logger.debug(f"Manifest backup created: {backup_path}")
            return str(backup_path)
        except Exception as e:
            logger.error(f"Error creating manifest backup: {e}")
            raise
    
    def _log_summary(self, result: FilterResult) -> None:
        """
        Log processing summary.
        
        Args:
            result: FilterResult to summarize
        """
        logger.info("=" * 60)
        logger.info("YOUTUBE OUTPUT FILTERER - PROCESSING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total processed: {result.total_processed}")
        logger.info(f"Files kept (children's voice): {result.files_kept}")
        logger.info(f"  └─ Moved to language folders based on detection")
        logger.info(f"Files deleted (no children's voice): {result.files_deleted}")
        logger.info(f"Files not found: {result.files_not_found}")
        logger.info(f"Errors: {result.errors}")
        logger.info(f"Processing time: {result.processing_time:.2f} seconds")
        
        if result.total_processed > 0:
            success_rate = ((result.files_kept + result.files_deleted) / result.total_processed) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")
            
            if result.files_kept + result.files_deleted > 0:
                children_ratio = (result.files_kept / (result.files_kept + result.files_deleted)) * 100
                logger.info(f"Children's voice detection ratio: {children_ratio:.1f}%")
        
        if result.error_details:
            logger.info("Error details:")
            for error in result.error_details:
                logger.info(f"  - {error}")
        
        logger.info("=" * 60)
    
    @staticmethod
    def run_filterer(manifest_path: Optional[str] = None, instance_id: Optional[str] = None, use_queue: bool = False) -> FilterResult:
        """
        Single entry point for API usage.
        
        Args:
            manifest_path: Path to manifest.json (defaults to standard location)
            instance_id: Optional unique identifier for this instance
            use_queue: Whether to use queue-based coordination (default: True)
            
        Returns:
            FilterResult containing processing statistics
        """
        if manifest_path is None:
            # Use default path relative to this script
            script_dir = Path(__file__).parent
            manifest_path = str(script_dir / "final_audio_files" / "manifest.json")
        
        filterer = None
        try:
            filterer = YouTubeOutputFilterer(str(manifest_path), instance_id=instance_id, use_queue=use_queue)
            return filterer.filter_audio_files()
        except Exception as e:
            logger.error(f"Error running filterer: {e}")
            return FilterResult(
                total_processed=0,
                files_kept=0,
                files_deleted=0,
                files_not_found=0,
                errors=1,
                processing_time=0.0,
                error_details=[str(e)]
            )
        finally:
            # Clean up queue manager if it exists
            if filterer and filterer.queue_manager:
                try:
                    filterer.queue_manager.unregister_instance()
                    logger.info(f"Unregistered instance: {filterer.queue_manager.instance_id}")
                except Exception as e:
                    logger.warning(f"Error unregistering instance: {e}")


def main():
    """Main function for direct script execution."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="YouTube Output Filterer - Filter audio files based on children's voice detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python youtube_output_filterer.py  # Single-instance mode (recommended for most users)
  python youtube_output_filterer.py --manifest /path/to/manifest.json
  python youtube_output_filterer.py --dry-run
  python youtube_output_filterer.py --no-queue  # Explicitly disable queue (default behavior now)  
  python youtube_output_filterer.py --instance-id my-instance-01  # Custom instance ID (only needed for queue mode)
        """
    )
    
    parser.add_argument(
        "--manifest", 
        default=None,
        help="Path to manifest.json file (default: ./final_audio_files/manifest.json)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without making changes"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--no-queue",
        action="store_true",
        help="Disable queue-based coordination (recommended if experiencing file lock permission issues)"
    )
    
    parser.add_argument(
        "--instance-id",
        default=None,
        help="Unique identifier for this filterer instance (auto-generated if not provided)"
    )
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    print("YouTube Output Filterer")
    print("=" * 50)
    print("Filters audio files based on children's voice detection")
    print("=" * 50)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print("-" * 50)
        
        # Just show what would be processed
        try:
            manifest_path = args.manifest
            if manifest_path is None:
                script_dir = Path(__file__).parent
                manifest_path = str(script_dir / "final_audio_files" / "manifest.json")
            
            # Default to single-instance mode for dry-run (safer)
            use_queue = False  # Always use single-instance for dry-run to avoid permission issues
            filterer = YouTubeOutputFilterer(manifest_path, instance_id=args.instance_id, use_queue=use_queue)
            
            # Always use legacy dry run (single-instance mode)
            unclassified = filterer.get_unclassified_records()
            print(f"Would process {len(unclassified)} unclassified records:")
            for i, record in enumerate(unclassified[:10], 1):  # Show first 10
                video_id = record.get('video_id', 'unknown')
                output_path = record.get('output_path', '')
                file_exists = os.path.exists(output_path) if output_path else False
                status = "FILE EXISTS" if file_exists else "FILE MISSING"
                print(f"  {i}. {video_id} - {status}")
            
            if len(unclassified) > 10:
                print(f"  ... and {len(unclassified) - 10} more records")
            
            if len(unclassified) == 0:
                print("  No unclassified records found - nothing to process!")
            
            print("\nUse without --dry-run to perform actual filtering.")
            
        except Exception as e:
            print(f"Error during dry run: {e}")
            exit(1)
        
        exit(0)
    
    # Run the actual filterer
    print("🚀 Starting filterer...")
    start_time = time.time()
    
    try:
        use_queue = not args.no_queue
        result = YouTubeOutputFilterer.run_filterer(args.manifest, instance_id=args.instance_id, use_queue=use_queue)
        
        # Print detailed summary
        print("\n" + "=" * 50)
        print("PROCESSING COMPLETED")
        print("=" * 50)
        print(f"📊 Total processed: {result.total_processed}")
        print(f"✅ Files kept (children's voice): {result.files_kept}")
        print(f"   └─ Organized into language folders")
        print(f"🗑️  Files deleted (no children's voice): {result.files_deleted}")
        print(f"❓ Files not found: {result.files_not_found}")
        print(f"❌ Errors: {result.errors}")
        print(f"⏱️  Processing time: {result.processing_time:.2f} seconds")
        
        if result.total_processed > 0:
            success_rate = ((result.files_kept + result.files_deleted) / result.total_processed) * 100
            print(f"📈 Success rate: {success_rate:.1f}%")
            
            if result.files_kept + result.files_deleted > 0:
                children_ratio = (result.files_kept / (result.files_kept + result.files_deleted)) * 100
                print(f"👶 Children's voice ratio: {children_ratio:.1f}%")
        
        print("=" * 50)
        
        if result.files_not_found > 0:
            print(f"\n⚠️  {result.files_not_found} files were not found (audio files may be on another machine)")
            print("   These records have been marked as classified=false in the manifest")
        
        if result.errors > 0:
            print(f"\n❌ {result.errors} errors occurred during processing:")
            for error in result.error_details:
                print(f"   - {error}")
            print("\nCheck the logs above for detailed error information.")
            exit(1)
        else:
            print(f"\n🎉 Processing completed successfully!")
            if result.total_processed == 0:
                print("   No unclassified records found - all files have already been processed!")
            exit(0)
    
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        print("Check the logs above for detailed error information.")
        exit(1)


if __name__ == "__main__":
    main()