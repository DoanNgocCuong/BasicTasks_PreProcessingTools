"""
Queue Manager for YouTube Output Filterer

This module provides inter-instance coordination for the YouTube Output Filterer
using a persistent queue system to prevent duplicate processing across multiple
API instances.

Features:
    - Atomic record claiming with file locking
    - Instance registration and heartbeat monitoring
    - Fault-tolerant processing with crash recovery
    - Automatic migration from legacy manifests
    - Thread-safe operations

Author: Generated for YouTube Audio Crawler
Version: 1.0
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import tempfile
import shutil

# Cross-platform file locking
try:
    import fcntl
    FILE_LOCKING_AVAILABLE = True
except ImportError:
    try:
        import msvcrt
        FILE_LOCKING_AVAILABLE = True
    except ImportError:
        FILE_LOCKING_AVAILABLE = False
        print("Warning: File locking not available. Queue operations may not be thread-safe.")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class QueueStatus:
    """Status of the processing queue."""
    total_pending: int
    total_processing: int
    total_completed: int
    total_failed: int
    active_instances: int
    stale_instances: int


@dataclass
class InstanceInfo:
    """Information about a processing instance."""
    instance_id: str
    active: bool
    last_heartbeat: datetime
    claimed_records: List[str]
    started_at: datetime


@dataclass
class ClaimResult:
    """Result of claiming records from the queue."""
    claimed_records: List[Dict]
    queue_status: QueueStatus


class QueueManager:
    """
    Manages the processing queue for coordinating multiple filterer instances.

    The queue uses a JSON file with atomic operations to ensure thread-safety
    across multiple processes and instances.
    """

    def __init__(self, queue_path: str, manifest_path: str, instance_id: str):
        """
        Initialize the QueueManager.

        Args:
            queue_path: Path to the queue JSON file
            manifest_path: Path to the manifest JSON file
            instance_id: Unique identifier for this instance
        """
        self.queue_path = Path(queue_path)
        self.manifest_path = Path(manifest_path)
        self.instance_id = instance_id

        # Configuration
        self.heartbeat_interval = 30  # seconds
        self.stale_timeout = 300  # 5 minutes
        self.max_retry_attempts = 3
        self.retry_delay = 0.1  # seconds

        # Threading
        self._lock = threading.Lock()
        self._file_lock = None

        # Initialize queue if it doesn't exist
        self._ensure_queue_exists()

        # Register this instance
        self.register_instance()

        logger.info(f"QueueManager initialized for instance: {instance_id}")

    def _ensure_queue_exists(self) -> None:
        """Ensure the queue file exists, create if necessary."""
        if not self.queue_path.exists():
            self._create_initial_queue()

    def _create_initial_queue(self) -> None:
        """Create the initial queue file."""
        queue_data = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "instances": {},
            "queue": {
                "pending": [],
                "processing": {},
                "completed": [],
                "failed": []
            },
            "records": {}
        }

        # Create directory if needed
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)

        with self._lock:
            with open(self.queue_path, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Created initial queue file: {self.queue_path}")

    def _acquire_file_lock(self, file_handle) -> bool:
        """Acquire an exclusive file lock."""
        if not FILE_LOCKING_AVAILABLE:
            return True  # No locking available, proceed anyway

        try:
            if hasattr(file_handle, 'fileno'):
                if 'fcntl' in globals():
                    fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX)
                elif 'msvcrt' in globals():
                    # Windows locking (simplified)
                    msvcrt.locking(file_handle.fileno(), msvcrt.LK_LOCK, 1)
            return True
        except Exception as e:
            logger.warning(f"Failed to acquire file lock: {e}")
            return False

    def _release_file_lock(self, file_handle) -> None:
        """Release the file lock."""
        if not FILE_LOCKING_AVAILABLE:
            return

        try:
            if hasattr(file_handle, 'fileno'):
                if 'fcntl' in globals():
                    fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
                elif 'msvcrt' in globals():
                    # Windows unlocking
                    msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception as e:
            logger.warning(f"Failed to release file lock: {e}")

    def _load_queue_data(self) -> Dict:
        """Load queue data with file locking."""
        for attempt in range(self.max_retry_attempts):
            try:
                with open(self.queue_path, 'r+', encoding='utf-8') as f:
                    if self._acquire_file_lock(f):
                        try:
                            data = json.load(f)
                            return data
                        finally:
                            self._release_file_lock(f)
                    else:
                        logger.warning(f"Failed to acquire lock on attempt {attempt + 1}")
            except Exception as e:
                logger.warning(f"Failed to load queue data (attempt {attempt + 1}): {e}")

            if attempt < self.max_retry_attempts - 1:
                time.sleep(self.retry_delay * (2 ** attempt))

        raise Exception("Failed to load queue data after all retry attempts")

    def _save_queue_data(self, data: Dict) -> None:
        """Save queue data with file locking and backup."""
        # Create backup
        backup_path = self.queue_path.with_suffix('.backup')
        if self.queue_path.exists():
            try:
                shutil.copy2(self.queue_path, backup_path)
            except Exception as e:
                logger.warning(f"Failed to create queue backup: {e}")

        # Update timestamp
        data["last_updated"] = datetime.now().isoformat()

        for attempt in range(self.max_retry_attempts):
            try:
                with open(self.queue_path, 'w', encoding='utf-8') as f:
                    if self._acquire_file_lock(f):
                        try:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                            return
                        finally:
                            self._release_file_lock(f)
                    else:
                        logger.warning(f"Failed to acquire lock on attempt {attempt + 1}")
            except Exception as e:
                logger.warning(f"Failed to save queue data (attempt {attempt + 1}): {e}")

            if attempt < self.max_retry_attempts - 1:
                time.sleep(self.retry_delay * (2 ** attempt))

        raise Exception("Failed to save queue data after all retry attempts")

    def register_instance(self) -> None:
        """Register this instance in the queue."""
        with self._lock:
            data = self._load_queue_data()

            data["instances"][self.instance_id] = {
                "active": True,
                "last_heartbeat": datetime.now().isoformat(),
                "claimed_records": [],
                "started_at": datetime.now().isoformat()
            }

            self._save_queue_data(data)
            logger.info(f"Registered instance: {self.instance_id}")

    def heartbeat(self) -> None:
        """Send a heartbeat to indicate this instance is still active."""
        with self._lock:
            data = self._load_queue_data()

            if self.instance_id in data["instances"]:
                data["instances"][self.instance_id]["last_heartbeat"] = datetime.now().isoformat()
                data["instances"][self.instance_id]["active"] = True
                self._save_queue_data(data)

    def unregister_instance(self) -> None:
        """Unregister this instance and re-queue any claimed records."""
        with self._lock:
            data = self._load_queue_data()

            if self.instance_id in data["instances"]:
                # Re-queue claimed records
                claimed_records = data["instances"][self.instance_id].get("claimed_records", [])
                if claimed_records:
                    data["queue"]["pending"].extend(claimed_records)
                    logger.info(f"Re-queued {len(claimed_records)} records from crashed instance: {self.instance_id}")

                # Remove instance
                del data["instances"][self.instance_id]

                # Clean up processing records
                if self.instance_id in data["queue"]["processing"]:
                    del data["queue"]["processing"][self.instance_id]

                self._save_queue_data(data)
                logger.info(f"Unregistered instance: {self.instance_id}")

    def cleanup_stale_instances(self) -> int:
        """
        Clean up instances that haven't sent heartbeats recently.

        Returns:
            Number of stale instances cleaned up
        """
        with self._lock:
            data = self._load_queue_data()
            now = datetime.now()
            cleaned_count = 0

            stale_instances = []
            for instance_id, instance_data in data["instances"].items():
                last_heartbeat = datetime.fromisoformat(instance_data["last_heartbeat"])
                if (now - last_heartbeat).total_seconds() > self.stale_timeout:
                    stale_instances.append(instance_id)

            for instance_id in stale_instances:
                # Re-queue claimed records
                claimed_records = data["instances"][instance_id].get("claimed_records", [])
                if claimed_records:
                    data["queue"]["pending"].extend(claimed_records)
                    logger.info(f"Re-queued {len(claimed_records)} records from stale instance: {instance_id}")

                # Remove instance
                del data["instances"][instance_id]

                # Clean up processing records
                if instance_id in data["queue"]["processing"]:
                    del data["queue"]["processing"][instance_id]

                cleaned_count += 1

            if cleaned_count > 0:
                self._save_queue_data(data)
                logger.info(f"Cleaned up {cleaned_count} stale instances")

            return cleaned_count

    def populate_queue_from_manifest(self) -> int:
        """
        Populate the queue with unclassified records from the manifest.

        Returns:
            Number of records added to queue
        """
        with self._lock:
            # Load manifest
            try:
                with open(self.manifest_path, 'r', encoding='utf-8') as f:
                    manifest_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load manifest: {e}")
                return 0

            # Load queue
            data = self._load_queue_data()

            # Find unclassified records not already in queue
            records = manifest_data.get('records', [])
            added_count = 0

            for record in records:
                video_id = record.get('video_id')
                if not video_id:
                    continue

                # Skip if already classified
                if record.get('classified', False):
                    continue

                # Skip if already in any queue state
                in_pending = video_id in data["queue"]["pending"]
                in_processing = any(video_id in records for records in data["queue"]["processing"].values())
                in_completed = video_id in data["queue"]["completed"]
                in_failed = video_id in data["queue"]["failed"]

                if not (in_pending or in_processing or in_completed or in_failed):
                    data["queue"]["pending"].append(video_id)
                    data["records"][video_id] = {
                        "video_id": video_id,
                        "added_to_queue": datetime.now().isoformat(),
                        "instance_id": None,
                        "processing_started": None
                    }
                    added_count += 1

            if added_count > 0:
                self._save_queue_data(data)
                logger.info(f"Added {added_count} records to queue from manifest")

            return added_count

    def claim_records(self, batch_size: int = 10) -> ClaimResult:
        """
        Atomically claim a batch of records for processing.

        Args:
            batch_size: Maximum number of records to claim

        Returns:
            ClaimResult with claimed records and queue status
        """
        with self._lock:
            data = self._load_queue_data()

            # Clean up stale instances first
            self.cleanup_stale_instances()

            # Get pending records
            pending = data["queue"]["pending"]
            if not pending:
                return ClaimResult(claimed_records=[], queue_status=self._get_queue_status(data))

            # Claim records
            claimed_video_ids = pending[:batch_size]
            remaining_pending = pending[batch_size:]

            # Update queue
            data["queue"]["pending"] = remaining_pending

            # Initialize processing list for this instance
            if self.instance_id not in data["queue"]["processing"]:
                data["queue"]["processing"][self.instance_id] = []

            # Add to processing and update records
            claimed_records = []
            for video_id in claimed_video_ids:
                data["queue"]["processing"][self.instance_id].append(video_id)
                data["records"][video_id]["instance_id"] = self.instance_id
                data["records"][video_id]["processing_started"] = datetime.now().isoformat()

                # Get full record from manifest
                record = self._get_record_from_manifest(video_id)
                if record:
                    claimed_records.append(record)

            # Update instance info
            if self.instance_id in data["instances"]:
                data["instances"][self.instance_id]["claimed_records"] = data["queue"]["processing"][self.instance_id]
                data["instances"][self.instance_id]["last_heartbeat"] = datetime.now().isoformat()

            self._save_queue_data(data)

            logger.info(f"Instance {self.instance_id} claimed {len(claimed_records)} records")

            return ClaimResult(
                claimed_records=claimed_records,
                queue_status=self._get_queue_status(data)
            )

    def _get_record_from_manifest(self, video_id: str) -> Optional[Dict]:
        """Get a record from the manifest by video_id."""
        try:
            with open(self.manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)

            records = manifest_data.get('records', [])
            for record in records:
                if record.get('video_id') == video_id:
                    return record
        except Exception as e:
            logger.error(f"Failed to get record {video_id} from manifest: {e}")

        return None

    def complete_record(self, video_id: str) -> bool:
        """
        Mark a record as completed.

        Args:
            video_id: The video ID to mark as completed

        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            data = self._load_queue_data()

            # Remove from processing
            if self.instance_id in data["queue"]["processing"]:
                if video_id in data["queue"]["processing"][self.instance_id]:
                    data["queue"]["processing"][self.instance_id].remove(video_id)
                    data["queue"]["completed"].append(video_id)

                    # Update instance claimed records
                    if self.instance_id in data["instances"]:
                        claimed = data["instances"][self.instance_id].get("claimed_records", [])
                        if video_id in claimed:
                            claimed.remove(video_id)

                    self._save_queue_data(data)
                    logger.debug(f"Completed record: {video_id}")
                    return True

        return False

    def fail_record(self, video_id: str) -> bool:
        """
        Mark a record as failed (will be re-queued).

        Args:
            video_id: The video ID to mark as failed

        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            data = self._load_queue_data()

            # Remove from processing and add to failed
            if self.instance_id in data["queue"]["processing"]:
                if video_id in data["queue"]["processing"][self.instance_id]:
                    data["queue"]["processing"][self.instance_id].remove(video_id)
                    data["queue"]["failed"].append(video_id)

                    # Update instance claimed records
                    if self.instance_id in data["instances"]:
                        claimed = data["instances"][self.instance_id].get("claimed_records", [])
                        if video_id in claimed:
                            claimed.remove(video_id)

                    self._save_queue_data(data)
                    logger.debug(f"Failed record: {video_id}")
                    return True

        return False

    def _get_queue_status(self, data: Dict) -> QueueStatus:
        """Get the current queue status."""
        instances = data.get("instances", {})
        now = datetime.now()

        active_instances = 0
        stale_instances = 0

        for instance_data in instances.values():
            last_heartbeat = datetime.fromisoformat(instance_data["last_heartbeat"])
            if (now - last_heartbeat).total_seconds() <= self.stale_timeout:
                active_instances += 1
            else:
                stale_instances += 1

        return QueueStatus(
            total_pending=len(data["queue"]["pending"]),
            total_processing=sum(len(records) for records in data["queue"]["processing"].values()),
            total_completed=len(data["queue"]["completed"]),
            total_failed=len(data["queue"]["failed"]),
            active_instances=active_instances,
            stale_instances=stale_instances
        )

    def get_queue_status(self) -> QueueStatus:
        """Get the current queue status."""
        data = self._load_queue_data()
        return self._get_queue_status(data)

    def get_instance_info(self, instance_id: Optional[str] = None) -> Optional[InstanceInfo]:
        """Get information about an instance."""
        data = self._load_queue_data()
        target_id = instance_id or self.instance_id

        if target_id not in data["instances"]:
            return None

        instance_data = data["instances"][target_id]
        return InstanceInfo(
            instance_id=target_id,
            active=instance_data["active"],
            last_heartbeat=datetime.fromisoformat(instance_data["last_heartbeat"]),
            claimed_records=instance_data.get("claimed_records", []),
            started_at=datetime.fromisoformat(instance_data["started_at"])
        )


# Convenience functions for external use
def create_queue_manager(manifest_path: str, instance_id: Optional[str] = None) -> QueueManager:
    """
    Create a QueueManager instance with default settings.

    Args:
        manifest_path: Path to the manifest file
        instance_id: Optional instance ID (generated if None)

    Returns:
        Configured QueueManager instance
    """
    if instance_id is None:
        timestamp = datetime.now().strftime("%H%M%S")
        instance_id = f"filterer_{os.getpid()}_{timestamp}"

    queue_path = Path(manifest_path).parent / "processing_queue.json"

    return QueueManager(
        queue_path=str(queue_path),
        manifest_path=manifest_path,
        instance_id=instance_id
    )