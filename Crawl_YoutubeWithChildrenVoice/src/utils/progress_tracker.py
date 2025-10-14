"""
Progress Tracker - Track and display progress for long-running operations

This module provides utilities for tracking progress of batch operations,
displaying progress bars, and estimating completion times.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Callable, Any, Dict
from enum import Enum
from contextlib import contextmanager

from .output_manager import get_output_manager


class ProgressStatus(Enum):
    """Status of a progress tracking operation."""
    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProgressMetrics:
    """Metrics for tracking progress."""
    total_items: int = 0
    completed_items: int = 0
    failed_items: int = 0
    skipped_items: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    last_update_time: Optional[float] = None

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_items == 0:
            return 100.0
        return (self.completed_items / self.total_items) * 100.0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        processed = self.completed_items + self.failed_items
        if processed == 0:
            return 0.0
        return (self.completed_items / processed) * 100.0

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        if self.start_time is None:
            return 0.0
        end_time = self.end_time or time.time()
        return end_time - self.start_time

    @property
    def estimated_time_remaining(self) -> Optional[float]:
        """Estimate time remaining in seconds."""
        if self.completed_items == 0 or self.start_time is None:
            return None

        avg_time_per_item = self.elapsed_time / self.completed_items
        remaining_items = self.total_items - self.completed_items
        return avg_time_per_item * remaining_items

    @property
    def estimated_completion_time(self) -> Optional[datetime]:
        """Estimate completion datetime."""
        eta = self.estimated_time_remaining
        if eta is None:
            return None
        return datetime.now() + timedelta(seconds=eta)

    @property
    def items_per_second(self) -> float:
        """Calculate processing rate."""
        elapsed = self.elapsed_time
        if elapsed == 0:
            return 0.0
        return self.completed_items / elapsed


class ProgressTracker:
    """
    Track progress of long-running operations with progress bars and metrics.

    Provides real-time progress tracking, ETA calculations, and status reporting
    for batch operations like video downloading, analysis, etc.
    """

    def __init__(self, operation_name: str, total_items: int = 0, show_progress_bar: bool = True):
        """
        Initialize progress tracker.

        Args:
            operation_name: Name of the operation being tracked
            total_items: Total number of items to process
            show_progress_bar: Whether to show progress bars
        """
        self.operation_name = operation_name
        self.show_progress_bar = show_progress_bar
        self.output = get_output_manager()

        self.metrics = ProgressMetrics(total_items=total_items)
        self.status = ProgressStatus.NOT_STARTED
        self.update_callback: Optional[Callable[[ProgressMetrics], None]] = None

    def start(self) -> None:
        """Start tracking progress."""
        self.metrics.start_time = time.time()
        self.metrics.last_update_time = self.metrics.start_time
        self.status = ProgressStatus.RUNNING

        self.output.info(f"Started {self.operation_name} (total: {self.metrics.total_items} items)")

    def update(self, completed: int = 1, failed: int = 0, skipped: int = 0) -> None:
        """
        Update progress counters.

        Args:
            completed: Number of items completed
            failed: Number of items failed
            skipped: Number of items skipped
        """
        self.metrics.completed_items += completed
        self.metrics.failed_items += failed
        self.metrics.skipped_items += skipped
        self.metrics.last_update_time = time.time()

        if self.show_progress_bar:
            self._display_progress_bar()

        if self.update_callback:
            self.update_callback(self.metrics)

    def set_total(self, total: int) -> None:
        """Update total number of items."""
        self.metrics.total_items = total

    def complete(self) -> None:
        """Mark operation as completed."""
        self.metrics.end_time = time.time()
        self.status = ProgressStatus.COMPLETED

        self._display_final_summary()

    def fail(self, error_message: str = "") -> None:
        """Mark operation as failed."""
        self.metrics.end_time = time.time()
        self.status = ProgressStatus.FAILED

        self.output.error(f"{self.operation_name} failed: {error_message}")

    def pause(self) -> None:
        """Pause progress tracking."""
        self.status = ProgressStatus.PAUSED

    def resume(self) -> None:
        """Resume progress tracking."""
        if self.status == ProgressStatus.PAUSED:
            self.status = ProgressStatus.RUNNING

    def set_update_callback(self, callback: Callable[[ProgressMetrics], None]) -> None:
        """
        Set callback function to be called on progress updates.

        Args:
            callback: Function that takes ProgressMetrics as argument
        """
        self.update_callback = callback

    @contextmanager
    def create_progress_bar(self, total: int, description: str = "", unit: str = "item"):
        """
        Create a progress bar context manager.

        Args:
            total: Total number of items
            description: Description of the operation
            unit: Unit name for items

        Yields:
            Progress bar object with update() method
        """
        # Set total and start tracking
        self.set_total(total)
        self.start()

        class ProgressBar:
            def __init__(self, tracker):
                self.tracker = tracker

            def update(self, n: int = 1):
                self.tracker.update(completed=n)

        progress_bar = ProgressBar(self)

        try:
            yield progress_bar
        finally:
            self.complete()

    def _display_progress_bar(self) -> None:
        """Display progress bar in console."""
        percentage = self.metrics.progress_percentage
        completed = self.metrics.completed_items
        total = self.metrics.total_items

        bar_length = 40
        filled_length = int(bar_length * completed / max(total, 1))
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        eta_str = ""
        if self.metrics.estimated_time_remaining:
            eta_seconds = int(self.metrics.estimated_time_remaining)
            if eta_seconds < 60:
                eta_str = f" ETA: {eta_seconds}s"
            elif eta_seconds < 3600:
                eta_str = f" ETA: {eta_seconds // 60}m {eta_seconds % 60}s"
            else:
                eta_str = f" ETA: {eta_seconds // 3600}h {(eta_seconds % 3600) // 60}m"

        rate_str = f" ({self.metrics.items_per_second:.1f} items/s)"

        message = f"\r🔄 {self.operation_name}: [{bar}] {completed}/{total} ({percentage:.1f}%){rate_str}{eta_str}"
        print(message, end="", flush=True)

        if completed >= total:
            print()  # New line when complete

    def _display_final_summary(self) -> None:
        """Display final completion summary."""
        elapsed = self.metrics.elapsed_time
        rate = self.metrics.items_per_second

        self.output.success(f"Completed {self.operation_name}")
        self.output.info(f"Processed {self.metrics.completed_items} items in {elapsed:.2f}s")
        self.output.info(f"Average rate: {rate:.2f} items/second")

        if self.metrics.failed_items > 0:
            self.output.warning(f"Failed items: {self.metrics.failed_items}")

        if self.metrics.skipped_items > 0:
            self.output.info(f"Skipped items: {self.metrics.skipped_items}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive progress summary.

        Returns:
            Dictionary with progress statistics
        """
        return {
            "operation": self.operation_name,
            "status": self.status.value,
            "total_items": self.metrics.total_items,
            "completed_items": self.metrics.completed_items,
            "failed_items": self.metrics.failed_items,
            "skipped_items": self.metrics.skipped_items,
            "progress_percentage": self.metrics.progress_percentage,
            "success_rate": self.metrics.success_rate,
            "elapsed_time": self.metrics.elapsed_time,
            "items_per_second": self.metrics.items_per_second,
            "estimated_time_remaining": self.metrics.estimated_time_remaining,
            "estimated_completion_time": self.metrics.estimated_completion_time.isoformat() if self.metrics.estimated_completion_time else None,
        }


class BatchProgressTracker:
    """
    Track progress of multiple concurrent batch operations.
    """

    def __init__(self, operation_name: str):
        """
        Initialize batch progress tracker.

        Args:
            operation_name: Name of the overall batch operation
        """
        self.operation_name = operation_name
        self.trackers: Dict[str, ProgressTracker] = {}
        self.output = get_output_manager()

    def add_tracker(self, tracker_id: str, tracker: ProgressTracker) -> None:
        """
        Add a progress tracker to the batch.

        Args:
            tracker_id: Unique identifier for the tracker
            tracker: ProgressTracker instance
        """
        self.trackers[tracker_id] = tracker

    def get_tracker(self, tracker_id: str) -> Optional[ProgressTracker]:
        """
        Get a specific progress tracker.

        Args:
            tracker_id: Tracker identifier

        Returns:
            ProgressTracker instance or None
        """
        return self.trackers.get(tracker_id)

    def get_overall_progress(self) -> ProgressMetrics:
        """
        Calculate overall progress across all trackers.

        Returns:
            Combined progress metrics
        """
        if not self.trackers:
            return ProgressMetrics()

        total_items = sum(t.metrics.total_items for t in self.trackers.values())
        completed_items = sum(t.metrics.completed_items for t in self.trackers.values())
        failed_items = sum(t.metrics.failed_items for t in self.trackers.values())
        skipped_items = sum(t.metrics.skipped_items for t in self.trackers.values())

        # Use earliest start time and latest end time
        start_times = [t.metrics.start_time for t in self.trackers.values() if t.metrics.start_time]
        end_times = [t.metrics.end_time for t in self.trackers.values() if t.metrics.end_time]

        start_time = min(start_times) if start_times else None
        end_time = max(end_times) if end_times else None

        return ProgressMetrics(
            total_items=total_items,
            completed_items=completed_items,
            failed_items=failed_items,
            skipped_items=skipped_items,
            start_time=start_time,
            end_time=end_time
        )

    def display_overall_progress(self) -> None:
        """Display overall progress summary."""
        overall = self.get_overall_progress()

        self.output.sub_header(f"OVERALL {self.operation_name.upper()} PROGRESS")
        self.output.info(f"Total items: {overall.total_items}")
        self.output.info(f"Completed: {overall.completed_items}")
        self.output.info(f"Failed: {overall.failed_items}")
        self.output.info(f"Skipped: {overall.skipped_items}")
        self.output.info(f"Progress: {overall.progress_percentage:.1f}%")
        self.output.info(f"Success rate: {overall.success_rate:.1f}%")

        if overall.elapsed_time > 0:
            self.output.info(f"Elapsed time: {overall.elapsed_time:.2f}s")
            self.output.info(f"Rate: {overall.items_per_second:.2f} items/s")


# Global progress tracker instance
_progress_tracker_instance: Optional[ProgressTracker] = None


def get_progress_tracker() -> ProgressTracker:
    """Get the global progress tracker instance."""
    global _progress_tracker_instance
    if _progress_tracker_instance is None:
        _progress_tracker_instance = ProgressTracker("Global Operation")
    return _progress_tracker_instance


def set_progress_tracker(tracker: ProgressTracker) -> None:
    """Set the global progress tracker instance."""
    global _progress_tracker_instance
    _progress_tracker_instance = tracker