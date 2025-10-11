#!/usr/bin/env python3
"""
YouTube Output Filterer API - Client-Server Architecture

FastAPI-based API for remote audio file processing.
Enables clients to send audio files to a server for children's voice detection processing,
utilizing the server's computational resources while modifying the client's files.

Features:
    - Upload manifest and audio files for processing (POST /upload)
    - Process uploaded files using server's computing power (POST /process)
    - Download processed results and updated manifest (GET /download)
    - Real-time processing status and progress tracking (GET /status)
    - Combined upload+process workflow (POST /filter-remote)
    - Health check and server statistics
    - Automatic cleanup of temporary files
    - File size limits and security measures
    - Client helper utilities for easy integration

Author: Generated for YouTube Audio Crawler
Version: 2.0 - Client-Server Architecture
"""

import asyncio
import json
import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, BinaryIO

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel, Field
import aiofiles
import aiofiles.os

# Import the filterer module
try:
    from youtube_output_filterer import YouTubeOutputFilterer, FilterResult, ProcessingResult
except ImportError as e:
    print(f"Warning: Could not import filterer module: {e}")
    # Create mock classes for testing
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
        def __init__(self, manifest_path):
            self.manifest_path = manifest_path
        
        def get_unclassified_records(self):
            return []

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# =================================================================
# CONFIGURATION AND CONSTANTS
# =================================================================

# File upload limits (configurable)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "500"))  # 500MB per file
MAX_TOTAL_UPLOAD_SIZE_MB = int(os.getenv("MAX_TOTAL_UPLOAD_SIZE_MB", "2000"))  # 2GB total
MAX_FILES_PER_UPLOAD = int(os.getenv("MAX_FILES_PER_UPLOAD", "100"))  # 100 files max
TEMP_FILE_CLEANUP_HOURS = int(os.getenv("TEMP_FILE_CLEANUP_HOURS", "24"))  # Clean after 24h
UPLOAD_TIMEOUT_MINUTES = int(os.getenv("UPLOAD_TIMEOUT_MINUTES", "30"))  # 30min timeout

# Convert to bytes
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
MAX_TOTAL_UPLOAD_SIZE_BYTES = MAX_TOTAL_UPLOAD_SIZE_MB * 1024 * 1024

# =================================================================
# PYDANTIC MODELS
# =================================================================

class UploadResponse(BaseModel):
    """Response model for file upload."""
    success: bool
    message: str
    session_id: str
    files_uploaded: int
    total_size_mb: float
    manifest_received: bool

class ProcessRequest(BaseModel):
    """Request model for processing operation."""
    session_id: str
    dry_run: bool = Field(
        default=False,
        description="If true, shows what would be processed without making changes"
    )

class ProcessResponse(BaseModel):
    """Response model for processing operation."""
    success: bool
    message: str
    task_id: Optional[str] = None
    session_id: str
    dry_run_results: Optional[Dict[str, Any]] = None

class DownloadRequest(BaseModel):
    """Request model for download operation."""
    session_id: str
    include_deleted_files: bool = Field(
        default=False,
        description="Whether to include files that were marked for deletion"
    )

class RemoteFilterRequest(BaseModel):
    """Request model for combined upload+process operation."""
    dry_run: bool = Field(
        default=False,
        description="If true, shows what would be processed without making changes"
    )

class RemoteFilterResponse(BaseModel):
    """Response model for combined filter operation."""
    success: bool
    message: str
    task_id: Optional[str] = None
    session_id: str
    dry_run_results: Optional[Dict[str, Any]] = None

class StatusResponse(BaseModel):
    """Response model for status check."""
    task_id: str
    session_id: Optional[str] = None
    status: str  # "uploading", "processing", "completed", "failed", "not_found"
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    download_ready: bool = False

class SessionInfo(BaseModel):
    """Information about an upload session."""
    session_id: str
    created_at: str
    files_count: int
    total_size_mb: float
    manifest_present: bool
    status: str  # "uploaded", "processing", "completed", "failed", "expired"
    last_activity: str

class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    version: str
    audio_classifier_ready: bool
    temp_storage_available: bool
    active_sessions: int

# =================================================================
# SESSION AND TEMPORARY FILE MANAGEMENT
# =================================================================

class UploadSession:
    """Manages an upload session with temporary files."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.temp_dir = tempfile.mkdtemp(prefix=f"filterer_session_{session_id}_")
        self.files: Dict[str, str] = {}  # filename -> temp_path mapping
        self.manifest_data: Optional[Dict] = None
        self.status = "uploading"
        self.total_size_bytes = 0
        self._lock = threading.Lock()
        
        logger.info(f"Created upload session {session_id} with temp dir: {self.temp_dir}")
    
    def add_file(self, filename: str, content: bytes) -> str:
        """Add a file to the session."""
        with self._lock:
            temp_path = os.path.join(self.temp_dir, filename)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            # Write file
            with open(temp_path, 'wb') as f:
                f.write(content)
            
            self.files[filename] = temp_path
            self.total_size_bytes += len(content)
            self.last_activity = datetime.now()
            
            logger.debug(f"Added file {filename} to session {self.session_id}")
            return temp_path
    
    def set_manifest(self, manifest_data: Dict) -> None:
        """Set the manifest data for the session."""
        with self._lock:
            self.manifest_data = manifest_data
            self.last_activity = datetime.now()
            logger.debug(f"Set manifest for session {self.session_id}")
    
    def get_temp_manifest_path(self) -> str:
        """Get path for temporary manifest file."""
        return os.path.join(self.temp_dir, "manifest.json")
    
    def write_manifest_to_temp(self) -> str:
        """Write manifest data to temporary file and return path."""
        if not self.manifest_data:
            raise ValueError("No manifest data available")
        
        manifest_path = self.get_temp_manifest_path()
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest_data, f, indent=2, ensure_ascii=False)
        
        return manifest_path
    
    def cleanup(self) -> None:
        """Clean up temporary files and directory."""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up session {self.session_id} temp dir: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up session {self.session_id}: {e}")
    
    def is_expired(self, max_age_hours: int = TEMP_FILE_CLEANUP_HOURS) -> bool:
        """Check if session has expired."""
        age = datetime.now() - self.last_activity
        return age.total_seconds() > (max_age_hours * 3600)
    
    def get_info(self) -> SessionInfo:
        """Get session information."""
        return SessionInfo(
            session_id=self.session_id,
            created_at=self.created_at.isoformat(),
            files_count=len(self.files),
            total_size_mb=round(self.total_size_bytes / (1024 * 1024), 2),
            manifest_present=self.manifest_data is not None,
            status=self.status,
            last_activity=self.last_activity.isoformat()
        )

class SessionManager:
    """Manages upload sessions."""
    
    def __init__(self):
        self.sessions: Dict[str, UploadSession] = {}
        self._lock = threading.Lock()
    
    def create_session(self) -> str:
        """Create a new upload session."""
        session_id = str(uuid.uuid4())
        with self._lock:
            session = UploadSession(session_id)
            self.sessions[session_id] = session
        
        logger.info(f"Created new upload session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[UploadSession]:
        """Get an existing session."""
        with self._lock:
            return self.sessions.get(session_id)
    
    def remove_session(self, session_id: str) -> None:
        """Remove and cleanup a session."""
        with self._lock:
            session = self.sessions.pop(session_id, None)
            if session:
                session.cleanup()
                logger.info(f"Removed session: {session_id}")
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions."""
        expired_count = 0
        with self._lock:
            expired_sessions = []
            for session_id, session in self.sessions.items():
                if session.is_expired():
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                session = self.sessions.pop(session_id)
                session.cleanup()
                expired_count += 1
                logger.info(f"Cleaned up expired session: {session_id}")
        
        return expired_count
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions."""
        with self._lock:
            return len(self.sessions)
    
    def list_sessions(self) -> List[SessionInfo]:
        """List all active sessions."""
        with self._lock:
            return [session.get_info() for session in self.sessions.values()]

# =================================================================
# TASK MANAGEMENT
# =================================================================

class TaskManager:
    """Manages background processing tasks for sessions."""
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
    
    def create_task(self, task_id: str, session_id: str) -> None:
        """Create a new processing task."""
        with self.lock:
            self.tasks[task_id] = {
                "status": "processing",
                "session_id": session_id,
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "progress": {
                    "current": 0,
                    "total": 0,
                    "current_file": None
                },
                "result": None,
                "error": None
            }
    
    def update_progress(self, task_id: str, current: int, total: int, current_file: Optional[str] = None) -> None:
        """Update task progress."""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id]["progress"] = {
                    "current": current,
                    "total": total,
                    "current_file": current_file,
                    "percentage": round((current / total) * 100, 2) if total > 0 else 0
                }
    
    def complete_task(self, task_id: str, result: FilterResult) -> None:
        """Mark task as completed."""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].update({
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "result": {
                        "total_processed": result.total_processed,
                        "files_kept": result.files_kept,
                        "files_deleted": result.files_deleted,
                        "files_not_found": result.files_not_found,
                        "errors": result.errors,
                        "processing_time": result.processing_time,
                        "error_details": result.error_details
                    }
                })
    
    def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].update({
                    "status": "failed",
                    "completed_at": datetime.now().isoformat(),
                    "error": error
                })
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task information."""
        with self.lock:
            return self.tasks.get(task_id)
    
    def cleanup_old_tasks(self, max_age_hours: int = 24) -> None:
        """Clean up old completed tasks."""
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)
        with self.lock:
            to_remove = []
            for task_id, task_info in self.tasks.items():
                if task_info.get("completed_at"):
                    try:
                        completed_time = datetime.fromisoformat(task_info["completed_at"]).timestamp()
                        if completed_time < cutoff_time:
                            to_remove.append(task_id)
                    except Exception:
                        pass
            
            for task_id in to_remove:
                del self.tasks[task_id]
                logger.info(f"Cleaned up old task: {task_id}")

# =================================================================
# REMOTE FILTERER CLASS
# =================================================================

class RemoteYouTubeFilterer(YouTubeOutputFilterer):
    """
    Modified filterer that works with uploaded files and temporary storage.
    Updates file paths in manifest to point to temporary uploaded files.
    """
    
    def __init__(self, session: UploadSession, task_id: str, task_manager: TaskManager):
        """Initialize remote filterer with session data."""
        self.session = session
        self.task_id = task_id
        self.task_manager = task_manager
        
        # Create temporary manifest file
        self.manifest_path = Path(session.write_manifest_to_temp())
        
        # Update manifest to point to uploaded files
        self._update_manifest_file_paths()
        
        # Initialize audio classifier
        try:
            from youtube_audio_classifier import AudioClassifier
            self.audio_classifier = AudioClassifier()
        except Exception as e:
            logger.error(f"Failed to initialize AudioClassifier: {e}")
            raise
        
        self._lock = threading.Lock()
        
        logger.info(f"Initialized RemoteYouTubeFilterer for session {session.session_id}")
    
    def _update_manifest_file_paths(self) -> None:
        """Update manifest to point to uploaded temporary files."""
        if not self.session.manifest_data:
            raise ValueError("No manifest data in session")
        
        updated_manifest = self.session.manifest_data.copy()
        records = updated_manifest.get('records', [])
        
        updated_records = []
        for record in records:
            output_path = record.get('output_path', '')
            if output_path:
                # Extract filename from original path
                filename = os.path.basename(output_path)
                
                # Check if this file was uploaded
                if filename in self.session.files:
                    # Update path to point to uploaded temp file
                    record = record.copy()
                    record['output_path'] = self.session.files[filename]
                    record['original_output_path'] = output_path  # Keep original for client
                    updated_records.append(record)
                    logger.debug(f"Updated path for {filename}: {output_path} -> {record['output_path']}")
                else:
                    # File not uploaded - mark for skipping
                    record = record.copy()
                    record['file_missing_in_upload'] = True
                    record['original_output_path'] = output_path
                    updated_records.append(record)
                    logger.warning(f"File {filename} referenced in manifest but not uploaded")
            else:
                updated_records.append(record)
        
        updated_manifest['records'] = updated_records
        
        # Write updated manifest to temp file
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(updated_manifest, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Updated manifest paths for {len(updated_records)} records")
    
    def get_unclassified_records(self) -> List[Dict]:
        """Get unclassified records that have uploaded files."""
        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            records = manifest_data.get('records', [])
            unclassified = []
            
            for record in records:
                # Skip if already classified
                if record.get('classified', False):
                    continue
                
                # Skip if file was not uploaded
                if record.get('file_missing_in_upload', False):
                    logger.debug(f"Skipping {record.get('video_id', 'unknown')} - file not uploaded")
                    continue
                
                unclassified.append(record)
            
            logger.info(f"Found {len(unclassified)} unclassified records with uploaded files")
            return unclassified
        
        except Exception as e:
            logger.error(f"Error reading manifest: {e}")
            raise
    
    def filter_audio_files(self) -> FilterResult:
        """Override to add progress reporting for remote processing."""
        start_time = time.time()
        logger.info(f"Starting remote audio file filtering for session {self.session.session_id}")
        
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
            
            # Update total in task manager
            self.task_manager.update_progress(self.task_id, 0, total_processed)
            
            if total_processed == 0:
                logger.info("No unclassified records with uploaded files found")
                return FilterResult(
                    total_processed=0,
                    files_kept=0,
                    files_deleted=0,
                    files_not_found=0,
                    errors=0,
                    processing_time=time.time() - start_time,
                    error_details=[]
                )
            
            logger.info(f"Processing {total_processed} uploaded records")
            
            # Process each record
            for i, record in enumerate(unclassified_records, 1):
                video_id = record.get('video_id', 'unknown')
                
                # Update progress
                self.task_manager.update_progress(
                    self.task_id, i - 1, total_processed, 
                    f"Processing {video_id}"
                )
                
                logger.info(f"Processing record {i}/{total_processed}: {video_id}")
                
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
                    logger.error(f"Error processing {video_id}: {result.error_message}")
                else:
                    chunk_info = ""
                    if result.was_chunked and result.chunks_analyzed is not None:
                        chunk_info = f" (analyzed {result.chunks_analyzed} chunks"
                        if result.positive_chunk_index is not None:
                            chunk_info += f", positive at chunk {result.positive_chunk_index + 1})"
                        else:
                            chunk_info += ")"
                    logger.info(f"Record {video_id} -> {result.action_taken}{chunk_info}")
            
            # Final progress update
            self.task_manager.update_progress(self.task_id, total_processed, total_processed, "Completed")
        
        except Exception as e:
            logger.error(f"Fatal error during remote filtering: {e}")
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
    
    def process_single_record(self, record: Dict) -> ProcessingResult:
        """Process a single audio file record."""
        start_time = time.time()
        video_id = record.get('video_id', 'unknown')
        output_path = record.get('output_path', '')
        
        try:
            # Check if file exists
            if not output_path or not os.path.exists(output_path):
                return ProcessingResult(
                    record_id=video_id,
                    has_children_voice=False,
                    action_taken="file_not_found",
                    error_message=f"File not found: {output_path}",
                    processing_time=time.time() - start_time
                )
            
            # Analyze audio for children's voice
            analysis_result = self.audio_classifier.analyze_audio_chunked(
                output_path, 
                max_chunks=3,  # Analyze first 3 chunks only
                early_exit=True  # Exit early on positive detection
            )
            
            has_children_voice = analysis_result['has_children_voice']
            chunks_analyzed = analysis_result.get('chunks_analyzed', 0)
            positive_chunk_index = analysis_result.get('positive_chunk_index')
            was_chunked = analysis_result.get('was_chunked', False)
            
            if has_children_voice:
                # Keep file - mark as classified
                self._mark_record_classified(record, True, analysis_result)
                action = "kept"
            else:
                # Delete file - mark as classified and remove file
                self._mark_record_classified(record, False, analysis_result)
                try:
                    os.remove(output_path)
                    logger.info(f"Deleted file: {output_path}")
                except OSError as e:
                    logger.warning(f"Could not delete file {output_path}: {e}")
                action = "deleted"
            
            return ProcessingResult(
                record_id=video_id,
                has_children_voice=has_children_voice,
                action_taken=action,
                error_message=None,
                processing_time=time.time() - start_time,
                chunks_analyzed=chunks_analyzed,
                positive_chunk_index=positive_chunk_index,
                was_chunked=was_chunked
            )
            
        except Exception as e:
            error_msg = f"Error processing {video_id}: {str(e)}"
            logger.error(error_msg)
            return ProcessingResult(
                record_id=video_id,
                has_children_voice=False,
                action_taken="error",
                error_message=error_msg,
                processing_time=time.time() - start_time
            )
    
    def _mark_record_classified(self, record: Dict, has_children_voice: bool, analysis_result: Dict) -> None:
        """Mark a record as classified in the manifest."""
        with self._lock:
            try:
                # Read current manifest
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
                
                # Find and update the record
                video_id = record.get('video_id')
                records = manifest_data.get('records', [])
                
                for i, manifest_record in enumerate(records):
                    if manifest_record.get('video_id') == video_id:
                        # Update record
                        records[i]['classified'] = True
                        records[i]['has_children_voice'] = has_children_voice
                        records[i]['classification_date'] = datetime.now().isoformat()
                        records[i]['chunks_analyzed'] = analysis_result.get('chunks_analyzed', 0)
                        records[i]['was_chunked'] = analysis_result.get('was_chunked', False)
                        if analysis_result.get('positive_chunk_index') is not None:
                            records[i]['positive_chunk_index'] = analysis_result['positive_chunk_index']
                        break
                
                # Write updated manifest
                manifest_data['records'] = records
                with open(self.manifest_path, 'w', encoding='utf-8') as f:
                    json.dump(manifest_data, f, indent=2, ensure_ascii=False)
                    
            except Exception as e:
                logger.error(f"Error marking record {video_id} as classified: {e}")
                raise
    
    def _log_summary(self, result: FilterResult) -> None:
        """Log a summary of the filtering results."""
        logger.info("=" * 60)
        logger.info("REMOTE FILTERING SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total processed: {result.total_processed}")
        logger.info(f"Files kept: {result.files_kept}")
        logger.info(f"Files deleted: {result.files_deleted}")
        logger.info(f"Files not found: {result.files_not_found}")
        logger.info(f"Errors: {result.errors}")
        logger.info(f"Processing time: {result.processing_time:.2f} seconds")
        
        if result.error_details:
            logger.info("Error details:")
            for error in result.error_details[:10]:  # Show first 10 errors
                logger.info(f"  - {error}")
            if len(result.error_details) > 10:
                logger.info(f"  ... and {len(result.error_details) - 10} more errors")
        
        logger.info("=" * 60)
    
    def get_processed_manifest_data(self) -> Dict:
        """Get the processed manifest data with original paths restored."""
        with open(self.manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        
        # Restore original paths for client
        records = manifest_data.get('records', [])
        for record in records:
            if 'original_output_path' in record:
                record['output_path'] = record.pop('original_output_path')
            
            # Remove temporary fields
            record.pop('file_missing_in_upload', None)
        
        return manifest_data
    
    def get_files_to_keep(self) -> List[str]:
        """Get list of temporary file paths that should be kept (sent back to client)."""
        files_to_keep = []
        
        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            records = manifest_data.get('records', [])
            for record in records:
                # If record is classified and has children's voice, keep the file
                if (record.get('classified', False) and 
                    record.get('has_children_voice', False) and
                    record.get('output_path')):
                    
                    temp_path = record['output_path']
                    if os.path.exists(temp_path):
                        files_to_keep.append(temp_path)
        
        except Exception as e:
            logger.error(f"Error determining files to keep: {e}")
        
        return files_to_keep

# =================================================================
# FASTAPI APP SETUP
# =================================================================

app = FastAPI(
    title="YouTube Output Filterer API - Client-Server",
    description="API for remote audio file processing using server's computational resources",
    version="2.0.0"
)

# Initialize managers
session_manager = SessionManager()
task_manager = TaskManager()

# =================================================================
# HELPER FUNCTIONS
# =================================================================

def generate_task_id() -> str:
    """Generate a unique task ID."""
    return f"process_{int(time.time() * 1000)}_{os.getpid()}"

def validate_file_size(file_size: int) -> None:
    """Validate uploaded file size."""
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB"
        )

def validate_total_upload_size(current_size: int, additional_size: int) -> None:
    """Validate total upload size."""
    if current_size + additional_size > MAX_TOTAL_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Total upload too large. Maximum: {MAX_TOTAL_UPLOAD_SIZE_MB}MB"
        )

async def run_remote_processing_task(session_id: str, task_id: str) -> None:
    """Run the remote processing task in background."""
    try:
        logger.info(f"Starting remote processing task {task_id} for session {session_id}")
        
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            task_manager.fail_task(task_id, "Session not found")
            return
        
        # Update session status
        session.status = "processing"
        
        # Create remote filterer and run processing
        filterer = RemoteYouTubeFilterer(session, task_id, task_manager)
        result = filterer.filter_audio_files()
        
        # Mark task as completed
        task_manager.complete_task(task_id, result)
        session.status = "completed"
        
        logger.info(f"Remote processing task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Remote processing task {task_id} failed: {e}")
        task_manager.fail_task(task_id, str(e))
        
        # Update session status
        session = session_manager.get_session(session_id)
        if session:
            session.status = "failed"

def create_download_zip(session: UploadSession) -> str:
    """Create a ZIP file with processed results."""
    # Get processed manifest
    if not session.manifest_data:
        raise ValueError("No manifest data available")
    
    # Create filterer to get processed data
    filterer = RemoteYouTubeFilterer(session, "download", task_manager)
    processed_manifest = filterer.get_processed_manifest_data()
    files_to_keep = filterer.get_files_to_keep()
    
    # Create ZIP file
    zip_path = os.path.join(session.temp_dir, "processed_results.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add updated manifest
        manifest_json = json.dumps(processed_manifest, indent=2, ensure_ascii=False)
        zipf.writestr("manifest.json", manifest_json)
        
        # Add kept audio files
        for temp_file_path in files_to_keep:
            if os.path.exists(temp_file_path):
                # Get original filename from manifest
                filename = None
                for record in processed_manifest.get('records', []):
                    if record.get('has_children_voice', False):
                        original_path = record.get('output_path', '')
                        if original_path:
                            candidate_filename = os.path.basename(original_path)
                            candidate_temp_path = session.files.get(candidate_filename)
                            if candidate_temp_path == temp_file_path:
                                filename = candidate_filename
                                break
                
                if filename:
                    zipf.write(temp_file_path, f"audio_files/{filename}")
                    logger.debug(f"Added {filename} to download ZIP")
                else:
                    # Fallback filename
                    filename = f"kept_file_{os.path.basename(temp_file_path)}"
                    zipf.write(temp_file_path, f"audio_files/{filename}")
                    logger.warning(f"Used fallback filename for {temp_file_path}")
    
    logger.info(f"Created download ZIP: {zip_path}")
    return zip_path

# =================================================================
# API ENDPOINTS
# =================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check if audio classifier can be initialized
        audio_classifier_ready = True
        try:
            from youtube_audio_classifier import AudioClassifier
            AudioClassifier()
        except Exception:
            audio_classifier_ready = False
        
        # Check temp storage
        temp_storage_available = True
        try:
            test_dir = tempfile.mkdtemp(prefix="health_test_")
            os.rmdir(test_dir)
        except Exception:
            temp_storage_available = False
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version="2.0.0",
            audio_classifier_ready=audio_classifier_ready,
            temp_storage_available=temp_storage_available,
            active_sessions=session_manager.get_active_sessions_count()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: List[UploadFile] = File(...),
    manifest: Optional[str] = Form(None)
):
    """Upload audio files and manifest for processing."""
    try:
        # Validate number of files
        if len(files) > MAX_FILES_PER_UPLOAD:
            raise HTTPException(
                status_code=413,
                detail=f"Too many files. Maximum: {MAX_FILES_PER_UPLOAD}"
            )
        
        # Create session
        session_id = session_manager.create_session()
        session = session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=500, detail="Failed to create session")
        
        total_size = 0
        files_uploaded = 0
        
        # Process manifest if provided
        manifest_received = False
        if manifest:
            try:
                manifest_data = json.loads(manifest)
                session.set_manifest(manifest_data)
                manifest_received = True
                logger.info(f"Received manifest with {len(manifest_data.get('records', []))} records")
            except json.JSONDecodeError:
                session_manager.remove_session(session_id)
                raise HTTPException(status_code=400, detail="Invalid manifest JSON")
        
        # Process uploaded files
        for file in files:
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Validate file size
            validate_file_size(file_size)
            validate_total_upload_size(total_size, file_size)
            
            # Save file to session
            session.add_file(file.filename, content)
            total_size += file_size
            files_uploaded += 1
            
            logger.info(f"Uploaded file: {file.filename} ({file_size / 1024 / 1024:.2f}MB)")
        
        total_size_mb = total_size / 1024 / 1024
        
        logger.info(f"Upload completed for session {session_id}: {files_uploaded} files, {total_size_mb:.2f}MB")
        
        return UploadResponse(
            success=True,
            message=f"Successfully uploaded {files_uploaded} files",
            session_id=session_id,
            files_uploaded=files_uploaded,
            total_size_mb=round(total_size_mb, 2),
            manifest_received=manifest_received
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/process", response_model=ProcessResponse)
async def process_files(
    request: ProcessRequest,
    background_tasks: BackgroundTasks
):
    """Process uploaded files."""
    try:
        # Get session
        session = session_manager.get_session(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Check if manifest was provided
        if not session.manifest_data:
            raise HTTPException(status_code=400, detail="No manifest data in session")
        
        if request.dry_run:
            # Handle dry run
            logger.info(f"Performing dry run for session {request.session_id}")
            
            # Create temporary filterer to analyze what would be processed
            temp_filterer = RemoteYouTubeFilterer(session, "dry_run", task_manager)
            unclassified = temp_filterer.get_unclassified_records()
            
            dry_run_results = {
                "session_id": request.session_id,
                "unclassified_count": len(unclassified),
                "files_to_process": []
            }
            
            for i, record in enumerate(unclassified[:10], 1):  # Show first 10
                video_id = record.get('video_id', 'unknown')
                output_path = record.get('output_path', '')
                filename = os.path.basename(output_path) if output_path else 'unknown'
                file_uploaded = filename in session.files
                
                dry_run_results["files_to_process"].append({
                    "index": i,
                    "video_id": video_id,
                    "filename": filename,
                    "file_uploaded": file_uploaded
                })
            
            if len(unclassified) > 10:
                dry_run_results["additional_files"] = len(unclassified) - 10
            
            return ProcessResponse(
                success=True,
                message=f"Dry run completed. Found {len(unclassified)} unclassified records with uploaded files.",
                session_id=request.session_id,
                dry_run_results=dry_run_results
            )
        
        # Start actual processing task
        task_id = generate_task_id()
        task_manager.create_task(task_id, request.session_id)
        
        # Add background task
        background_tasks.add_task(run_remote_processing_task, request.session_id, task_id)
        
        return ProcessResponse(
            success=True,
            message="Processing task started successfully",
            task_id=task_id,
            session_id=request.session_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting processing task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start processing task: {str(e)}"
        )

@app.get("/status/{task_id}", response_model=StatusResponse)
async def get_task_status(task_id: str):
    """Get status of a processing task."""
    task_info = task_manager.get_task(task_id)
    
    if not task_info:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    # Check if download is ready
    download_ready = False
    if task_info.get("status") == "completed":
        session_id = task_info.get("session_id")
        session = session_manager.get_session(session_id)
        download_ready = session is not None
    
    return StatusResponse(
        task_id=task_id,
        session_id=task_info.get("session_id"),
        status=task_info["status"],
        progress=task_info.get("progress"),
        result=task_info.get("result"),
        error=task_info.get("error"),
        started_at=task_info.get("started_at"),
        completed_at=task_info.get("completed_at"),
        download_ready=download_ready
    )

@app.get("/download/{session_id}")
async def download_results(session_id: str):
    """Download processed results as a ZIP file."""
    try:
        # Get session
        session = session_manager.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session.status != "completed":
            raise HTTPException(
                status_code=400, 
                detail=f"Session not ready for download. Status: {session.status}"
            )
        
        # Create download ZIP
        zip_path = create_download_zip(session)
        
        # Return ZIP file
        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"processed_results_{session_id}.zip",
            headers={"Content-Disposition": f"attachment; filename=processed_results_{session_id}.zip"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download error: {e}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")

@app.post("/filter-remote", response_model=RemoteFilterResponse)
async def filter_remote_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    manifest: str = Form(...),
    dry_run: bool = Form(False)
):
    """Combined upload and process endpoint for convenience."""
    try:
        # Upload files first
        upload_response = await upload_files(files=files, manifest=manifest)
        
        if not upload_response.success:
            raise HTTPException(status_code=500, detail="Upload failed")
        
        # Process files
        process_request = ProcessRequest(
            session_id=upload_response.session_id,
            dry_run=dry_run
        )
        
        process_response = await process_files(process_request, background_tasks)
        
        return RemoteFilterResponse(
            success=process_response.success,
            message=f"Upload and processing initiated. {upload_response.message}",
            task_id=process_response.task_id,
            session_id=upload_response.session_id,
            dry_run_results=process_response.dry_run_results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Remote filter error: {e}")
        raise HTTPException(status_code=500, detail=f"Remote filter failed: {str(e)}")

@app.get("/sessions")
async def list_sessions():
    """List all active sessions."""
    # Clean up expired sessions first
    cleaned_count = session_manager.cleanup_expired_sessions()
    if cleaned_count > 0:
        logger.info(f"Cleaned up {cleaned_count} expired sessions")
    
    sessions = session_manager.list_sessions()
    return {"sessions": [session.dict() for session in sessions]}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and clean up its temporary files."""
    session = session_manager.get_session(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_manager.remove_session(session_id)
    return {"message": f"Session {session_id} deleted successfully"}

@app.get("/tasks")
async def list_active_tasks():
    """List all active and recent tasks."""
    # Clean up old tasks first
    task_manager.cleanup_old_tasks()
    
    tasks = []
    with task_manager.lock:
        for task_id, task_info in task_manager.tasks.items():
            tasks.append({
                "task_id": task_id,
                "session_id": task_info.get("session_id"),
                "status": task_info["status"],
                "started_at": task_info.get("started_at"),
                "completed_at": task_info.get("completed_at"),
                "progress": task_info.get("progress")
            })
    
    return {"tasks": tasks}

# =================================================================
# CLIENT HELPER UTILITIES
# =================================================================

class YouTubeFiltererClient:
    """
    Client helper class for easy interaction with the remote filtering API.
    Use this class from your local machine to send files to the server for processing.
    """
    
    def __init__(self, server_url: str = "http://localhost:8000"):
        """
        Initialize the client.
        
        Args:
            server_url: Base URL of the filtering API server
        """
        self.server_url = server_url.rstrip('/')
        self.session = None
        
    def upload_and_process(
        self, 
        manifest_path: str, 
        audio_files_dir: str, 
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Upload manifest and audio files, then process them remotely.
        
        Args:
            manifest_path: Path to local manifest.json file
            audio_files_dir: Directory containing audio files referenced in manifest
            dry_run: If True, only shows what would be processed
            
        Returns:
            Dictionary with processing results
        """
        import requests
        
        try:
            # Read manifest
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            
            # Prepare files to upload
            files_to_upload = []
            audio_files = []
            
            # Find audio files referenced in manifest
            for record in manifest_data.get('records', []):
                output_path = record.get('output_path', '')
                if output_path:
                    filename = os.path.basename(output_path)
                    local_file_path = os.path.join(audio_files_dir, filename)
                    
                    if os.path.exists(local_file_path):
                        files_to_upload.append(local_file_path)
                        audio_files.append(filename)
                    else:
                        print(f"Warning: Audio file not found: {local_file_path}")
            
            print(f"Found {len(files_to_upload)} audio files to upload")
            
            if not files_to_upload and not dry_run:
                return {
                    "success": False,
                    "error": "No audio files found to upload"
                }
            
            # Prepare multipart form data
            files = []
            for file_path in files_to_upload:
                files.append(('files', (os.path.basename(file_path), open(file_path, 'rb'), 'audio/wav')))
            
            data = {
                'manifest': json.dumps(manifest_data),
                'dry_run': str(dry_run).lower()
            }
            
            # Upload and process
            print(f"Uploading to {self.server_url}/filter-remote...")
            response = requests.post(
                f"{self.server_url}/filter-remote",
                files=files,
                data=data,
                timeout=UPLOAD_TIMEOUT_MINUTES * 60
            )
            
            # Close file handles
            for _, (_, file_handle, _) in files:
                file_handle.close()
            
            if response.status_code == 200:
                result = response.json()
                self.session_id = result.get('session_id')
                self.task_id = result.get('task_id')
                
                if dry_run:
                    return result
                
                print(f"Upload successful. Session: {self.session_id}, Task: {self.task_id}")
                return result
            else:
                return {
                    "success": False,
                    "error": f"Upload failed: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Client error: {str(e)}"
            }
    
    def wait_for_completion(self, task_id: str, check_interval: int = 5) -> Dict[str, Any]:
        """
        Wait for processing to complete.
        
        Args:
            task_id: Task ID to monitor
            check_interval: How often to check status (seconds)
            
        Returns:
            Final task status
        """
        import requests
        import time
        
        print(f"Waiting for task {task_id} to complete...")
        
        while True:
            try:
                response = requests.get(f"{self.server_url}/status/{task_id}")
                
                if response.status_code == 200:
                    status = response.json()
                    
                    if status['status'] == 'completed':
                        print("✅ Processing completed successfully!")
                        return status
                    elif status['status'] == 'failed':
                        print("❌ Processing failed!")
                        return status
                    else:
                        # Show progress
                        progress = status.get('progress', {})
                        current = progress.get('current', 0)
                        total = progress.get('total', 0)
                        percentage = progress.get('percentage', 0)
                        
                        if total > 0:
                            print(f"🔄 Processing... {current}/{total} ({percentage:.1f}%)")
                        else:
                            print(f"🔄 Processing... Status: {status['status']}")
                        
                        time.sleep(check_interval)
                else:
                    print(f"Error checking status: {response.status_code}")
                    time.sleep(check_interval)
                    
            except Exception as e:
                print(f"Error checking status: {e}")
                time.sleep(check_interval)
    
    def download_results(self, session_id: str, output_path: str) -> bool:
        """
        Download processed results.
        
        Args:
            session_id: Session ID to download
            output_path: Local path to save results ZIP file
            
        Returns:
            True if download successful
        """
        import requests
        
        try:
            print(f"Downloading results for session {session_id}...")
            
            response = requests.get(
                f"{self.server_url}/download/{session_id}",
                stream=True
            )
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"✅ Results downloaded to: {output_path}")
                return True
            else:
                print(f"❌ Download failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Download error: {e}")
            return False
    
    def extract_results(self, zip_path: str, extract_to: str) -> bool:
        """
        Extract downloaded results ZIP file.
        
        Args:
            zip_path: Path to downloaded ZIP file
            extract_to: Directory to extract to
            
        Returns:
            True if extraction successful
        """
        try:
            print(f"Extracting results to: {extract_to}")
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            
            print("✅ Extraction completed")
            return True
            
        except Exception as e:
            print(f"❌ Extraction error: {e}")
            return False
    
    def process_complete_workflow(
        self, 
        manifest_path: str, 
        audio_files_dir: str, 
        output_dir: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Complete workflow: upload, process, wait, download, and extract.
        
        Args:
            manifest_path: Path to local manifest.json file
            audio_files_dir: Directory containing audio files
            output_dir: Directory to save processed results
            dry_run: If True, only shows what would be processed
            
        Returns:
            Dictionary with workflow results
        """
        # Step 1: Upload and process
        upload_result = self.upload_and_process(manifest_path, audio_files_dir, dry_run)
        
        if not upload_result.get('success'):
            return upload_result
        
        if dry_run:
            return upload_result
        
        # Step 2: Wait for completion
        task_id = upload_result.get('task_id')
        session_id = upload_result.get('session_id')
        
        if not task_id:
            return {"success": False, "error": "No task ID received"}
        
        completion_result = self.wait_for_completion(task_id)
        
        if completion_result.get('status') != 'completed':
            return {
                "success": False,
                "error": f"Processing failed: {completion_result.get('error', 'Unknown error')}"
            }
        
        # Step 3: Download results
        os.makedirs(output_dir, exist_ok=True)
        zip_path = os.path.join(output_dir, f"results_{session_id}.zip")
        
        if not self.download_results(session_id, zip_path):
            return {"success": False, "error": "Download failed"}
        
        # Step 4: Extract results
        if not self.extract_results(zip_path, output_dir):
            return {"success": False, "error": "Extraction failed"}
        
        return {
            "success": True,
            "message": "Complete workflow finished successfully",
            "session_id": session_id,
            "task_id": task_id,
            "output_dir": output_dir,
            "results_zip": zip_path,
            "processing_stats": completion_result.get('result', {})
        }

# =================================================================
# STARTUP AND SHUTDOWN EVENTS
# =================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize the API on startup."""
    logger.info("YouTube Output Filterer API (Client-Server) starting up...")
    
    # Clean up old tasks and sessions
    task_manager.cleanup_old_tasks()
    session_manager.cleanup_expired_sessions()
    
    logger.info("API startup completed")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("YouTube Output Filterer API shutting down...")
    
    # Clean up all sessions
    with session_manager._lock:
        for session in list(session_manager.sessions.values()):
            session.cleanup()
    
    logger.info("API shutdown completed")

# =================================================================
# MAIN FUNCTION FOR DIRECT EXECUTION
# =================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("YouTube Output Filterer API - Client-Server Architecture")
    print("=" * 60)
    print("This API enables remote audio processing using server computational resources")
    print("while modifying files on the client machine.")
    print()
    print("Server Endpoints:")
    print("  📖 API Documentation: http://localhost:8000/docs")
    print("  ❤️  Health Check: http://localhost:8000/health")
    print("  📤 Upload Files: POST http://localhost:8000/upload")
    print("  ⚙️  Process Files: POST http://localhost:8000/process")
    print("  📥 Download Results: GET http://localhost:8000/download/{session_id}")
    print("  🚀 Combined Workflow: POST http://localhost:8000/filter-remote")
    print()
    print("Client Usage Example:")
    print("  from api_youtube_filterer import YouTubeFiltererClient")
    print("  client = YouTubeFiltererClient('http://your-server:8000')")
    print("  result = client.process_complete_workflow(")
    print("      manifest_path='./final_audio_files/manifest.json',")
    print("      audio_files_dir='./final_audio_files/audio_files',")
    print("      output_dir='./processed_results'")
    print("  )")
    print("=" * 60)
    
    uvicorn.run(
        "api_youtube_filterer:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )