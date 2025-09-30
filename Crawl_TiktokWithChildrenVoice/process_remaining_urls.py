#!/usr/bin/env python3
"""
TikTok Audio Processor - Download Remaining URLs

This script processes all URLs from the collected URLs file that haven't been downloaded yet,
downloads the videos, validates them for children's voice content, and saves the validated
audio files to the final_audio_files directory with a CSV manifest for tracking.

Author: Generated for TikTok Children's Voice Processing
Version: 1.0
"""

import csv
import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Set, Dict, Any, Optional, List
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from tiktok_api_client import TikTokAPIClient
    from tiktok_audio_classifier import TikTokAudioClassifier
    from tiktok_video_downloader import TikTokVideoDownloader
    API_CLIENT_AVAILABLE = True
except ImportError as e:
    API_CLIENT_AVAILABLE = False
    print(f"❌ Failed to import TikTok modules: {e}")
    print("Please ensure all required modules are available")


class TikTokAudioProcessor:
    """Process remaining TikTok URLs and save validated audio files."""
    
    def __init__(self):
        """Initialize the processor."""
        self.output_dir = Path("./tiktok_url_outputs")
        self.final_audio_dir = Path("./final_audio_files")
        self.urls_file = self.output_dir / "multi_query_collected_video_urls.txt"
        self.manifest_file = self.final_audio_dir / "manifest.csv"
        
        # Create directories
        self.output_dir.mkdir(exist_ok=True)
        self.final_audio_dir.mkdir(exist_ok=True)
        
        # Initialize components
        if not API_CLIENT_AVAILABLE:
            raise RuntimeError("Required TikTok modules are not available")
        
        print("🔧 Initializing TikTok Audio Processor...")
        self.api_client = TikTokAPIClient(self)
        self.audio_classifier = TikTokAudioClassifier(self)
        self.video_downloader = TikTokVideoDownloader(self)
        
        # Load existing downloads
        self.downloaded_urls = self._load_manifest()
        
        print("✅ TikTok Audio Processor initialized successfully")
    
    def print_info(self, message: str) -> None:
        """Print info message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ℹ️  {message}")
    
    def print_progress(self, message: str) -> None:
        """Print progress message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] 🔄 {message}")
    
    def print_success(self, message: str) -> None:
        """Print success message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ✅ {message}")
    
    def print_warning(self, message: str) -> None:
        """Print warning message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ⚠️  {message}")
    
    def print_error(self, message: str) -> None:
        """Print error message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] ❌ {message}")
    
    def debug_log(self, message: str) -> None:
        """Print debug message."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        print(f"[{timestamp}] 🔍 DEBUG: {message}")
    
    def _load_manifest(self) -> Set[str]:
        """Load existing manifest CSV and return set of downloaded URLs."""
        downloaded_urls = set()
        
        if self.manifest_file.exists():
            try:
                with open(self.manifest_file, 'r', encoding='utf-8', newline='') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('status') == 'success':
                            downloaded_urls.add(row.get('url', ''))
                self.print_info(f"📋 Loaded {len(downloaded_urls)} existing downloads from manifest")
            except Exception as e:
                self.print_error(f"Error loading manifest: {e}")
        else:
            # Create manifest file with headers
            self._create_manifest_headers()
            self.print_info("📋 Created new manifest file")
        
        return downloaded_urls
    
    def _create_manifest_headers(self) -> None:
        """Create manifest CSV file with headers."""
        try:
            with open(self.manifest_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'url', 'video_id', 'title', 'author_username', 'duration_seconds',
                    'confidence', 'is_vietnamese', 'has_children_voice', 
                    'output_path', 'status', 'timestamp'
                ])
        except Exception as e:
            self.print_error(f"Error creating manifest: {e}")
    
    def _update_manifest(self, video_info: Dict, audio_path: str, analysis_result: Any) -> None:
        """Update manifest CSV with new download entry."""
        try:
            with open(self.manifest_file, 'a', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    video_info.get('url', ''),
                    video_info.get('video_id', ''),
                    video_info.get('title', '').replace('"', "'"),  # Clean quotes
                    video_info.get('author_username', ''),
                    video_info.get('duration', 0),
                    getattr(analysis_result, 'confidence', 0.0),
                    getattr(analysis_result, 'is_vietnamese', False),
                    getattr(analysis_result, 'has_children_voice', False),
                    audio_path,
                    'success',
                    datetime.now().isoformat()
                ])
        except Exception as e:
            self.print_error(f"Error updating manifest: {e}")
    
    def _get_next_audio_filename(self) -> str:
        """Generate next sequential audio filename."""
        existing_files = list(self.final_audio_dir.glob("*.wav"))
        
        # Find the highest existing number
        max_num = 0
        for file in existing_files:
            try:
                # Extract number from filename like "0001_video_title.wav"
                num_str = file.stem.split('_')[0]
                if num_str.isdigit():
                    max_num = max(max_num, int(num_str))
            except (IndexError, ValueError):
                continue
        
        # Return next number
        return f"{max_num + 1:04d}"
    
    def _save_final_audio(self, temp_audio_path: str, video_info: Dict, analysis_result: Any) -> Optional[str]:
        """Save validated audio to final_audio_files directory."""
        try:
            # Generate filename
            file_number = self._get_next_audio_filename()
            video_id = video_info.get('video_id', 'unknown')[:8]
            title = video_info.get('title', 'unknown')
            
            # Clean title for filename
            clean_title = ''.join(c for c in title if c.isalnum() or c in ' -_')[:30]
            clean_title = clean_title.replace(' ', '')
            
            filename = f"{file_number}_{video_id}_{clean_title}.wav"
            final_audio_path = self.final_audio_dir / filename
            
            # Copy audio file to final directory
            shutil.copy2(temp_audio_path, final_audio_path)
            
            self.print_success(f"💾 Saved final audio: {filename}")
            return str(final_audio_path)
            
        except Exception as e:
            self.print_error(f"Error saving final audio: {e}")
            return None
    
    def _extract_video_id_from_url(self, url: str) -> str:
        """Extract video ID from TikTok URL."""
        try:
            import re
            # Common TikTok URL patterns
            patterns = [
                r'tiktok\\.com/@[^/]+/video/(\\d+)',
                r'tiktok\\.com/.*?/video/(\\d+)',
                r'vm\\.tiktok\\.com/(\\w+)',
                r'vt\\.tiktok\\.com/(\\w+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            
            # Fallback: use URL hash
            return str(hash(url))[-8:]
            
        except Exception:
            return 'unknown'
    
    def _get_video_info_from_url(self, url: str) -> Dict:
        """Get video information from URL using API."""
        try:
            # Extract video ID
            video_id = self._extract_video_id_from_url(url)
            
            # Try to get more detailed info from API if possible
            # For now, return basic info
            return {
                'url': url,
                'video_id': video_id,
                'title': 'Unknown',
                'author_username': 'unknown',
                'duration': 0
            }
        except Exception as e:
            self.print_error(f"Error getting video info: {e}")
            return {
                'url': url,
                'video_id': 'unknown',
                'title': 'Unknown',
                'author_username': 'unknown',
                'duration': 0
            }
    
    def process_video(self, url: str) -> bool:
        """Process a single video URL."""
        try:
            self.print_progress(f"Processing: {url[:60]}...")
            
            # Get video info
            video_info = self._get_video_info_from_url(url)
            
            # Download and convert to audio
            audio_path, duration = self.video_downloader.download_and_convert_audio(video_info)
            
            if not audio_path or not Path(audio_path).exists():
                self.print_warning("Failed to download/convert video")
                return False
            
            # Analyze audio
            analysis_result = self.audio_classifier.analyze_audio(audio_path)
            
            if analysis_result.error:
                self.print_warning(f"Analysis failed: {analysis_result.error}")
                # Clean up
                self.video_downloader.cleanup_audio_file(audio_path)
                return False
            
            # Check if it's Vietnamese (if language detection is enabled)
            if not analysis_result.is_vietnamese:
                self.debug_log(f"Video is not Vietnamese (detected: {analysis_result.detected_language})")
                # Clean up
                self.video_downloader.cleanup_audio_file(audio_path)
                return False
            
            # Check for children's voice
            if not analysis_result.has_children_voice:
                self.debug_log(f"No children's voice detected (confidence: {analysis_result.confidence:.2f})")
                # Clean up
                self.video_downloader.cleanup_audio_file(audio_path)
                return False
            
            # Video passed validation - save to final directory
            final_audio_path = self._save_final_audio(audio_path, video_info, analysis_result)
            
            if final_audio_path:
                # Update manifest
                self._update_manifest(video_info, final_audio_path, analysis_result)
                # Add to downloaded URLs
                self.downloaded_urls.add(url)
                
                self.print_success(f"✅ Validated and saved: {video_info.get('title', 'Unknown')[:30]}... (confidence: {analysis_result.confidence:.2f})")
            
            # Clean up temporary audio
            self.video_downloader.cleanup_audio_file(audio_path)
            
            return bool(final_audio_path)
            
        except Exception as e:
            self.print_error(f"Error processing video {url}: {e}")
            return False
    
    def load_urls_from_file(self) -> List[str]:
        """Load URLs from the collected URLs file."""
        if not self.urls_file.exists():
            self.print_error(f"URLs file not found: {self.urls_file}")
            return []
        
        try:
            with open(self.urls_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip()]
            
            self.print_info(f"📋 Loaded {len(urls)} URLs from file")
            return urls
            
        except Exception as e:
            self.print_error(f"Error reading URLs file: {e}")
            return []
    
    def process_remaining_urls(self) -> None:
        """Process all remaining URLs that haven't been downloaded yet."""
        # Load all URLs
        all_urls = self.load_urls_from_file()
        
        if not all_urls:
            self.print_warning("No URLs found to process")
            return
        
        # Filter remaining URLs
        remaining_urls = [url for url in all_urls if url not in self.downloaded_urls]
        
        if not remaining_urls:
            self.print_success("✅ All URLs have already been processed!")
            return
        
        self.print_info(f"📊 Statistics:")
        self.print_info(f"   Total URLs: {len(all_urls)}")
        self.print_info(f"   Already processed: {len(all_urls) - len(remaining_urls)}")
        self.print_info(f"   Remaining to process: {len(remaining_urls)}")
        
        # Process remaining URLs
        successful_count = 0
        failed_count = 0
        
        for i, url in enumerate(remaining_urls, 1):
            self.print_progress(f"[{i}/{len(remaining_urls)}] Processing URL {i}")
            
            if self.process_video(url):
                successful_count += 1
            else:
                failed_count += 1
            
            # Progress update
            if i % 10 == 0:
                self.print_info(f"Progress: {successful_count} successful, {failed_count} failed out of {i} processed")
        
        # Final summary
        self.print_success(f"🎉 Processing complete!")
        self.print_info(f"📊 Final Statistics:")
        self.print_info(f"   Successfully processed: {successful_count}")
        self.print_info(f"   Failed: {failed_count}")
        self.print_info(f"   Success rate: {(successful_count / len(remaining_urls) * 100):.1f}%")
        
        # Show final audio directory stats
        if self.final_audio_dir.exists():
            audio_files = list(self.final_audio_dir.glob("*.wav"))
            total_size = sum(f.stat().st_size for f in audio_files) / (1024*1024)  # MB
            self.print_info(f"💾 Final audio files: {len(audio_files)} files ({total_size:.1f} MB)")


def main():
    """Main function."""
    try:
        print("🚀 Starting TikTok Audio Processor...")
        
        processor = TikTokAudioProcessor()
        processor.process_remaining_urls()
        
        print("✅ TikTok Audio Processor completed successfully!")
        
    except KeyboardInterrupt:
        print("\\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\\n❌ Process failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()