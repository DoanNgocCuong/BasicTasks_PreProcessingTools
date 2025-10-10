#!/usr/bin/env python3
"""
YouTube URL Validator and Audio Classifier

This module provides comprehensive validation and analysis tools for YouTube URL collections.
It validates URL formats, detects and reports duplicates, normalizes URLs to standard format,
and generates detailed statistics and cleaned datasets.

Additionally, it provides audio classification functionality to validate audio files
using children's voice detection and cleanup non-children audio files.

Author: Le Hoang Minh
"""
import json
import os
import re
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import Counter
from dataclasses import dataclass

# Import models from the new models package
from models.validation_models import DuplicateInfo, ValidationResult, ClassificationResult

# Import utilities
from utils.url_utils import extract_video_id, normalize_youtube_url


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
        video_id = extract_video_id(url)
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
                video_id = extract_video_id(url)
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
                    video_id = extract_video_id(url)
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


class AudioFileClassifier:
    """Handles audio file classification and cleanup based on children's voice detection."""
    
    def __init__(self, manifest_path: Optional[Path] = None, max_workers: int = 4):
        """
        Initialize the audio classifier.
        
        Args:
            manifest_path (Optional[Path]): Path to manifest.json file
            max_workers (int): Maximum number of worker threads for parallel processing
        """
        self.script_dir = Path(__file__).parent
        self.manifest_path = manifest_path or self.script_dir / "final_audio_files" / "manifest.json"
        self.max_workers = max_workers
        self._classifier = None
        self._classifier_lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'children_voice_kept': 0,
            'non_children_deleted': 0,
            'files_not_found': 0,
            'classification_errors': 0
        }
    
    def _get_classifier(self):
        """Get or create audio classifier instance (thread-safe lazy loading)."""
        if self._classifier is None:
            with self._classifier_lock:
                if self._classifier is None:
                    try:
                        # Import here to avoid issues if the module is not available
                        from youtube_audio_classifier import AudioClassifier
                        self._classifier = AudioClassifier()
                        print("✅ Audio classifier loaded successfully")
                    except ImportError as e:
                        print(f"❌ Failed to import AudioClassifier: {e}")
                        raise
                    except Exception as e:
                        print(f"❌ Failed to initialize AudioClassifier: {e}")
                        raise
        return self._classifier
    
    def load_manifest(self) -> Dict[str, Any]:
        """
        Load manifest.json file.
        
        Returns:
            Dict[str, Any]: Manifest data
        """
        try:
            if not self.manifest_path.exists():
                raise FileNotFoundError(f"Manifest file not found: {self.manifest_path}")
            
            with self.manifest_path.open('r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading manifest: {e}")
            raise
    
    def save_manifest(self, manifest_data: Dict[str, Any]) -> None:
        """
        Save manifest.json file.
        
        Args:
            manifest_data (Dict[str, Any]): Manifest data to save
        """
        try:
            # Create backup before saving
            backup_path = self.manifest_path.with_suffix(f'.json.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            shutil.copy2(self.manifest_path, backup_path)
            
            with self.manifest_path.open('w', encoding='utf-8') as f:
                json.dump(manifest_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Manifest saved successfully (backup: {backup_path.name})")
        except Exception as e:
            print(f"❌ Error saving manifest: {e}")
            raise
    
    def classify_audio_file(self, manifest_entry: Dict[str, Any]) -> ClassificationResult:
        """
        Classify a single audio file for children's voice.
        
        Args:
            manifest_entry (Dict[str, Any]): Manifest entry containing audio file path
            
        Returns:
            ClassificationResult: Classification result
        """
        audio_path = manifest_entry.get('output_path', '')
        
        try:
            start_time = datetime.now()
            
            # Check if file exists
            if not os.path.exists(audio_path):
                return ClassificationResult(
                    audio_path=audio_path,
                    is_children=False,
                    confidence=0.0,
                    error="File not found"
                )
            
            # Get classifier and run classification
            classifier = self._get_classifier()
            is_children = classifier.is_child_audio_optimized(audio_path)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if is_children is None:
                return ClassificationResult(
                    audio_path=audio_path,
                    is_children=False,
                    confidence=0.0,
                    error="Classification failed",
                    processing_time=processing_time
                )
            
            return ClassificationResult(
                audio_path=audio_path,
                is_children=is_children,
                confidence=1.0 if is_children else 0.0,
                processing_time=processing_time
            )
            
        except Exception as e:
            return ClassificationResult(
                audio_path=audio_path,
                is_children=False,
                confidence=0.0,
                error=str(e)
            )
    
    def delete_audio_file_and_update_stats(self, manifest_entry: Dict[str, Any], manifest_data: Dict[str, Any]) -> bool:
        """
        Delete audio file and remove its duration from total stats.
        
        Args:
            manifest_entry (Dict[str, Any]): Manifest entry to delete
            manifest_data (Dict[str, Any]): Full manifest data
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        audio_path = manifest_entry.get('output_path', '')
        duration = manifest_entry.get('duration_seconds', 0)
        
        try:
            # Delete audio file if it exists
            if os.path.exists(audio_path):
                os.remove(audio_path)
                print(f"🗑️  Deleted audio file: {Path(audio_path).name}")
            
            # Update total duration
            if 'total_duration_seconds' in manifest_data and duration > 0:
                manifest_data['total_duration_seconds'] -= duration
            
            return True
            
        except Exception as e:
            print(f"❌ Error deleting file {audio_path}: {e}")
            return False
    
    def process_single_entry(self, manifest_entry: Dict[str, Any], manifest_data: Dict[str, Any]) -> Tuple[bool, ClassificationResult]:
        """
        Process a single manifest entry for classification.
        
        Args:
            manifest_entry (Dict[str, Any]): Single manifest entry
            manifest_data (Dict[str, Any]): Full manifest data (for stats updates)
            
        Returns:
            Tuple[bool, ClassificationResult]: (should_keep, classification_result)
        """
        # Skip if already classified
        if manifest_entry.get('classified', False):
            return True, ClassificationResult(
                audio_path=manifest_entry.get('output_path', ''),
                is_children=True,  # If in manifest and classified, it's children's voice
                confidence=1.0
            )
        
        # Run classification
        result = self.classify_audio_file(manifest_entry)
        
        # Update statistics
        self.stats['total_processed'] += 1
        
        if result.error == "File not found":
            self.stats['files_not_found'] += 1
            print(f"❌ File not found: {Path(result.audio_path).name}")
            return False, result
        elif result.error:
            self.stats['classification_errors'] += 1
            print(f"❌ Classification error for {Path(result.audio_path).name}: {result.error}")
            return False, result
        elif result.is_children:
            self.stats['children_voice_kept'] += 1
            # Update manifest entry
            manifest_entry['classified'] = True
            manifest_entry['classification_timestamp'] = datetime.now().isoformat()
            print(f"✅ Children's voice detected: {Path(result.audio_path).name}")
            return True, result
        else:
            self.stats['non_children_deleted'] += 1
            # Delete file and update stats
            self.delete_audio_file_and_update_stats(manifest_entry, manifest_data)
            print(f"❌ Non-children voice detected and deleted: {Path(result.audio_path).name}")
            return False, result
    
    def validate_and_classify_audio_files(self) -> Dict[str, int]:
        """
        Main method to validate and classify all unclassified audio files.
        
        Returns:
            Dict[str, int]: Statistics summary
        """
        print(">>> Starting audio file classification and validation...")
        print(f">>> Manifest file: {self.manifest_path}")
        print(f">>> Max workers: {self.max_workers}")
        
        # Load manifest
        manifest_data = self.load_manifest()
        total_records = len(manifest_data.get('records', []))
        print(f">>> Total records in manifest: {total_records}")
        
        # Filter unclassified entries
        unclassified_entries = [
            entry for entry in manifest_data.get('records', [])
            if not entry.get('classified', False)
        ]
        
        print(f">>> Unclassified entries to process: {len(unclassified_entries)}")
        
        if not unclassified_entries:
            print(">>> All entries are already classified!")
            return self.stats
        
        # Process entries with thread pool
        entries_to_keep = []
        
        print(f">>> Processing {len(unclassified_entries)} entries with {self.max_workers} workers...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_entry = {
                executor.submit(self.process_single_entry, entry, manifest_data): entry
                for entry in unclassified_entries
            }
            
            # Process completed tasks
            for i, future in enumerate(as_completed(future_to_entry), 1):
                entry = future_to_entry[future]
                try:
                    should_keep, result = future.result()
                    if should_keep:
                        entries_to_keep.append(entry)
                    
                    # Progress update
                    if i % 10 == 0 or i == len(unclassified_entries):
                        print(f">>> Progress: {i}/{len(unclassified_entries)} entries processed")
                        
                except Exception as e:
                    print(f">>> Error processing entry: {e}")
                    self.stats['classification_errors'] += 1
        
        # Update manifest with kept entries (remove deleted ones)
        all_classified_entries = [
            entry for entry in manifest_data.get('records', [])
            if entry.get('classified', False)
        ]
        
        # Combine already classified + newly classified entries
        updated_records = all_classified_entries + entries_to_keep
        manifest_data['records'] = updated_records
        
        print(f">>> Updated manifest: {len(updated_records)} total records (removed {total_records - len(updated_records)} entries)")
        
        # Save updated manifest
        self.save_manifest(manifest_data)
        
        # Print statistics
        self.print_classification_summary()
        
        return self.stats
    
    def print_classification_summary(self):
        """Print classification summary statistics."""
        print("\n" + "=" * 60)
        print("🎯 AUDIO CLASSIFICATION SUMMARY")
        print("=" * 60)
        print(f"📊 Total entries processed: {self.stats['total_processed']}")
        print(f"✅ Children's voices kept: {self.stats['children_voice_kept']}")
        print(f"❌ Non-children voices deleted: {self.stats['non_children_deleted']}")
        print(f"📁 Files not found: {self.stats['files_not_found']}")
        print(f"⚠️  Classification errors: {self.stats['classification_errors']}")
        
        if self.stats['total_processed'] > 0:
            success_rate = ((self.stats['children_voice_kept']) / self.stats['total_processed']) * 100
            print(f"📈 Children's voice rate: {success_rate:.1f}%")
        
        print("=" * 60)


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


def main_audio_classification():
    """Main function for audio file classification."""
    print(">>> YouTube Audio File Classifier")
    print("=" * 60)
    
    # Initialize classifier
    classifier = AudioFileClassifier(max_workers=4)
    
    # Run classification
    try:
        stats = classifier.validate_and_classify_audio_files()
        print("\n>>> Classification completed successfully!")
        
    except Exception as e:
        print(f"\n>>> Classification failed: {e}")
        print("Please check the error messages above and try again.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--classify-audio":
        main_audio_classification()
    else:
        main()
