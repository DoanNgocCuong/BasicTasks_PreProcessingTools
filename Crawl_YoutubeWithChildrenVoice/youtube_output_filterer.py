#!/usr/bin/env python3
"""
YouTube Output Filterer

This module filters downloaded audio files based on children's voice detection,
managing the manifest accordingly and supporting concurrent execution.

Features:
    - Processes audio files using paths from manifest.json
    - Uses AudioClassifier for children's voice detection
    - Removes files without children's voices and updates manifest
    - Marks processed files to avoid reprocessing
    - Supports concurrent execution with thread safety
    - Handles missing files and error cases gracefully

Author: Generated for YouTube Audio Crawler
Version: 1.0
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import shutil

# Import the existing AudioClassifier
from youtube_audio_classifier import AudioClassifier


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
    
    def __init__(self, manifest_path: str, audio_classifier: Optional[AudioClassifier] = None):
        """
        Initialize the filterer.
        
        Args:
            manifest_path: Path to the manifest.json file
            audio_classifier: Optional AudioClassifier instance (creates new if None)
        """
        self.manifest_path = Path(manifest_path)
        self.audio_classifier = audio_classifier or AudioClassifier()
        self._lock = threading.Lock()  # For thread-safe manifest updates
        
        # Validate manifest file exists
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {self.manifest_path}")
        
        logger.info(f"Initialized YouTubeOutputFilterer with manifest: {self.manifest_path}")
    
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
                    logger.info(f"Record {record.get('video_id', 'unknown')} -> {result.action_taken}")
        
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
                    processing_time=time.time() - start_time
                )
            
            # Re-check if record was classified by another instance
            current_record = self._get_current_record(record)
            if current_record and current_record.get('classified', False):
                return ProcessingResult(
                    record_id=video_id,
                    has_children_voice=current_record.get('has_children_voice', False),
                    action_taken="skipped",
                    error_message="Already classified by another instance",
                    processing_time=time.time() - start_time
                )
            
            # Classify audio
            logger.info(f"Classifying audio: {output_path}")
            is_child = self.audio_classifier.is_child_audio_optimized(output_path)
            
            if is_child is None:
                # Classification error - mark as classified but keep file
                self._update_record_classification(record, classified=True, has_children_voice=False)
                return ProcessingResult(
                    record_id=video_id,
                    has_children_voice=False,
                    action_taken="error",
                    error_message="Audio classification failed",
                    processing_time=time.time() - start_time
                )
            
            if is_child:
                # Keep file and mark as classified
                self._update_record_classification(record, classified=True, has_children_voice=True)
                return ProcessingResult(
                    record_id=video_id,
                    has_children_voice=True,
                    action_taken="kept",
                    error_message=None,
                    processing_time=time.time() - start_time
                )
            else:
                # Delete file and remove from manifest
                self._delete_file_and_update_manifest(record)
                return ProcessingResult(
                    record_id=video_id,
                    has_children_voice=False,
                    action_taken="deleted",
                    error_message=None,
                    processing_time=time.time() - start_time
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
                processing_time=time.time() - start_time
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
    
    def _update_record_classification(self, record: Dict, classified: bool, has_children_voice: bool) -> None:
        """
        Update a single record's classification status in the manifest.
        
        Args:
            record: Record to update
            classified: Whether record has been classified
            has_children_voice: Whether children's voice was detected
        """
        video_id = record.get('video_id')
        updates = [{
            'video_id': video_id,
            'classified': classified,
            'has_children_voice': has_children_voice,
            'classification_timestamp': datetime.now().isoformat()
        }]
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
    def run_filterer(manifest_path: Optional[str] = None) -> FilterResult:
        """
        Single entry point for API usage.
        
        Args:
            manifest_path: Path to manifest.json (defaults to standard location)
            
        Returns:
            FilterResult containing processing statistics
        """
        if manifest_path is None:
            # Use default path relative to this script
            script_dir = Path(__file__).parent
            manifest_path = str(script_dir / "final_audio_files" / "manifest.json")
        
        try:
            filterer = YouTubeOutputFilterer(str(manifest_path))
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


def main():
    """Main function for direct script execution."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="YouTube Output Filterer - Filter audio files based on children's voice detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python youtube_output_filterer.py
  python youtube_output_filterer.py --manifest /path/to/manifest.json
  python youtube_output_filterer.py --dry-run
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
            
            filterer = YouTubeOutputFilterer(manifest_path)
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
        result = YouTubeOutputFilterer.run_filterer(args.manifest)
        
        # Print detailed summary
        print("\n" + "=" * 50)
        print("PROCESSING COMPLETED")
        print("=" * 50)
        print(f"📊 Total processed: {result.total_processed}")
        print(f"✅ Files kept (children's voice): {result.files_kept}")
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