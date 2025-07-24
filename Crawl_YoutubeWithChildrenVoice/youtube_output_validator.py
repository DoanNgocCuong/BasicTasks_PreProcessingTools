#!/usr/bin/env python3
"""
YouTube URL Validator and Duplicate Checker

This module provides comprehensive validation and analysis tools for YouTube URL collections.
It validates URL formats, detects and reports duplicates, normalizes URLs to standard format,
and generates detailed statistics and cleaned datasets.

Key Features:
    - YouTube URL format validation using regex patterns
    - Duplicate detection and counting across multiple URL formats
    - URL normalization to standard YouTube format
    - Comprehensive validation statistics and reporting
    - Generation of cleaned, deduplicated URL datasets
    - Support for various YouTube URL formats (youtube.com, youtu.be, m.youtube.com)
    - Detailed error reporting for invalid URLs

Supported URL Formats:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID  
    - https://m.youtube.com/watch?v=VIDEO_ID

Output Files:
    - duplicates_report.txt: Detailed duplicate analysis report
    - cleaned_video_urls.txt: Deduplicated, normalized URL list
    - validation_statistics.txt: Comprehensive validation metrics

Use Cases:
    - Quality assurance for YouTube URL datasets
    - Data cleaning and preprocessing for video collections
    - Duplicate detection in large URL collections
    - URL format standardization and normalization
    - Dataset integrity verification

Workflow:
    1. Read URLs from input file
    2. Validate each URL against YouTube patterns
    3. Normalize valid URLs to standard format
    4. Detect duplicates using normalized URLs
    5. Generate comprehensive reports and statistics
    6. Output cleaned, deduplicated dataset

Dependencies:
    - re: For regex pattern matching
    - pathlib: For file path operations
    - collections.Counter: For duplicate counting

Usage:
    python youtube_output_validator.py

Author: Le Hoang Minh
Created: 2025
Version: 1.0
"""
import re
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from collections import Counter
from dataclasses import dataclass


@dataclass
class DuplicateInfo:
    """Data class for duplicate URL information."""
    url: str
    normalized_url: str
    positions: List[int]  # Line positions (0-based) where this URL appears
    count: int

@dataclass
class ValidationResult:
    """Data class for validation results."""
    total_urls: int
    unique_urls: int
    duplicate_count: int
    invalid_urls: int
    duplicates: Dict[str, int]  # Kept for backward compatibility
    invalid_url_list: List[str]
    valid_urls: Set[str]
    duplicate_urls: List[DuplicateInfo]  # Detailed duplicate information with positions


class Config:
    """Configuration for the URL validator."""
    
    def __init__(self):
        # Get the script directory
        self.script_dir = Path(__file__).parent
        
        # Default file paths
        self.default_input_file = self.script_dir / "youtube_url_outputs" / "collected_video_urls.txt"
        self.default_output_dir = self.script_dir / "youtube_url_outputs"
        
        # Output file names
        self.duplicates_report_file = self.default_output_dir / "duplicates_report.txt"
        self.cleaned_urls_file = self.default_output_dir / "cleaned_video_urls.txt"
        self.validation_stats_file = self.default_output_dir / "validation_statistics.txt"
        
        # YouTube URL patterns
        self.youtube_patterns = [
            r'https://www\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
            r'https://youtu\.be/([a-zA-Z0-9_-]{11})',
            r'https://m\.youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})',
        ]
        
        # Compiled regex patterns
        self.compiled_patterns = [re.compile(pattern) for pattern in self.youtube_patterns]


class YouTubeURLValidator:
    """Validator for YouTube URLs with duplicate detection and cleaning."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the validator with configuration."""
        self.config = config or Config()
        
        # Ensure output directory exists
        self.config.default_output_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_video_id(self, url: str) -> str:
        """
        Extract video ID from YouTube URL.
        
        Args:
            url (str): YouTube URL
            
        Returns:
            str: Video ID or empty string if not found
        """
        for pattern in self.config.compiled_patterns:
            match = pattern.search(url.strip())
            if match:
                return match.group(1)
        return ""
    
    def is_valid_youtube_url(self, url: str) -> bool:
        """
        Check if URL is a valid YouTube video URL.
        
        Args:
            url (str): URL to validate
            
        Returns:
            bool: True if valid YouTube URL, False otherwise
        """
        url = url.strip()
        if not url:
            return False
        
        return any(pattern.search(url) for pattern in self.config.compiled_patterns)
    
    def normalize_youtube_url(self, url: str) -> str:
        """
        Normalize YouTube URL to standard format.
        
        Args:
            url (str): YouTube URL
            
        Returns:
            str: Normalized URL or original if invalid
        """
        video_id = self.extract_video_id(url)
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
        return url.strip()
    
    def read_urls_from_file(self, file_path: Path) -> List[str]:
        """
        Read URLs from file.
        
        Args:
            file_path (Path): Path to the file containing URLs
            
        Returns:
            List[str]: List of URLs
        """
        try:
            with file_path.open('r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            return urls
        except FileNotFoundError:
            print(f"❌ Error: File not found: {file_path}")
            return []
        except Exception as e:
            print(f"❌ Error reading file {file_path}: {e}")
            return []
    
    def validate_urls(self, urls: List[str]) -> ValidationResult:
        """
        Validate URLs and detect duplicates.
        
        Args:
            urls (List[str]): List of URLs to validate
            
        Returns:
            ValidationResult: Validation results
        """
        # Track normalized URLs with their positions
        url_positions = {}  # normalized_url -> list of positions
        normalized_urls = []
        invalid_urls = []
        
        for i, url in enumerate(urls):
            if self.is_valid_youtube_url(url):
                normalized_url = self.normalize_youtube_url(url)
                normalized_urls.append(normalized_url)
                
                # Track positions for each normalized URL
                if normalized_url not in url_positions:
                    url_positions[normalized_url] = []
                url_positions[normalized_url].append(i)
            else:
                invalid_urls.append(url)
        
        # Count occurrences to find duplicates
        url_counts = Counter(normalized_urls)
        
        # Find duplicates (URLs that appear more than once)
        duplicates = {url: count for url, count in url_counts.items() if count > 1}
        
        # Build detailed duplicate information
        duplicate_urls = []
        for normalized_url, count in duplicates.items():
            positions = url_positions[normalized_url]
            duplicate_info = DuplicateInfo(
                url=urls[positions[0]],  # Original URL from first occurrence
                normalized_url=normalized_url,
                positions=positions,
                count=count
            )
            duplicate_urls.append(duplicate_info)
        
        # Get unique URLs
        unique_urls = set(normalized_urls)
        
        # Calculate statistics
        total_duplicate_count = sum(count - 1 for count in duplicates.values())
        
        return ValidationResult(
            total_urls=len(urls),
            unique_urls=len(unique_urls),
            duplicate_count=total_duplicate_count,
            invalid_urls=len(invalid_urls),
            duplicates=duplicates,
            invalid_url_list=invalid_urls,
            valid_urls=unique_urls,
            duplicate_urls=duplicate_urls
        )
    
    def print_validation_summary(self, result: ValidationResult):
        """
        Print validation summary to console.
        
        Args:
            result (ValidationResult): Validation results
        """
        print("=" * 60)
        print("🔍 YouTube URL Validation Report")
        print("=" * 60)
        
        print(f"📊 STATISTICS:")
        print(f"   Total URLs processed: {result.total_urls}")
        print(f"   Unique valid URLs: {result.unique_urls}")
        print(f"   Duplicate URLs found: {result.duplicate_count}")
        print(f"   Invalid URLs found: {result.invalid_urls}")
        
        if result.duplicate_count > 0:
            print(f"\n🔄 DUPLICATES FOUND:")
            for url, count in result.duplicates.items():
                video_id = self.extract_video_id(url)
                print(f"   • {video_id} (appears {count} times)")
                print(f"     URL: {url}")
        else:
            print(f"\n✅ NO DUPLICATES FOUND!")
        
        if result.invalid_urls > 0:
            print(f"\n❌ INVALID URLs:")
            for i, invalid_url in enumerate(result.invalid_url_list[:5], 1):  # Show first 5
                print(f"   {i}. {invalid_url}")
            if len(result.invalid_url_list) > 5:
                print(f"   ... and {len(result.invalid_url_list) - 5} more")
        else:
            print(f"\n✅ ALL URLs ARE VALID!")
        
        print("=" * 60)
    
    def save_duplicates_report(self, result: ValidationResult):
        """
        Save detailed duplicates report to file.
        
        Args:
            result (ValidationResult): Validation results
        """
        with self.config.duplicates_report_file.open('w', encoding='utf-8') as f:
            f.write("YouTube URL Duplicates Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total URLs processed: {result.total_urls}\n")
            f.write(f"Unique valid URLs: {result.unique_urls}\n")
            f.write(f"Duplicate URLs found: {result.duplicate_count}\n")
            f.write(f"Invalid URLs found: {result.invalid_urls}\n\n")
            
            if result.duplicates:
                f.write("DUPLICATE URLs:\n")
                f.write("-" * 30 + "\n")
                for url, count in result.duplicates.items():
                    video_id = self.extract_video_id(url)
                    f.write(f"Video ID: {video_id}\n")
                    f.write(f"URL: {url}\n")
                    f.write(f"Occurrences: {count}\n")
                    f.write("-" * 30 + "\n")
            else:
                f.write("No duplicates found.\n")
            
            if result.invalid_url_list:
                f.write("\nINVALID URLs:\n")
                f.write("-" * 30 + "\n")
                for i, invalid_url in enumerate(result.invalid_url_list, 1):
                    f.write(f"{i}. {invalid_url}\n")
    
    def save_cleaned_urls(self, result: ValidationResult):
        """
        Save cleaned URLs (unique valid URLs) to file.
        
        Args:
            result (ValidationResult): Validation results
        """
        sorted_urls = sorted(result.valid_urls)
        
        with self.config.cleaned_urls_file.open('w', encoding='utf-8') as f:
            for url in sorted_urls:
                f.write(f"{url}\n")
    
    def save_validation_statistics(self, result: ValidationResult):
        """
        Save validation statistics to file.
        
        Args:
            result (ValidationResult): Validation results
        """
        with self.config.validation_stats_file.open('w', encoding='utf-8') as f:
            f.write("YouTube URL Validation Statistics\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total URLs processed: {result.total_urls}\n")
            f.write(f"Unique valid URLs: {result.unique_urls}\n")
            f.write(f"Duplicate URLs: {result.duplicate_count}\n")
            f.write(f"Invalid URLs: {result.invalid_urls}\n")
            f.write(f"Duplicate rate: {(result.duplicate_count / result.total_urls * 100):.2f}%\n")
            f.write(f"Invalid rate: {(result.invalid_urls / result.total_urls * 100):.2f}%\n")
            f.write(f"Unique rate: {(result.unique_urls / result.total_urls * 100):.2f}%\n")
    
    def validate_file(self, input_file: Optional[Path] = None) -> ValidationResult:
        """
        Validate URLs from file and generate reports.
        
        Args:
            input_file (Path): Path to input file. Uses default if None.
            
        Returns:
            ValidationResult: Validation results
        """
        file_path = input_file or self.config.default_input_file
        
        print(f"🔍 Reading URLs from: {file_path}")
        urls = self.read_urls_from_file(file_path)
        
        if not urls:
            print("❌ No URLs found or file could not be read.")
            return ValidationResult(0, 0, 0, 0, {}, [], set(), [])
        
        print(f"📊 Processing {len(urls)} URLs...")
        result = self.validate_urls(urls)
        
        # Print summary
        self.print_validation_summary(result)
        
        # Save reports
        print(f"\n💾 Saving reports...")
        self.save_duplicates_report(result)
        self.save_cleaned_urls(result)
        self.save_validation_statistics(result)
        
        print(f"✅ Reports saved to:")
        print(f"   • Duplicates report: {self.config.duplicates_report_file}")
        print(f"   • Cleaned URLs: {self.config.cleaned_urls_file}")
        print(f"   • Statistics: {self.config.validation_stats_file}")
        
        return result
    
    def remove_duplicates_from_file(self, duplicate_urls: List[DuplicateInfo], file_path: Path) -> int:
        """
        Remove duplicate URLs from file in-place.
        
        Args:
            duplicate_urls (List[DuplicateInfo]): List of duplicate information
            file_path (Path): Path to the file containing URLs
            
        Returns:
            int: Number of duplicates removed
        """
        try:
            # Read all lines from the file
            with file_path.open('r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Collect all positions to remove (keep only the first occurrence of each duplicate)
            positions_to_remove = set()
            
            for duplicate_info in duplicate_urls:
                # Remove all occurrences except the first one
                positions_to_remove.update(duplicate_info.positions[1:])
            
            # Create new content excluding the duplicate positions
            new_lines = []
            for i, line in enumerate(lines):
                if i not in positions_to_remove:
                    new_lines.append(line)
            
            # Write the cleaned content back to the file
            with file_path.open('w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            removed_count = len(positions_to_remove)
            print(f"✅ Removed {removed_count} duplicate URLs from {file_path}")
            return removed_count
            
        except Exception as e:
            print(f"❌ Error removing duplicates from file {file_path}: {e}")
            return 0
    
    def validate_only(self, file_path: Path) -> ValidationResult:
        """
        Validate URLs from file without side effects (no file creation).
        
        Args:
            file_path (Path): Path to input file
            
        Returns:
            ValidationResult: Validation results
        """
        urls = self.read_urls_from_file(file_path)
        
        if not urls:
            return ValidationResult(0, 0, 0, 0, {}, [], set(), [])
        
        return self.validate_urls(urls)
    
    def validate_and_clean_file(self, file_path: Path) -> ValidationResult:
        """
        Validate URLs from file and remove duplicates in-place.
        
        Args:
            file_path (Path): Path to input file
            
        Returns:
            ValidationResult: Validation results (before cleaning)
        """
        # First validate to get duplicate information
        result = self.validate_only(file_path)
        
        # Remove duplicates if found
        if result.duplicate_urls:
            removed_count = self.remove_duplicates_from_file(result.duplicate_urls, file_path)
            print(f"🧹 Cleaned file by removing {removed_count} duplicate URLs")
        
        return result


def main():
    """Main function to run the YouTube URL validator."""
    print("🎬 YouTube URL Validator and Duplicate Checker")
    print("=" * 60)
    
    # Initialize validator
    validator = YouTubeURLValidator()
    
    # Check if default file exists
    if not validator.config.default_input_file.exists():
        print(f"❌ Default file not found: {validator.config.default_input_file}")
        print("Please ensure the file exists or provide a different file path.")
        return
    
    # Validate URLs and clean duplicates
    print("🔍 Validating URLs and cleaning duplicates...")
    result = validator.validate_and_clean_file(validator.config.default_input_file)
    
    # Print summary
    validator.print_validation_summary(result)
    
    # Final summary
    if result.duplicate_count > 0:
        print(f"\n🧹 File has been cleaned of {result.duplicate_count} duplicate URLs!")
        print(f"   Original file now contains only unique URLs.")
    else:
        print(f"\n✅ No duplicates found! Your URL collection was already clean.")


if __name__ == "__main__":
    main()
