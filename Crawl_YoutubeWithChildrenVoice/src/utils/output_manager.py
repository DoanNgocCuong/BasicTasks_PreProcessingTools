"""
Output Manager - Centralized logging and user interface

This module provides a centralized system for all output operations,
including console logging, progress tracking, and user feedback.
"""

import sys
import time
from datetime import datetime
from enum import Enum
from typing import List, Optional, TextIO
from pathlib import Path


class LogLevel(Enum):
    """Logging levels for different types of messages."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


class OutputManager:
    """
    Centralized output management for all print statements and user feedback.

    This class handles all console output, progress tracking, and user interface
    elements in a consistent, configurable way.
    """

    def __init__(self, debug_mode: bool = False, output_file: Optional[Path] = None):
        """
        Initialize the output manager.

        Args:
            debug_mode: Whether to show debug messages
            output_file: Optional file to write output to
        """
        self.debug_mode = debug_mode
        self.output_file = output_file
        self.start_time = time.time()
        self.last_progress_time = 0.0

        # Open output file if specified
        self.file_handle: Optional[TextIO] = None
        if output_file:
            self.file_handle = open(output_file, 'a', encoding='utf-8')

    def __del__(self):
        """Clean up file handle on destruction."""
        if self.file_handle:
            self.file_handle.close()

    def _write(self, message: str) -> None:
        """Write message to console and optionally to file."""
        # Write to console
        print(message)

        # Write to file if configured
        if self.file_handle:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.file_handle.write(f"[{timestamp}] {message}\n")
            self.file_handle.flush()

    def _format_message(self, level: LogLevel, message: str) -> str:
        """Format a message with appropriate prefix and styling."""
        prefixes = {
            LogLevel.DEBUG: "🔍 DEBUG:",
            LogLevel.INFO: "ℹ️",
            LogLevel.SUCCESS: "✅",
            LogLevel.WARNING: "⚠️",
            LogLevel.ERROR: "❌"
        }

        prefix = prefixes.get(level, "")
        if prefix:
            return f"{prefix} {message}"
        return message

    def debug(self, message: str) -> None:
        """Log a debug message."""
        if self.debug_mode:
            formatted = self._format_message(LogLevel.DEBUG, message)
            self._write(formatted)

    def info(self, message: str) -> None:
        """Log an info message."""
        formatted = self._format_message(LogLevel.INFO, message)
        self._write(formatted)

    def success(self, message: str) -> None:
        """Log a success message."""
        formatted = self._format_message(LogLevel.SUCCESS, message)
        self._write(formatted)

    def warning(self, message: str) -> None:
        """Log a warning message."""
        formatted = self._format_message(LogLevel.WARNING, message)
        self._write(formatted)

    def error(self, message: str) -> None:
        """Log an error message."""
        formatted = self._format_message(LogLevel.ERROR, message)
        self._write(formatted)

    def set_level(self, level: str) -> None:
        """Set the logging level (enable/disable debug mode)."""
        self.debug_mode = level.upper() == "DEBUG"

    def progress(self, message: str) -> None:
        """Log a progress message."""
        formatted = f"🔍 {message}"
        self._write(formatted)
        self.last_progress_time = time.time()

    def timing(self, message: str, duration: float) -> None:
        """Log a timing message."""
        formatted = f"⏱️  {message}: {duration:.2f}s"
        self._write(formatted)

    def result(self, message: str, is_positive: bool = True) -> None:
        """Log a result message."""
        symbol = "✓" if is_positive else "✗"
        self._write(f"{symbol} {message}")

    def header(self, title: str, width: int = 60) -> None:
        """Print a formatted header."""
        separator = "=" * width
        self._write(separator)
        self._write(title)
        self._write(separator)

    def sub_header(self, title: str, width: int = 50) -> None:
        """Print a formatted sub-header."""
        separator = "=" * width
        self._write(f"\n{separator}")
        self._write(title)
        self._write(separator)

    def section_divider(self, width: int = 50) -> None:
        """Print a section divider."""
        self._write("-" * width)

    def enumerated_list(self, items: List[str], title: Optional[str] = None) -> None:
        """Print an enumerated list."""
        if title:
            self._write(f"\n📋 {title}")
        for i, item in enumerate(items, 1):
            self._write(f"  {i}. '{item}'")

    def statistics(self, stats_dict: dict) -> None:
        """Print statistics in a formatted way."""
        for key, value in stats_dict.items():
            self._write(f"  - {key}: {value}")

    def progress_bar(self, current: int, total: int, prefix: str = "Progress") -> None:
        """Display a progress bar."""
        if total == 0:
            return

        percentage = (current / total) * 100
        bar_length = 40
        filled_length = int(bar_length * current / total)
        bar = "█" * filled_length + "░" * (bar_length - filled_length)

        message = f"\r{prefix}: [{bar}] {current}/{total} ({percentage:.1f}%)"
        print(message, end="", flush=True)

        if current == total:
            print()  # New line when complete

    def elapsed_time(self) -> float:
        """Get elapsed time since initialization."""
        return time.time() - self.start_time

    def print_session_summary(self, session_stats: dict) -> None:
        """Print a comprehensive session summary."""
        self.header("SESSION SUMMARY", 60)

        self.info(f"Total runtime: {self.elapsed_time():.2f} seconds")
        self.statistics(session_stats)
        self.section_divider()

    def print_video_summary(self, video_stats: dict) -> None:
        """Print video processing summary."""
        self.sub_header("VIDEO PROCESSING SUMMARY")
        self.statistics(video_stats)

    def print_error_summary(self, errors: List[str]) -> None:
        """Print error summary."""
        if errors:
            self.sub_header("ERROR SUMMARY")
            for error in errors:
                self.error(error)
        else:
            self.success("No errors encountered")

    def flush(self) -> None:
        """Flush any buffered output."""
        if self.file_handle:
            self.file_handle.flush()
        sys.stdout.flush()


# Global output manager instance
_output_manager: Optional[OutputManager] = None


def get_output_manager() -> OutputManager:
    """Get the global output manager instance."""
    global _output_manager
    if _output_manager is None:
        _output_manager = OutputManager()
    return _output_manager


def set_output_manager(manager: OutputManager) -> None:
    """Set the global output manager instance."""
    global _output_manager
    _output_manager = manager