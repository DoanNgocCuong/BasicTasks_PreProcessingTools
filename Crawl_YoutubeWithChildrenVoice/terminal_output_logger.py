#!/usr/bin/env python3
"""
Terminal Output Logger for YouTube Video Crawler

This module provides comprehensive logging of all terminal output during the crawling process,
creating timestamped logs similar to collection reports for debugging and analysis purposes.

Author: Le Hoang Minh
"""

import sys
import os
import io
from datetime import datetime
from pathlib import Path
from typing import TextIO, Optional
import contextlib


class TerminalOutputLogger:
    """
    Captures and logs all terminal output to timestamped files.
    
    This class intercepts stdout and stderr to create comprehensive logs
    of the entire crawling process, including all print statements,
    error messages, and progress indicators.
    """
    
    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the terminal output logger.
        
        Args:
            base_dir (str, optional): Base directory for log files. 
                                    Defaults to script directory.
        """
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(self.base_dir, 'youtube_url_outputs')
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_filename = f"{timestamp}_terminal_output.log"
        self.log_filepath = os.path.join(self.output_dir, self.log_filename)
        
        # Store original stdout and stderr
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr
        
        # Create log file handle
        self.log_file: Optional[TextIO] = None
        
        # Statistics tracking
        self.start_time = None
        self.end_time = None
        self.total_lines_logged = 0
        self.error_lines_logged = 0
        
        # Buffer for capturing output
        self.stdout_buffer = io.StringIO()
        self.stderr_buffer = io.StringIO()
        
    def __enter__(self):
        """Enter context manager - start logging."""
        self.start_logging()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - stop logging and generate summary."""
        self.stop_logging()
        self.generate_log_summary()
    
    def start_logging(self):
        """Start capturing terminal output to log file."""
        self.start_time = datetime.now()
        
        try:
            self.log_file = open(self.log_filepath, 'w', encoding='utf-8', buffering=1)
            
            # Write log header
            self._write_log_header()
            
            # Replace stdout and stderr with custom writers
            sys.stdout = self._create_tee_writer(self.original_stdout, 'STDOUT')
            sys.stderr = self._create_tee_writer(self.original_stderr, 'STDERR')
            
            print(f"📝 Terminal output logging started: {self.log_filepath}")
            
        except Exception as e:
            print(f"❌ Failed to start terminal logging: {e}")
            self._restore_original_streams()
    
    def stop_logging(self):
        """Stop capturing terminal output and close log file."""
        self.end_time = datetime.now()
        
        try:
            if self.log_file and not self.log_file.closed:
                self._write_log_footer()
                self.log_file.close()
            
            # Restore original stdout and stderr
            self._restore_original_streams()
            
            print(f"📝 Terminal output logging stopped: {self.log_filepath}")
            
        except Exception as e:
            print(f"❌ Error stopping terminal logging: {e}")
    
    def _restore_original_streams(self):
        """Restore original stdout and stderr."""
        sys.stdout = self.original_stdout
        sys.stderr = self.original_stderr
    
    def _write_log_header(self):
        """Write comprehensive header to log file."""
        if not self.log_file:
            return

        start_time_str = self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else 'Unknown'
        process_started_str = self.start_time.isoformat() if self.start_time else 'Unknown'

        header = f"""=== YOUTUBE VIDEO CRAWLER TERMINAL OUTPUT LOG ===
Log generated: {start_time_str}
Process started: {process_started_str}
Log file: {self.log_filename}
Working directory: {os.getcwd()}
Python version: {sys.version}
Platform: {sys.platform}

=== CONFIGURATION INFORMATION ===
Base directory: {self.base_dir}
Output directory: {self.output_dir}
Script path: {__file__}

=== TERMINAL OUTPUT CAPTURE STARTED ===
Format: [TIMESTAMP] [STREAM] MESSAGE
STDOUT = Standard output (normal program output)
STDERR = Standard error (error messages and warnings)

{'=' * 80}

"""
        self.log_file.write(header)
        self.log_file.flush()

    def _write_log_footer(self):
        """Write comprehensive footer with statistics to log file."""
        if not self.log_file:
            return

        duration = self.end_time - self.start_time if self.end_time and self.start_time else None
        duration_str = str(duration).split('.')[0] if duration else "Unknown"
        end_time_str = self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else 'Unknown'
        process_completed_str = self.end_time.isoformat() if self.end_time else 'Unknown'

        footer = f"""

{'=' * 80}
=== TERMINAL OUTPUT CAPTURE ENDED ===

=== LOGGING STATISTICS ===
Process ended: {end_time_str}
Total duration: {duration_str}
Total lines logged: {self.total_lines_logged}
Error lines logged: {self.error_lines_logged}
Normal output lines: {self.total_lines_logged - self.error_lines_logged}

=== LOG FILE INFORMATION ===
Log file: {self.log_filepath}
Log file size: {self._get_file_size_mb():.2f} MB
Encoding: UTF-8

=== PROCESS COMPLETION SUMMARY ===
Log capture completed successfully at: {process_completed_str}
This log contains the complete terminal output from the YouTube video crawler process.

=== END OF LOG ===
"""
        self.log_file.write(footer)
        self.log_file.flush()
    
    def _get_file_size_mb(self) -> float:
        """Get current log file size in MB."""
        try:
            if os.path.exists(self.log_filepath):
                size_bytes = os.path.getsize(self.log_filepath)
                return size_bytes / (1024 * 1024)
        except Exception:
            pass
        return 0.0
    
    def _create_tee_writer(self, original_stream, stream_name: str):
        """Create a writer that outputs to both original stream and log file."""
        
        class TeeWriter:
            def __init__(self, original, log_file, stream_name, logger):
                self.original = original
                self.log_file = log_file
                self.stream_name = stream_name
                self.logger = logger
            
            def write(self, text):
                # Write to original stream
                self.original.write(text)
                self.original.flush()
                
                # Write to log file with timestamp
                if self.log_file and not self.log_file.closed and text.strip():
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    log_line = f"[{timestamp}] [{self.stream_name}] {text}"
                    self.log_file.write(log_line)
                    self.log_file.flush()
                    
                    # Update statistics
                    self.logger.total_lines_logged += text.count('\n')
                    if self.stream_name == 'STDERR':
                        self.logger.error_lines_logged += text.count('\n')
                
                return len(text)
            
            def flush(self):
                self.original.flush()
                if self.log_file and not self.log_file.closed:
                    self.log_file.flush()
            
            def __getattr__(self, name):
                return getattr(self.original, name)
        
        return TeeWriter(original_stream, self.log_file, stream_name, self)
    
    def generate_log_summary(self):
        """Generate a summary report of the logging session."""
        try:
            summary_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_terminal_log_summary.txt"
            summary_filepath = os.path.join(self.output_dir, summary_filename)
            
            duration = self.end_time - self.start_time if self.end_time and self.start_time else None
            duration_str = str(duration).split('.')[0] if duration else "Unknown"
            
            summary_content = f"""=== TERMINAL OUTPUT LOG SUMMARY ===
Summary generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== LOG SESSION INFORMATION ===
Session start: {self.start_time.strftime('%Y-%m-%d %H:%M:%S') if self.start_time else 'Unknown'}
Session end: {self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else 'Unknown'}
Total duration: {duration_str}

=== LOG FILE DETAILS ===
Log file: {self.log_filename}
Full path: {self.log_filepath}
File size: {self._get_file_size_mb():.2f} MB

=== LOGGING STATISTICS ===
Total lines logged: {self.total_lines_logged}
Error lines logged: {self.error_lines_logged}
Normal output lines: {self.total_lines_logged - self.error_lines_logged}
Error ratio: {(self.error_lines_logged / max(self.total_lines_logged, 1) * 100):.1f}%

=== USAGE INSTRUCTIONS ===
The complete terminal output log can be found at:
{self.log_filepath}

This log contains timestamped entries for all console output during the crawler execution.
Use this log for:
- Debugging issues and errors
- Performance analysis
- Process flow understanding
- Error pattern identification

=== END OF SUMMARY ===
"""
            
            with open(summary_filepath, 'w', encoding='utf-8') as f:
                f.write(summary_content)
                
            print(f"📊 Terminal log summary generated: {summary_filepath}")
            
        except Exception as e:
            print(f"❌ Failed to generate log summary: {e}")
    
    def get_log_filepath(self) -> str:
        """Get the path to the current log file."""
        return self.log_filepath
    
    def get_log_statistics(self) -> dict:
        """Get current logging statistics."""
        return {
            'log_filepath': self.log_filepath,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'total_lines_logged': self.total_lines_logged,
            'error_lines_logged': self.error_lines_logged,
            'file_size_mb': self._get_file_size_mb()
        }


@contextlib.contextmanager
def capture_terminal_output(base_dir: Optional[str] = None):
    """
    Context manager for easily capturing terminal output.
    
    Usage:
        with capture_terminal_output() as logger:
            # Your code here
            print("This will be logged")
            # Logger automatically stops and generates summary on exit
    
    Args:
        base_dir (str, optional): Base directory for log files
        
    Yields:
        TerminalOutputLogger: The logger instance
    """
    logger = TerminalOutputLogger(base_dir)
    try:
        logger.start_logging()
        yield logger
    finally:
        logger.stop_logging()
        logger.generate_log_summary()


def main():
    """Demo and test function for TerminalOutputLogger."""
    print("Testing TerminalOutputLogger...")
    
    with capture_terminal_output() as logger:
        print("✅ This is a normal message")
        print("ℹ️ This is an info message")
        print("⚠️ This is a warning message")
        print("❌ This is an error message", file=sys.stderr)
        
        # Simulate some processing
        import time
        for i in range(3):
            print(f"🔄 Processing step {i+1}/3...")
            time.sleep(0.1)
        
        print("✅ Test completed successfully")
    
    print("TerminalOutputLogger test finished!")


if __name__ == "__main__":
    main()
