#!/usr/bin/env python3
"""
YouTube Output Filterer API

FastAPI-based API wrapper for the YouTube Output Filterer module.
Provides RESTful endpoints for filtering audio files based on children's voice detection.

Features:
    - Process all unclassified files via POST /filter
    - Get filtering status and progress via GET /status
    - Retrieve processing statistics via GET /stats
    - Health check endpoint GET /health
    - Dry run functionality for preview
    - Async processing with background tasks
    - Real-time progress tracking

Author: Generated for YouTube Audio Crawler
Version: 1.0
"""

import asyncio
import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Import the filterer module
try:
    from youtube_output_filterer import YouTubeOutputFilterer, FilterResult, ProcessingResult
except ImportError as e:
    print(f"Warning: Could not import filterer module: {e}")
    # Create mock classes for testing
    class FilterResult:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class ProcessingResult:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
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
# PYDANTIC MODELS
# =================================================================

class FilterRequest(BaseModel):
    """Request model for filtering operation."""
    manifest_path: Optional[str] = Field(
        default=None,
        description="Path to manifest.json file. If not provided, uses default location."
    )
    dry_run: bool = Field(
        default=False,
        description="If true, shows what would be processed without making changes"
    )

class FilterResponse(BaseModel):
    """Response model for filtering operation."""
    success: bool
    message: str
    task_id: Optional[str] = None
    dry_run_results: Optional[Dict[str, Any]] = None
    concurrent_info: Optional[Dict[str, Any]] = None  # Info about other running tasks

class StatusResponse(BaseModel):
    """Response model for status check."""
    task_id: str
    status: str  # "running", "completed", "failed", "not_found"
    progress: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

class StatsResponse(BaseModel):
    """Response model for statistics."""
    total_records: int
    classified_records: int
    unclassified_records: int
    files_with_children_voice: int
    files_without_children_voice: int
    missing_files: int
    manifest_path: str
    last_updated: Optional[str] = None

class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str
    timestamp: str
    version: str
    manifest_accessible: bool
    audio_classifier_ready: bool

# =================================================================
# GLOBAL STATE MANAGEMENT
# =================================================================

class RecordLockManager:
    """Manages locks for individual manifest records to prevent concurrent processing."""
    
    def __init__(self):
        self.locked_records: Dict[str, str] = {}  # video_id -> task_id mapping
        self.lock = threading.Lock()
    
    def try_lock_record(self, video_id: str, task_id: str) -> bool:
        """
        Try to lock a record for processing.
        
        Args:
            video_id: The video ID to lock
            task_id: The task requesting the lock
            
        Returns:
            True if lock acquired, False if already locked by another task
        """
        with self.lock:
            if video_id in self.locked_records:
                current_task = self.locked_records[video_id]
                if current_task != task_id:
                    return False  # Already locked by another task
            
            self.locked_records[video_id] = task_id
            return True
    
    def release_record(self, video_id: str, task_id: str) -> None:
        """
        Release a record lock.
        
        Args:
            video_id: The video ID to unlock
            task_id: The task releasing the lock
        """
        with self.lock:
            if video_id in self.locked_records and self.locked_records[video_id] == task_id:
                del self.locked_records[video_id]
    
    def release_all_records_for_task(self, task_id: str) -> List[str]:
        """
        Release all records locked by a specific task.
        
        Args:
            task_id: The task to release locks for
            
        Returns:
            List of video IDs that were released
        """
        released_records = []
        with self.lock:
            to_remove = []
            for video_id, locked_task_id in self.locked_records.items():
                if locked_task_id == task_id:
                    to_remove.append(video_id)
                    released_records.append(video_id)
            
            for video_id in to_remove:
                del self.locked_records[video_id]
        
        return released_records
    
    def get_locked_records(self) -> Dict[str, str]:
        """Get a copy of currently locked records."""
        with self.lock:
            return self.locked_records.copy()

class TaskManager:
    """Manages background filtering tasks."""
    
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()
    
    def create_task(self, task_id: str, manifest_path: str) -> None:
        """Create a new task."""
        with self.lock:
            self.tasks[task_id] = {
                "status": "running",
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "progress": {
                    "current": 0,
                    "total": 0,
                    "current_file": None
                },
                "result": None,
                "error": None,
                "manifest_path": manifest_path
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
        
        # Release all record locks for this task
        released_records = record_lock_manager.release_all_records_for_task(task_id)
        if released_records:
            logger.info(f"Released {len(released_records)} record locks for completed task {task_id}")
    
    def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed."""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].update({
                    "status": "failed",
                    "completed_at": datetime.now().isoformat(),
                    "error": error
                })
        
        # Release all record locks for this task
        released_records = record_lock_manager.release_all_records_for_task(task_id)
        if released_records:
            logger.info(f"Released {len(released_records)} record locks for failed task {task_id}")
    
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
# FASTAPI APP SETUP
# =================================================================

app = FastAPI(
    title="YouTube Output Filterer API",
    description="API for filtering audio files based on children's voice detection",
    version="1.0.0"
)

task_manager = TaskManager()
record_lock_manager = RecordLockManager()

# =================================================================
# HELPER FUNCTIONS
# =================================================================

def get_default_manifest_path() -> str:
    """Get the default manifest path."""
    script_dir = Path(__file__).parent
    return str(script_dir / "final_audio_files" / "manifest.json")

def validate_manifest_path(manifest_path: Optional[str]) -> str:
    """Validate and return manifest path."""
    if not manifest_path:
        manifest_path = get_default_manifest_path()
    
    if not os.path.exists(manifest_path):
        raise HTTPException(
            status_code=404,
            detail=f"Manifest file not found: {manifest_path}"
        )
    
    return manifest_path

def generate_task_id() -> str:
    """Generate a unique task ID."""
    return f"filter_{int(time.time() * 1000)}_{os.getpid()}"

def get_manifest_stats(manifest_path: str) -> Dict[str, Any]:
    """Get statistics from manifest file."""
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
        
        records = manifest_data.get('records', [])
        total_records = len(records)
        classified_records = len([r for r in records if r.get('classified', False)])
        unclassified_records = total_records - classified_records
        files_with_children_voice = len([r for r in records if r.get('has_children_voice', False)])
        files_without_children_voice = len([r for r in records if r.get('classified', False) and not r.get('has_children_voice', False)])
        missing_files = len([r for r in records if not os.path.exists(r.get('output_path', ''))])
        
        # Get last modification time
        last_updated = datetime.fromtimestamp(os.path.getmtime(manifest_path)).isoformat()
        
        return {
            "total_records": total_records,
            "classified_records": classified_records,
            "unclassified_records": unclassified_records,
            "files_with_children_voice": files_with_children_voice,
            "files_without_children_voice": files_without_children_voice,
            "missing_files": missing_files,
            "last_updated": last_updated
        }
    except Exception as e:
        logger.error(f"Error getting manifest stats: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error reading manifest file: {str(e)}"
        )

async def run_filtering_task(task_id: str, manifest_path: str) -> None:
    """Run the filtering task in background."""
    try:
        logger.info(f"Starting filtering task {task_id}")
        
        # Create custom filterer class that reports progress and handles record locking
        class ConcurrentFilterer(YouTubeOutputFilterer):
            def __init__(self, manifest_path: str, task_id: str, task_manager: TaskManager, lock_manager: RecordLockManager):
                super().__init__(manifest_path)
                self.task_id = task_id
                self.task_manager = task_manager
                self.lock_manager = lock_manager
            
            def get_available_unclassified_records(self) -> List[Dict]:
                """
                Get unclassified records that are not currently locked by other tasks.
                
                Returns:
                    List of unclassified record dictionaries that can be processed
                """
                all_unclassified = self.get_unclassified_records()
                available_records = []
                
                for record in all_unclassified:
                    video_id = record.get('video_id')
                    if video_id and self.lock_manager.try_lock_record(video_id, self.task_id):
                        available_records.append(record)
                        logger.debug(f"Locked record {video_id} for task {self.task_id}")
                    elif video_id:
                        logger.debug(f"Record {video_id} already locked by another task, skipping")
                    else:
                        logger.warning(f"Record has no video_id, skipping: {record}")
                
                logger.info(f"Task {self.task_id}: Found {len(available_records)} available records out of {len(all_unclassified)} unclassified")
                return available_records
            
            def process_single_record_with_lock(self, record: Dict) -> ProcessingResult:
                """
                Process a single record and ensure lock is released afterwards.
                
                Args:
                    record: Dictionary containing record information
                    
                Returns:
                    ProcessingResult with processing outcome
                """
                video_id = record.get('video_id')
                
                try:
                    # Process the record using parent class method
                    result = self.process_single_record(record)
                    return result
                    
                finally:
                    # Always release the lock when done processing this record
                    if video_id:
                        self.lock_manager.release_record(video_id, self.task_id)
                        logger.debug(f"Released lock for record {video_id} from task {self.task_id}")
            
            def filter_audio_files(self) -> FilterResult:
                """Override to add progress reporting and record-level locking."""
                start_time = time.time()
                logger.info(f"Starting concurrent audio file filtering for task {self.task_id}...")
                
                # Initialize counters
                total_processed = 0
                files_kept = 0
                files_deleted = 0
                files_not_found = 0
                errors = 0
                error_details = []
                skipped_locked = 0
                
                try:
                    # Get available unclassified records (excluding those locked by other tasks)
                    available_records = self.get_available_unclassified_records()
                    total_processed = len(available_records)
                    
                    # Count total unclassified for informational purposes
                    all_unclassified = super().get_unclassified_records()
                    skipped_locked = len(all_unclassified) - total_processed
                    
                    # Update total in task manager
                    self.task_manager.update_progress(self.task_id, 0, total_processed)
                    
                    if total_processed == 0:
                        if skipped_locked > 0:
                            logger.info(f"No available records to process. {skipped_locked} records are currently locked by other tasks.")
                        else:
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
                    
                    logger.info(f"Task {self.task_id}: Processing {total_processed} available records ({skipped_locked} skipped due to locks)")
                    
                    # Process each available record with progress updates
                    for i, record in enumerate(available_records, 1):
                        video_id = record.get('video_id', 'unknown')
                        
                        # Update progress
                        self.task_manager.update_progress(
                            self.task_id, i - 1, total_processed, 
                            f"Processing {video_id}"
                        )
                        
                        logger.info(f"Task {self.task_id}: Processing record {i}/{total_processed}: {video_id}")
                        
                        result = self.process_single_record_with_lock(record)
                        
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
                            logger.info(f"Task {self.task_id}: Record {video_id} -> {result.action_taken}{chunk_info}")
                    
                    # Final progress update
                    self.task_manager.update_progress(self.task_id, total_processed, total_processed, "Completed")
                
                except Exception as e:
                    logger.error(f"Fatal error during filtering in task {self.task_id}: {e}")
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
                
                # Add info about skipped records
                if skipped_locked > 0:
                    logger.info(f"Task {self.task_id}: Completed processing. {skipped_locked} records were skipped (locked by other tasks)")
                
                # Log summary
                self._log_summary(result)
                
                return result
        
        # Create and run filterer with record-level locking
        filterer = ConcurrentFilterer(manifest_path, task_id, task_manager, record_lock_manager)
        result = filterer.filter_audio_files()
        
        # Mark task as completed
        task_manager.complete_task(task_id, result)
        logger.info(f"Filtering task {task_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Filtering task {task_id} failed: {e}")
        task_manager.fail_task(task_id, str(e))

# =================================================================
# API ENDPOINTS
# =================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check if default manifest is accessible
        default_manifest = get_default_manifest_path()
        manifest_accessible = os.path.exists(default_manifest)
        
        # Check if audio classifier can be initialized
        audio_classifier_ready = True
        try:
            from youtube_audio_classifier import AudioClassifier
            AudioClassifier()
        except Exception:
            audio_classifier_ready = False
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            manifest_accessible=manifest_accessible,
            audio_classifier_ready=audio_classifier_ready
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")

@app.post("/filter", response_model=FilterResponse)
async def filter_audio_files(
    request: FilterRequest,
    background_tasks: BackgroundTasks
):
    """Start filtering process for unclassified audio files."""
    try:
        # Validate manifest path
        manifest_path = validate_manifest_path(request.manifest_path)
        
        if request.dry_run:
            # Handle dry run
            logger.info("Performing dry run...")
            filterer = YouTubeOutputFilterer(manifest_path)
            unclassified = filterer.get_unclassified_records()
            
            dry_run_results = {
                "unclassified_count": len(unclassified),
                "files_to_process": []
            }
            
            for i, record in enumerate(unclassified[:10], 1):  # Show first 10
                video_id = record.get('video_id', 'unknown')
                output_path = record.get('output_path', '')
                file_exists = os.path.exists(output_path) if output_path else False
                
                dry_run_results["files_to_process"].append({
                    "index": i,
                    "video_id": video_id,
                    "output_path": output_path,
                    "file_exists": file_exists
                })
            
            if len(unclassified) > 10:
                dry_run_results["additional_files"] = len(unclassified) - 10
            
            return FilterResponse(
                success=True,
                message=f"Dry run completed. Found {len(unclassified)} unclassified records.",
                dry_run_results=dry_run_results
            )
        
        # Start actual filtering task
        task_id = generate_task_id()
        task_manager.create_task(task_id, manifest_path)
        
        # Get info about other running tasks on the same manifest
        running_tasks = []
        with task_manager.lock:
            for tid, task_info in task_manager.tasks.items():
                if (task_info.get("status") == "running" and 
                    task_info.get("manifest_path") == manifest_path and 
                    tid != task_id):
                    running_tasks.append({
                        "task_id": tid,
                        "started_at": task_info.get("started_at"),
                        "progress": task_info.get("progress", {})
                    })
        
        concurrent_info = {
            "other_running_tasks": len(running_tasks),
            "running_tasks": running_tasks[:3],  # Show only first 3
            "note": "This task will process records not currently locked by other tasks"
        }
        
        # Add background task
        background_tasks.add_task(run_filtering_task, task_id, manifest_path)
        
        return FilterResponse(
            success=True,
            message="Filtering task started successfully",
            task_id=task_id,
            concurrent_info=concurrent_info if running_tasks else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting filter task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start filtering task: {str(e)}"
        )

@app.get("/status/{task_id}", response_model=StatusResponse)
async def get_task_status(task_id: str):
    """Get status of a filtering task."""
    task_info = task_manager.get_task(task_id)
    
    if not task_info:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    return StatusResponse(
        task_id=task_id,
        status=task_info["status"],
        progress=task_info.get("progress"),
        result=task_info.get("result"),
        error=task_info.get("error"),
        started_at=task_info.get("started_at"),
        completed_at=task_info.get("completed_at")
    )

@app.get("/stats", response_model=StatsResponse)
async def get_manifest_statistics(
    manifest_path: Optional[str] = Query(
        default=None,
        description="Path to manifest.json file. If not provided, uses default location."
    )
):
    """Get statistics from the manifest file."""
    try:
        # Validate manifest path
        manifest_path = validate_manifest_path(manifest_path)
        
        # Get statistics
        stats = get_manifest_stats(manifest_path)
        
        return StatsResponse(
            manifest_path=manifest_path,
            **stats
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get statistics: {str(e)}"
        )

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
                "status": task_info["status"],
                "started_at": task_info.get("started_at"),
                "completed_at": task_info.get("completed_at"),
                "progress": task_info.get("progress")
            })
    
    return {"tasks": tasks}

@app.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """Cancel or remove a task (Note: running tasks cannot be stopped, only removed from tracking)."""
    task_info = task_manager.get_task(task_id)
    
    if not task_info:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )
    
    with task_manager.lock:
        if task_id in task_manager.tasks:
            del task_manager.tasks[task_id]
    
    return {"message": f"Task {task_id} removed from tracking"}

@app.get("/locks")
async def get_locked_records():
    """Get information about currently locked records."""
    locked_records = record_lock_manager.get_locked_records()
    
    # Get task information for each locked record
    lock_info = []
    for video_id, task_id in locked_records.items():
        task_info = task_manager.get_task(task_id)
        lock_info.append({
            "video_id": video_id,
            "locked_by_task": task_id,
            "task_status": task_info.get("status", "unknown") if task_info else "task_not_found",
            "task_started_at": task_info.get("started_at") if task_info else None
        })
    
    return {
        "total_locked_records": len(locked_records),
        "locked_records": lock_info
    }

# =================================================================
# STARTUP EVENT
# =================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize the API on startup."""
    logger.info("YouTube Output Filterer API starting up...")
    
    # Clean up old tasks
    task_manager.cleanup_old_tasks()
    
    logger.info("API startup completed")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown."""
    logger.info("YouTube Output Filterer API shutting down...")

# =================================================================
# MAIN FUNCTION FOR DIRECT EXECUTION
# =================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("Starting YouTube Output Filterer API...")
    print("=" * 50)
    print("API Documentation: http://localhost:8000/docs")
    print("Health Check: http://localhost:8000/health")
    print("Statistics: http://localhost:8000/stats")
    print("=" * 50)
    
    uvicorn.run(
        "api_youtube_filterer:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )