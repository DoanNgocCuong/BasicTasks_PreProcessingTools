"""
File Manager - Centralized file operations

This module provides utilities for file operations, manifest management,
and directory handling throughout the crawler system.
"""

import json
import shutil
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import time

from .output_manager import get_output_manager


class FileManager:
    """
    Centralized file operations for the crawler system.

    Handles manifest files, temporary files, backups, and general file I/O.
    """

    def __init__(self, base_dir: Path):
        """
        Initialize file manager.

        Args:
            base_dir: Base directory for all file operations
        """
        self.base_dir = base_dir
        self.output = get_output_manager()

        # Define output directories based on config
        from ..config import get_config
        config = get_config()
        self.url_outputs_dir = config.output.url_outputs_dir
        self.audio_outputs_dir = config.output.audio_outputs_dir
        self.final_audio_dir = config.output.final_audio_dir
        # Backup directories
        self.url_backups_dir = config.output.url_backups_dir
        self.audio_backups_dir = config.output.audio_backups_dir
        self.final_audio_backups_dir = config.output.final_audio_backups_dir

    def ensure_directories(self, *dirs: Path) -> None:
        """Ensure all specified directories exist, including backup directories."""
        all_dirs = list(dirs) + [
            self.url_backups_dir,
            self.audio_backups_dir,
            self.final_audio_backups_dir
        ]
        for dir_path in all_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    def create_backup(self, file_path: Path, suffix: Optional[str] = None) -> Path:
        """
        Create a backup of a file with timestamp in the appropriate backup directory.

        Args:
            file_path: Path to the file to backup
            suffix: Optional suffix for backup filename

        Returns:
            Path to the backup file
        """
        if not file_path.exists():
            return file_path

        # Determine the appropriate backup directory based on file location
        backup_dir = self._get_backup_directory(file_path)

        # Ensure backup directory exists
        backup_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if suffix:
            backup_name = f"{file_path.stem}_backup_{suffix}_{timestamp}{file_path.suffix}"
        else:
            backup_name = f"{file_path.stem}_backup_{timestamp}{file_path.suffix}"

        backup_path = backup_dir / backup_name

        try:
            shutil.copy2(file_path, backup_path)
            self.output.debug(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            self.output.warning(f"Failed to create backup of {file_path}: {e}")
            return file_path

    def _get_backup_directory(self, file_path: Path) -> Path:
        """
        Determine the appropriate backup directory for a file.

        Args:
            file_path: Path to the file

        Returns:
            Path to the backup directory
        """
        # Resolve to absolute paths for comparison
        abs_file_path = file_path.resolve()
        abs_url_outputs = self.url_outputs_dir.resolve()
        abs_audio_outputs = self.audio_outputs_dir.resolve()
        abs_final_audio = self.final_audio_dir.resolve()

        # Check which output directory the file belongs to
        if abs_file_path.is_relative_to(abs_url_outputs):
            return self.url_backups_dir
        elif abs_file_path.is_relative_to(abs_audio_outputs):
            return self.audio_backups_dir
        elif abs_file_path.is_relative_to(abs_final_audio):
            return self.final_audio_backups_dir
        else:
            # Default to a general backups directory in the base output dir
            return self.base_dir / "backups"

    def load_json(self, file_path: Path, default: Any = None) -> Any:
        """
        Load JSON data from file.

        Args:
            file_path: Path to JSON file
            default: Default value if file doesn't exist or is invalid

        Returns:
            Loaded JSON data or default value
        """
        if not file_path.exists():
            return default

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.output.warning(f"Failed to load JSON from {file_path}: {e}")
            return default

    def save_json(self, file_path: Path, data: Any, indent: int = 2) -> bool:
        """
        Save data to JSON file atomically.

        Args:
            file_path: Path to save JSON file
            data: Data to save
            indent: JSON indentation level

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create backup if file exists
            if file_path.exists():
                self.create_backup(file_path)

            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write to temporary file first for atomic operation
            temp_file = file_path.with_suffix(file_path.suffix + '.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)

            # Atomically move temp file to final location
            temp_file.replace(file_path)

            self.output.debug(f"Saved JSON atomically to {file_path}")
            return True
        except Exception as e:
            self.output.error(f"Failed to save JSON to {file_path}: {e}")
            # Clean up temp file if it exists
            temp_file = file_path.with_suffix(file_path.suffix + '.tmp')
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except Exception:
                    pass
            return False

    def load_text_file(self, file_path: Path, default: str = "") -> str:
        """
        Load text content from file.

        Args:
            file_path: Path to text file
            default: Default content if file doesn't exist

        Returns:
            File content or default value
        """
        if not file_path.exists():
            return default

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.output.warning(f"Failed to load text from {file_path}: {e}")
            return default

    def save_text_file(self, file_path: Path, content: str) -> bool:
        """
        Save text content to file.

        Args:
            file_path: Path to save text file
            content: Text content to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.output.debug(f"Saved text to {file_path}")
            return True
        except Exception as e:
            self.output.error(f"Failed to save text to {file_path}: {e}")
            return False

    def append_text_file(self, file_path: Path, content: str) -> bool:
        """
        Append text content to file.

        Args:
            file_path: Path to text file
            content: Text content to append

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(content)

            return True
        except Exception as e:
            self.output.error(f"Failed to append text to {file_path}: {e}")
            return False

    def list_files(self, directory: Path, pattern: str = "*") -> List[Path]:
        """
        List files in directory matching pattern.

        Args:
            directory: Directory to list files from
            pattern: Glob pattern to match files

        Returns:
            List of matching file paths
        """
        if not directory.exists():
            return []

        try:
            return list(directory.glob(pattern))
        except Exception as e:
            self.output.warning(f"Failed to list files in {directory}: {e}")
            return []

    def get_file_size(self, file_path: Path) -> Optional[int]:
        """
        Get file size in bytes.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes or None if error
        """
        try:
            return file_path.stat().st_size
        except Exception:
            return None

    def cleanup_temp_files(self, temp_dir: Path, max_age_hours: int = 24) -> int:
        """
        Clean up old temporary files.

        Args:
            temp_dir: Temporary directory to clean
            max_age_hours: Maximum age of files to keep

        Returns:
            Number of files cleaned up
        """
        if not temp_dir.exists():
            return 0

        cleaned = 0
        cutoff_time = datetime.now().timestamp() - (max_age_hours * 3600)

        try:
            for file_path in temp_dir.glob("*"):
                if file_path.is_file():
                    try:
                        file_time = file_path.stat().st_mtime
                        if file_time < cutoff_time:
                            file_path.unlink()
                            cleaned += 1
                    except Exception:
                        continue

            if cleaned > 0:
                self.output.debug(f"Cleaned up {cleaned} temporary files from {temp_dir}")

        except Exception as e:
            self.output.warning(f"Failed to cleanup temp files in {temp_dir}: {e}")

        return cleaned

    def create_temp_file(self, suffix: str = "", prefix: str = "tmp_") -> Path:
        """
        Create a temporary file.

        Args:
            suffix: File suffix/extension
            prefix: File prefix

        Returns:
            Path to temporary file
        """
        fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix)
        # Close the file descriptor as we just need the path
        import os
        os.close(fd)
        return Path(path)

    def create_temp_dir(self, suffix: str = "", prefix: str = "tmp_") -> Path:
        """
        Create a temporary directory.

        Args:
            suffix: Directory suffix
            prefix: Directory prefix

        Returns:
            Path to temporary directory
        """
        return Path(tempfile.mkdtemp(suffix=suffix, prefix=prefix))


class ManifestManager:
    """
    Manager for manifest files that track collected videos and audio files.
    """

    def __init__(self, manifest_path: Path, file_manager: FileManager):
        """
        Initialize manifest manager.

        Args:
            manifest_path: Path to manifest file
            file_manager: File manager instance
        """
        self.manifest_path = manifest_path
        self.file_manager = file_manager
        self.output = get_output_manager()
        self._lock_file = manifest_path.with_suffix(manifest_path.suffix + '.lock')
        self._lock_timeout = 30  # seconds

    def acquire_lock(self) -> bool:
        """
        Acquire a lock on the manifest file.

        Returns:
            True if lock acquired, False otherwise
        """
        start_time = time.time()
        while time.time() - start_time < self._lock_timeout:
            try:
                # Try to create lock file exclusively
                self._lock_file.touch(exist_ok=False)
                self.output.debug(f"Acquired manifest lock: {self._lock_file}")
                return True
            except FileExistsError:
                # Lock file exists, wait and retry
                time.sleep(0.1)
                continue
            except Exception as e:
                self.output.warning(f"Failed to acquire manifest lock: {e}")
                return False

        self.output.warning(f"Timeout acquiring manifest lock after {self._lock_timeout}s")
        return False

    def release_lock(self) -> None:
        """Release the manifest lock."""
        try:
            if self._lock_file.exists():
                self._lock_file.unlink()
                self.output.debug(f"Released manifest lock: {self._lock_file}")
        except Exception as e:
            self.output.warning(f"Failed to release manifest lock: {e}")

    def load_manifest(self) -> Dict[str, Any]:
        """
        Load manifest data from file.

        Returns:
            Manifest data dictionary
        """
        data = self.file_manager.load_json(self.manifest_path, {"records": []})
        if "records" not in data:
            data["records"] = []
        return data

    def save_manifest(self, data: Dict[str, Any]) -> bool:
        """
        Save manifest data to file.

        Args:
            data: Manifest data to save

        Returns:
            True if successful
        """
        return self.file_manager.save_json(self.manifest_path, data)

    def add_record(self, record: Dict[str, Any]) -> bool:
        """
        Add a record to the manifest.

        Args:
            record: Record data to add

        Returns:
            True if successful
        """
        if not self.acquire_lock():
            return False

        try:
            data = self.load_manifest()
            data["records"].append(record)
            data["total_duration_seconds"] = data.get("total_duration_seconds", 0.0) + record.get("duration_seconds", 0.0)
            return self.save_manifest(data)
        finally:
            self.release_lock()

    def find_record(self, video_id: str) -> Optional[Dict[str, Any]]:
        """
        Find a record by video ID.

        Args:
            video_id: Video ID to search for

        Returns:
            Record data or None if not found
        """
        if not self.acquire_lock():
            return None

        try:
            data = self.load_manifest()
            for record in data.get("records", []):
                if record.get("video_id") == video_id:
                    return record
            return None
        finally:
            self.release_lock()

    def remove_record(self, video_id: str) -> bool:
        """
        Remove a record by video ID.

        Args:
            video_id: Video ID to remove

        Returns:
            True if record was found and removed
        """
        if not self.acquire_lock():
            return False

        try:
            data = self.load_manifest()
            original_count = len(data.get("records", []))

            data["records"] = [
                record for record in data.get("records", [])
                if record.get("video_id") != video_id
            ]

            if len(data["records"]) < original_count:
                return self.save_manifest(data)
            return False
        finally:
            self.release_lock()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get manifest statistics.

        Returns:
            Statistics dictionary
        """
        if not self.acquire_lock():
            return {}

        try:
            data = self.load_manifest()
            records = data.get("records", [])

            return {
                "total_records": len(records),
                "total_duration_seconds": data.get("total_duration_seconds", 0.0),
                "total_duration_minutes": data.get("total_duration_seconds", 0.0) / 60.0,
                "unique_channels": len(set(r.get("channel_title", "") for r in records)),
                "date_created": data.get("date_created", "unknown")
            }
        finally:
            self.release_lock()


# Global file manager instance
_file_manager: Optional[FileManager] = None


def get_file_manager() -> FileManager:
    """Get the global file manager instance."""
    global _file_manager
    if _file_manager is None:
        # Get config to determine base directory
        from ..config import get_config
        config = get_config()
        _file_manager = FileManager(config.output.base_dir)
    return _file_manager


def set_file_manager(manager: FileManager) -> None:
    """Set the global file manager instance."""
    global _file_manager
    _file_manager = manager