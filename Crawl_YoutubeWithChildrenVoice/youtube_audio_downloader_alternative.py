#!/usr/bin/env python3
"""
YouTube Audio Downloader Alternative using pytube

This module provides alternative functionality for downloading audio from YouTube videos
using pytube instead of yt-dlp. Created as a fallback when yt-dlp fails due to YouTube
blocking or cookie issues.

Author: Assistant
"""

import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from urllib.parse import parse_qs, urlparse

import ffmpeg


YTDLP_DOWNLOAD_WAIT_SECONDS = 180

try:
    from pytubefix import YouTube  # type: ignore
    print("[SUCCESS] Using pytubefix (maintained fork)")
except ImportError:
    try:
        from pytube import YouTube  # type: ignore
        print("[INFO] Falling back to pytube")
    except ImportError:
        print("[ERROR] Neither pytubefix nor pytube available")
        sys.exit(1)


class URLHelper:
    """Helper class for URL parsing and video ID extraction."""
    
    @staticmethod
    def extract_video_id(url: str) -> Optional[str]:
        """Extract YouTube video ID from URL."""
        try:
            parsed = urlparse(url)
            if 'youtube.com' in parsed.netloc:
                return parse_qs(parsed.query).get('v', [None])[0]
            elif 'youtu.be' in parsed.netloc:
                return parsed.path[1:]
        except Exception:
            pass
        return None


class FileNameHelper:
    """Helper class for generating file names."""
    
    @staticmethod
    def to_camel_case(text: str, max_len: int = 40) -> str:
        """Convert text to camel case with specified max length."""
        try:
            words = re.split(r'[^a-z0-9]+', (text or '').lower())
            words = [w for w in words if w]
            camel = ''.join(w.capitalize() for w in words)
            return camel[:max_len] if camel else 'NoTitle'
        except Exception:
            return 'NoTitle'
    
    @staticmethod
    def build_basename(index: int, url: str) -> str:
        """Build a descriptive basename for audio files."""
        title = None
        try:
            yt_tmp = YouTube(url)  # type: ignore
            title = yt_tmp.title
        except Exception:
            title = None
        
        video_id = URLHelper.extract_video_id(url)
        camel = FileNameHelper.to_camel_case(title or '')
        short_id = (video_id or 'noid')[:8]
        return f"{index:04d}_{short_id}_{camel}"


class ManifestManager:
    """Helper class for managing manifest files."""
    
    def __init__(self, manifest_path: Path):
        self.manifest_path = manifest_path
    
    def load_manifest(self) -> Dict:
        """Load manifest data from file."""
        try:
            if self.manifest_path.exists():
                data = json.loads(self.manifest_path.read_text(encoding='utf-8'))
                # Backward compatibility: older manifests were plain lists
                if isinstance(data, list):
                    records = data
                    total = 0.0
                    try:
                        total = float(sum(float(r.get('duration_seconds', 0) or 0) for r in records))
                    except Exception:
                        total = 0.0
                    return {
                        'total_duration_seconds': total,
                        'records': records
                    }
                elif isinstance(data, dict):
                    records = data.get('records', []) or []
                    # Ensure total exists; if missing, compute from records
                    if 'total_duration_seconds' not in data:
                        try:
                            data['total_duration_seconds'] = float(sum(float(r.get('duration_seconds', 0) or 0) for r in records))
                        except Exception:
                            data['total_duration_seconds'] = 0.0
                    else:
                        # Normalize type
                        try:
                            data['total_duration_seconds'] = float(data['total_duration_seconds'])
                        except Exception:
                            data['total_duration_seconds'] = 0.0
                    data['records'] = records
                    return data
        except Exception:
            pass
        return {
            'total_duration_seconds': 0.0,
            'records': []
        }
    
    def save_manifest(self, manifest_data: Dict) -> None:
        """Save manifest data to file."""
        try:
            self.manifest_path.write_text(
                json.dumps(manifest_data, ensure_ascii=False, indent=2), 
                encoding='utf-8'
            )
        except Exception as e:
            print(f"⚠️ Unable to write manifest: {e}")
    
    @staticmethod
    def index_manifest(records: List[Dict]) -> Dict[str, Dict]:
        """Create an index of manifest records by video ID."""
        by_id = {}
        for rec in records:
            vid = rec.get('video_id')
            if vid:
                by_id[vid] = rec
        return by_id


class TitleBackfillService:
    """Service for backfilling missing titles in manifest records."""
    
    def __init__(self, manifest_manager: ManifestManager):
        self.manifest_manager = manifest_manager
    
    def backfill_missing_titles(self, manifest_data: Dict) -> None:
        """Backfill missing titles by downloading and then deleting the file."""
        manifest_records = manifest_data.get('records', [])
        updated = False
        updated_count = 0
        failed_count = 0
        skipped_count = 0
        total_missing = sum(1 for r in manifest_records if r.get('status') == 'success' and not r.get('title'))
        
        if total_missing:
            print(f"🔧 Backfilling titles for {total_missing} records without titles...")
            print("=" * 60)
        else:
            print("✅ All records already have titles - no backfilling needed")
            return
            
        for idx_bf, rec in enumerate(manifest_records, start=1):
            try:
                if rec.get('status') == 'success' and not rec.get('title'):
                    url_val = rec.get('url')
                    if not url_val:
                        # Try reconstruct from video_id
                        vid_local = rec.get('video_id')
                        if vid_local:
                            url_val = f"https://www.youtube.com/watch?v={vid_local}"
                    
                    if not url_val:
                        vid_print = rec.get('video_id') or 'unknown'
                        print(f"⏭️  [{idx_bf}/{len(manifest_records)}] Skipping record {vid_print}: No URL available")
                        skipped_count += 1
                        continue
                    
                    vid_print = rec.get('video_id') or url_val[:50] + "..."
                    print(f"🔍 [{idx_bf}/{len(manifest_records)}] Processing: {vid_print}")
                    
                    title_val = self._fetch_title_via_download(url_val, vid_print)
                    
                    if title_val:
                        rec['title'] = title_val
                        updated = True
                        updated_count += 1
                        print(f"   ✅ SUCCESS: Title added - {title_val[:50]}...")
                        
                        # Persist incrementally so progress is visible
                        try:
                            manifest_data['records'] = manifest_records
                            self.manifest_manager.save_manifest(manifest_data)
                            print(f"   💾 Manifest updated incrementally")
                        except Exception as save_error:
                            print(f"   ⚠️  Incremental save failed: {save_error}")
                    else:
                        failed_count += 1
                        print(f"   ❌ FAILED: Could not retrieve title for {vid_print}")
                        
            except Exception as record_error:
                failed_count += 1
                vid_print = rec.get('video_id', 'unknown') if rec else 'unknown'
                print(f"❌ [{idx_bf}/{len(manifest_records)}] Record processing failed for {vid_print}: {str(record_error)[:100]}...")
        
        self._print_backfill_summary(len(manifest_records), total_missing, updated_count, failed_count, skipped_count)
        
        if updated:
            self._finalize_manifest_update(manifest_data, manifest_records, updated_count, total_missing, failed_count)
        elif total_missing > 0:
            self._handle_no_updates(total_missing, failed_count, skipped_count)
        
        print("=" * 60)
    
    def _fetch_title_via_download(self, url_val: str, vid_print: str) -> Optional[str]:
        """Fetch video title by performing a temporary download."""
        title_val = None
        # Download to a temporary directory and delete afterward
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                print(f"   📡 Creating YouTube object for {vid_print}...")
                yt_tmp2 = YouTube(url_val)  # type: ignore
                print(f"   🎯 Found video: {yt_tmp2.title[:50]}...")
                
                audio_stream = yt_tmp2.streams.filter(only_audio=True).order_by('abr').desc().first()
                if audio_stream is not None:
                    print(f"   ⏬ Downloading temporary file to fetch title...")
                    temp_name = f"tmp_title_fetch.{audio_stream.subtype}"
                    temp_path = Path(tmpdir) / temp_name
                    audio_stream.download(output_path=tmpdir, filename=temp_name)
                    # We only needed to perform a download; we don't keep the file
                    title_val = yt_tmp2.title
                    print(f"   🧹 Cleaning up temporary file...")
                    try:
                        if temp_path.exists():
                            temp_path.unlink()
                    except Exception as cleanup_error:
                        print(f"   ⚠️  Cleanup warning: {cleanup_error}")
                else:
                    # Even if no stream, try to use the title if accessible
                    print(f"   ⚠️  No audio streams found, but title is accessible")
                    title_val = yt_tmp2.title
                    
            except Exception as download_error:
                print(f"   ❌ Download failed: {str(download_error)[:100]}...")
                title_val = None
        
        return title_val
    
    def _print_backfill_summary(self, total_records: int, total_missing: int, updated_count: int, failed_count: int, skipped_count: int) -> None:
        """Print summary of backfill operation."""
        print("=" * 60)
        print("📊 BACKFILL SUMMARY:")
        print(f"   📋 Total records processed: {total_records}")
        print(f"   🔍 Records needing titles: {total_missing}")
        print(f"   ✅ Successfully updated: {updated_count}")
        print(f"   ❌ Failed to update: {failed_count}")
        print(f"   ⏭️  Skipped (no URL): {skipped_count}")
    
    def _finalize_manifest_update(self, manifest_data: Dict, manifest_records: List[Dict], updated_count: int, total_missing: int, failed_count: int) -> None:
        """Finalize the manifest update after backfill."""
        try:
            print("💾 Finalizing manifest update...")
            manifest_data['total_duration_seconds'] = float(sum(float(r.get('duration_seconds', 0) or 0) for r in manifest_records))
            manifest_data['records'] = manifest_records
            self.manifest_manager.save_manifest(manifest_data)
            print(f"✅ Backfill complete! Updated titles for {updated_count}/{total_missing} record(s).")
            
            if failed_count > 0:
                print(f"⚠️  Note: {failed_count} record(s) could not be updated (network issues, deleted videos, etc.)")
                
        except Exception as final_save_error:
            print(f"❌ Final manifest save failed: {final_save_error}")
    
    def _handle_no_updates(self, total_missing: int, failed_count: int, skipped_count: int) -> None:
        """Handle case where no updates were made."""
        print("⚠️ Backfill attempted, but no titles could be updated.")
        if failed_count == total_missing:
            print("💡 All attempts failed - check network connection or try again later")
        elif skipped_count == total_missing:
            print("💡 All records were skipped due to missing URLs")


class AudioDownloadProcessor:
    """Processor for handling individual audio downloads."""
    
    def __init__(self, downloader, manifest_manager: ManifestManager):
        self.downloader = downloader
        self.manifest_manager = manifest_manager
    
    def process_single_url(self, url: str, index: int, manifest_data: Dict, manifest_index: Dict[str, Dict]) -> None:
        """Process a single URL for download."""
        manifest_records = manifest_data.get('records', [])
        video_id = URLHelper.extract_video_id(url)
        
        if video_id and video_id in manifest_index and manifest_index[video_id].get('status') == 'success':
            print("⏭️  Already downloaded (manifest) - skipping")
            return
        
        try:
            self.downloader._current_basename = FileNameHelper.build_basename(index, url)
        except Exception:
            self.downloader._current_basename = None
        
        result = self.downloader.download_audio_pytube(url, index=index)
        self.downloader._current_basename = None
        
        if result:
            wav_file, duration = result
            print(f"✅ Saved: {wav_file} ({duration}s)")
            self._update_manifest(url, video_id, wav_file, duration, manifest_data, manifest_records, manifest_index)
        else:
            print("❌ Download failed")
            print(f"💔 SCRIPT EXECUTION FAILED: Could not download {url[:50]}...")
    
    def _update_manifest(self, url: str, video_id: Optional[str], wav_file: str, duration: float, 
                        manifest_data: Dict, manifest_records: List[Dict], manifest_index: Dict[str, Dict]) -> None:
        """Update the manifest with new download record."""
        # Try to fetch full title for manifest
        title_val = self._fetch_video_title(url)
        
        record = {
            'video_id': video_id or '',
            'url': url,
            'output_path': wav_file,
            'status': 'success',
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'duration_seconds': duration,
            'title': title_val
        }
        
        if video_id:
            manifest_index[video_id] = record
            # Merge preserving any records without video_id
            others = [r for r in manifest_records if not r.get('video_id') or r.get('video_id') not in manifest_index]
            manifest_records[:] = others + list(manifest_index.values())
        else:
            manifest_records.append(record)

        # Recompute total_duration_seconds to ensure correctness
        try:
            manifest_data['total_duration_seconds'] = float(sum(float(r.get('duration_seconds', 0) or 0) for r in manifest_records))
        except Exception:
            manifest_data['total_duration_seconds'] = 0.0
        manifest_data['records'] = manifest_records

        self.manifest_manager.save_manifest(manifest_data)
    
    def _fetch_video_title(self, url: str) -> str:
        """Fetch video title from URL."""
        try:
            yt_tmp2 = YouTube(url)  # type: ignore
            return yt_tmp2.title or ''
        except Exception:
            return ''


class BatchProcessor:
    """Processor for batch operations."""
    
    def __init__(self, processor: AudioDownloadProcessor):
        self.processor = processor
    
    def process_urls_from_file(self, file_path: Path, manifest_data: Dict, manifest_index: Dict[str, Dict]) -> None:
        """Process URLs from a file."""
        if not file_path.exists():
            print("❌ URLs file not found")
            sys.exit(1)
        
        urls = self._load_urls_from_file(file_path)
        print(f"📋 Batch download from: {file_path} ({len(urls)} URLs)")
        
        for idx, url in enumerate(urls, start=1):
            print(f"\n===== [{idx}/{len(urls)}] {url} =====")
            self.processor.process_single_url(url, idx, manifest_data, manifest_index)
        
        print("\n🎉 Batch download completed")
    
    def process_default_urls_file(self, default_urls_file: Path, manifest_data: Dict, manifest_index: Dict[str, Dict]) -> None:
        """Process URLs from the default file."""
        if default_urls_file.exists():
            self.process_urls_from_file(default_urls_file, manifest_data, manifest_index)
        else:
            print("⚠️ No URLs file found. Usage: python youtube_audio_downloader_alternative.py <url>|--from-file <path>")
            test_with_sample_video()
    
    def process_url_arguments(self, args: List[str], manifest_data: Dict, manifest_index: Dict[str, Dict]) -> None:
        """Process URLs from command line arguments."""
        for i, url in enumerate(args, start=1):
            self.processor.process_single_url(url, i, manifest_data, manifest_index)
    
    @staticmethod
    def _load_urls_from_file(file_path: Path) -> List[str]:
        """Load URLs from a text file."""
        return [
            line.strip() 
            for line in file_path.read_text(encoding='utf-8').splitlines() 
            if line.strip().startswith('http')
        ]


class YouTubeAudioDownloaderAlternative:
    """Alternative YouTube audio downloader using pytube."""
    
    def __init__(self, output_dir: str = "youtube_audio_outputs", cookies_file: Optional[str] = None, cookies_from_browser: Optional[str] = None):
        """
        Initialize the alternative downloader.
        
        Args:
            output_dir (str): Directory to save audio files
            cookies_file (Optional[str]): Path to cookies file (for future yt-dlp fallback)
            cookies_from_browser (Optional[str]): Browser name for cookies (for future yt-dlp fallback)
        """
        self.base_dir = Path(__file__).parent
        self.output_dir = self.base_dir / output_dir
        self.output_dir.mkdir(exist_ok=True)
        self._current_basename: Optional[str] = None  # For custom basenames when run as script
        
        # Cookie settings (stored for potential yt-dlp fallback usage)
        self.cookies_file = cookies_file
        self.cookies_from_browser = cookies_from_browser
        
        print(f"📁 Alternative downloader initialized. Output dir: {self.output_dir}")
        
        # Report cookie status
        if cookies_file:
            if os.path.exists(cookies_file):
                file_size = os.path.getsize(cookies_file)
                print(f"🍪 Cookie file configured: {cookies_file} ({file_size} bytes)")
            else:
                print(f"⚠️ Cookie file configured but not found: {cookies_file}")
        elif cookies_from_browser:
            print(f"🍪 Browser cookies configured: {cookies_from_browser}")
        else:
            print("⚠️ No cookies configured for alternative downloader")
            print("💡 Note: pytube doesn't use cookies, but they're available for yt-dlp fallback")
    
    def test_pytube_download(self, url: str) -> bool:
        """
        Test if pytube can download audio from a YouTube URL.
        
        Args:
            url (str): YouTube video URL
            
        Returns:
            bool: True if successful, False otherwise
        """
        print("🔧 ============================================")
        print("🔧 TESTING PYTUBE ALTERNATIVE METHOD")
        print("🔧 ============================================")
        print(f"🎵 Testing pytube download for: {url}")
        
        try:
            # Create YouTube object
            print("📡 Creating YouTube object...")
            yt = YouTube(url)  # type: ignore
            
            # Get video info
            print(f"📺 Video title: {yt.title}")
            print(f"📏 Video length: {yt.length}s ({yt.length//60}m {yt.length%60}s)")
            print(f"👤 Channel: {yt.author}")
            
            # Get available audio streams
            print("🔍 Getting available audio streams...")
            audio_streams = yt.streams.filter(only_audio=True)
            
            if not audio_streams:
                print("❌ No audio streams found")
                return False
            
            print(f"✅ Found {len(audio_streams)} audio streams:")
            for i, stream in enumerate(audio_streams):
                print(f"  {i+1}. {stream.itag}: {stream.mime_type} - {stream.abr}")
            
            # Select best audio quality
            best_audio = audio_streams.order_by('abr').desc().first()
            print(f"🎯 Selected best quality: {best_audio.mime_type} - {best_audio.abr}")
            
            # Test download (just a small portion)
            print("⏬ Testing download...")
            test_filename = f"test_pytube_{int(time.time())}.{best_audio.subtype}"
            test_path = self.output_dir / test_filename
            
            # Download to test
            best_audio.download(output_path=str(self.output_dir), filename=test_filename)
            
            if test_path.exists():
                file_size = test_path.stat().st_size
                print(f"✅ Download successful! File size: {file_size} bytes")
                
                # Clean up test file
                # test_path.unlink()
                # print("🧹 Test file cleaned up")
                
                print(f"💾 Test file kept for inspection: {test_path}")
                
                print("🎉 ============================================")
                print("🎉 PYTUBE TEST SUCCESSFUL!")
                print("🎉 Ready to use as yt-dlp alternative")
                print("🎉 ============================================")
                return True
            else:
                print("❌ Download failed - file not created")
                return False
                
        except Exception as e:
            print(f"❌ Pytube test failed: {e}")
            print("🔧 ============================================")
            print("🔧 PYTUBE TEST FAILED")
            print("🔧 ============================================")
            return False
    
    def download_audio_pytube(self, url: str, index: int = 0) -> Optional[Tuple[str, float]]:
        """
        Download and convert audio using pytube.
        
        Args:
            url (str): YouTube video URL
            index (int): Index for filename uniqueness
            
        Returns:
            Optional[Tuple[str, float]]: (wav_file_path, duration) or None if failed
        """
        print("🔧 ============================================")
        print("🔧 PYTUBE ALTERNATIVE METHOD ACTIVATED")
        print("🔧 ============================================")
        print(f"🎵 Starting pytube download for video {index}")
        
        # Generate compact, descriptive filename when run as script (basename may be injected)
        custom_base = getattr(self, '_current_basename', None)
        if custom_base:
            wav_file = self.output_dir / f"{custom_base}.wav"
        else:
            timestamp = int(time.time() * 1000)
            wav_file = self.output_dir / f"yt_{index}_{timestamp}.wav"
        temp_audio_file = None
        
        try:
            # Step 1: Download using pytube
            print("📡 Creating YouTube object...")
            yt = YouTube(url)  # type: ignore
            
            print(f"📺 Video: {yt.title[:50]}...")
            print(f"📏 Duration: {yt.length//60}m {yt.length%60}s")
            
            # No duration limit here; crawler decides whether to skip by length
            
            # Get best audio stream
            print("🔍 Getting audio streams...")
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            
            if not audio_stream:
                print("❌ No audio streams available")
                print(f"💔 DOWNLOAD FAILED: No audio streams for {yt.title[:50]}...")
                return None
            
            print(f"🎯 Selected: {audio_stream.mime_type} - {audio_stream.abr}")
            
            # Download audio
            print("⏬ Downloading audio...")
            temp_filename = f"tmp_{index}.{audio_stream.subtype}"
            temp_audio_file = self.output_dir / temp_filename
            
            audio_stream.download(output_path=str(self.output_dir), filename=temp_filename)
            
            if not temp_audio_file.exists():
                print("❌ Download failed - file not created")
                print(f"💔 DOWNLOAD FAILED: File not created for {yt.title[:50]}...")
                return None
            
            print(f"✅ Downloaded: {temp_audio_file.stat().st_size} bytes")
            print(f"🎉 Video successfully downloaded: {yt.title[:50]}...")
            
            # Step 2: Convert to WAV using ffmpeg
            print("🎵 Converting to WAV format...")
            
            # Use ffmpeg to convert to WAV
            try:
                stream = ffmpeg.input(str(temp_audio_file))
                # No time cap; convert full audio
                stream = ffmpeg.output(
                    stream, 
                    str(wav_file),
                    acodec='pcm_s16le',  # WAV PCM format
                    ar=16000,  # 16kHz sample rate
                    ac=1  # Mono
                )
                ffmpeg.run(stream, quiet=True, overwrite_output=True)
                
                if wav_file.exists():
                    # Get audio duration
                    audio_duration = float(yt.length)
                    
                    print(f"📏 Final audio duration: {audio_duration//60:.0f}m {audio_duration%60:.0f}s")
                    print("🎉 ============================================")
                    print("🎉 PYTUBE ALTERNATIVE METHOD SUCCESSFUL!")
                    print("🎉 ============================================")
                    print(f"✅ WAV file created: {wav_file}")
                    
                    return str(wav_file), audio_duration
                else:
                    print("❌ WAV conversion failed")
                    print(f"💔 CONVERSION FAILED: WAV file not created for {yt.title[:50]}...")
                    return None
                    
            except Exception as ffmpeg_error:
                print(f"❌ FFmpeg conversion failed: {ffmpeg_error}")
                print(f"💔 FFMPEG FAILED: Could not convert audio for {yt.title[:50]}...")
                return None
                
        except Exception as e:
            print(f"❌ Pytube download error: {e}")
            print(f"💔 PYTUBE FAILED: General download error for URL: {url[:50]}...")
            
            # Try yt-dlp fallback with cookies if configured
            if self.cookies_file or self.cookies_from_browser:
                print("🔄 Attempting yt-dlp fallback with cookies...")
                return self.download_audio_yt_dlp_fallback(url, index)
            else:
                print("⚠️ No cookies configured for yt-dlp fallback")
                return None
            
        finally:
            # Clean up temporary audio file (keeping WAV file for inspection)
            if temp_audio_file and temp_audio_file.exists():
                try:
                    temp_audio_file.unlink()
                    print("🧹 Temporary audio file cleaned up (WAV file kept)")
                except Exception as cleanup_error:
                    print(f"⚠️ Could not clean up temp file: {cleanup_error}")
    
    def download_audio_yt_dlp_fallback(self, url: str, index: int = 0) -> Optional[Tuple[str, float]]:
        """
        Fallback method using yt-dlp with cookies when pytube fails.
        
        Args:
            url (str): YouTube video URL
            index (int): Index for filename uniqueness
            
        Returns:
            Optional[Tuple[str, float]]: (wav_file_path, duration) or None if failed
        """
        print("🔧 ============================================")
        print("🔧 YT-DLP ANDROID CLIENT METHOD ACTIVATED")
        print("🔧 Using reliable Android client to bypass restrictions")
        print("🔧 ============================================")
        print(f"🎵 Starting yt-dlp Android client download for video {index}")
        
        # Generate output filename
        custom_base = getattr(self, '_current_basename', None)
        if custom_base:
            wav_file = self.output_dir / f"{custom_base}.wav"
            temp_audio_name = f"{custom_base}_temp"
        else:
            timestamp = int(time.time() * 1000)
            wav_file = self.output_dir / f"ytdlp_{index}_{timestamp}.wav"
            temp_audio_name = f"ytdlp_{index}_{timestamp}_temp"
        
        try:
            # Step 1: Use yt-dlp to download audio with cookies
            print("⏬ Downloading with yt-dlp...")
            
            # Build yt-dlp command with Android client to bypass YouTube restrictions
            cmd = [
                "yt-dlp",
                "-f", "bestaudio[ext=m4a]/bestaudio/best",  # Prefer m4a to avoid format issues
                "--extract-audio",
                "--audio-format", "wav",
                "--audio-quality", "5",  # Reduced quality to speed up processing (0=best, 9=worst)
                "--extractor-args", "youtube:player_client=android",  # Use Android client to bypass restrictions
                "--no-playlist",  # Ensure we don't accidentally download playlists
                "--no-check-certificate",  # Skip SSL certificate verification that might hang
                "--output", str(self.output_dir / f"{temp_audio_name}.%(ext)s"),
                url
            ]
            
            # Skip cookies when using Android client (incompatible)
            print("🤖 Using Android client - cookies disabled (Android client doesn't support cookies)")
            print("💡 Android client bypasses restrictions without needing cookies")
            
            # Add user agent for anti-detection
            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
            ]
            cmd.extend(["--user-agent", random.choice(user_agents)])
            
            # Add progress output and limit retries to prevent hanging
            cmd.extend(["--progress", "--retries", "1", "--fragment-retries", "1"])
            
            # Execute yt-dlp with enhanced timeout handling and stdin closure
            print(f"🔄 Running yt-dlp with Android client...")
            
            # Create result object compatible with subprocess.run
            class ProcessResult:
                def __init__(self, returncode: int, stdout: str, stderr: str):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr
            
            try:
                # Use Popen for better timeout control and explicitly close stdin
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    stdin=subprocess.PIPE,
                    text=True,
                    universal_newlines=True
                )
                
                # Close stdin immediately to prevent hanging
                if process.stdin:
                    process.stdin.close()
                
                # Wait with shorter timeout and provide periodic status updates
                print(f"⏳ Waiting for yt-dlp download (timeout: {YTDLP_DOWNLOAD_WAIT_SECONDS} seconds)...")
                try:
                    stdout, stderr = process.communicate(timeout=YTDLP_DOWNLOAD_WAIT_SECONDS)
                except subprocess.TimeoutExpired:
                    print("⚠️ Download taking longer than expected, forcing termination...")
                    process.terminate()
                    try:
                        process.wait(timeout=5)  # Give it 5 seconds to terminate gracefully
                    except subprocess.TimeoutExpired:
                        print("🔪 Force killing stuck process...")
                        process.kill()
                        process.wait()  # Wait for process to die
                    raise
                returncode = process.returncode
                
                result = ProcessResult(returncode, stdout, stderr)
                
            except subprocess.TimeoutExpired:
                print("⏰ yt-dlp process forced termination due to timeout")
                # Clean up any partial files left behind
                self._cleanup_temp_files(temp_audio_name)
                return None
            
            if result.returncode != 0:
                print(f"❌ yt-dlp failed: {result.stderr.strip()}")
                # Clean up any partial files left behind
                self._cleanup_temp_files(temp_audio_name)
                return None
            
            # Find the downloaded file
            temp_wav_file = None
            for file in self.output_dir.glob(f"{temp_audio_name}.*"):
                if file.suffix.lower() in ['.wav', '.m4a', '.mp3', '.webm']:
                    temp_wav_file = file
                    break
            
            if not temp_wav_file or not temp_wav_file.exists():
                print("❌ yt-dlp download failed - no output file found")
                # Clean up any partial files left behind
                self._cleanup_temp_files(temp_audio_name)
                return None
            
            print(f"✅ yt-dlp download successful: {temp_wav_file}")
            
            # Step 2: Convert to final WAV format if needed
            if temp_wav_file.suffix.lower() != '.wav':
                print("🎵 Converting to WAV format...")
                try:
                    stream = ffmpeg.input(str(temp_wav_file))
                    stream = ffmpeg.output(
                        stream, 
                        str(wav_file),
                        acodec='pcm_s16le',  # WAV PCM format
                        ar=16000,  # 16kHz sample rate
                        ac=1  # Mono
                    )
                    ffmpeg.run(stream, quiet=True, overwrite_output=True)
                    
                    # Clean up temporary file
                    temp_wav_file.unlink()
                    
                except Exception as ffmpeg_error:
                    print(f"❌ FFmpeg conversion failed: {ffmpeg_error}")
                    return None
            else:
                # Just rename the file
                temp_wav_file.rename(wav_file)
            
            if not wav_file.exists():
                print("❌ Final WAV file not created")
                return None
            
            # Get audio duration
            try:
                probe = ffmpeg.probe(str(wav_file))
                duration = float(probe['streams'][0]['duration'])
            except Exception:
                duration = None
            
            print("🎉 ============================================")
            print("🎉 YT-DLP ANDROID CLIENT METHOD SUCCESSFUL!")
            print("🎉 Downloaded using Android client bypass")
            print("🎉 ============================================")
            print(f"✅ Successfully downloaded via yt-dlp Android client: {wav_file}")
            
            if duration:
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                print(f"📏 Audio duration: {minutes}:{seconds:02d}")
            
            return str(wav_file), duration or 0.0
            
        except subprocess.TimeoutExpired:
            print("❌ yt-dlp timeout after 2 minutes - process was hanging")
            print("💡 This indicates the download was stuck, likely due to network issues")
            return None
        except Exception as e:
            print(f"❌ yt-dlp fallback error: {e}")
            # Clean up any partial files left behind
            self._cleanup_temp_files(temp_audio_name if 'temp_audio_name' in locals() else None)
            return None
    
    def _cleanup_temp_files(self, temp_audio_name: Optional[str] = None) -> None:
        """
        Clean up temporary and partial files left behind by failed downloads.
        
        Args:
            temp_audio_name (Optional[str]): Specific temp file name to clean up,
                                           or None to clean all orphaned files
        """
        try:
            if temp_audio_name:
                # Clean up specific temp files
                pattern_files = list(self.output_dir.glob(f"{temp_audio_name}.*"))
                for temp_file in pattern_files:
                    try:
                        temp_file.unlink()
                        print(f"🧹 Cleaned up temp file: {temp_file.name}")
                    except Exception as e:
                        print(f"⚠️  Could not clean up {temp_file.name}: {e}")
            
            # Always clean up orphaned .part files (partial downloads)
            part_files = list(self.output_dir.glob("*.part"))
            if part_files:
                print(f"🧹 Found {len(part_files)} orphaned .part files to clean up")
                import time
                current_time = time.time()
                
                for part_file in part_files:
                    try:
                        # Check file age - only remove files older than 5 minutes
                        file_age = current_time - part_file.stat().st_mtime
                        if file_age > 300:  # 5 minutes
                            part_file.unlink()
                            print(f"🗑️  Removed orphaned file: {part_file.name}")
                        else:
                            print(f"⏳ Skipping recent file (still downloading): {part_file.name}")
                    except Exception as e:
                        print(f"⚠️  Could not remove {part_file.name}: {e}")
            
        except Exception as e:
            print(f"⚠️  Error during temp file cleanup: {e}")
    
    def cleanup_all_temp_files(self) -> None:
        """
        Public method to clean up all temporary files.
        Call this periodically or at the end of processing.
        """
        print("🧹 Starting comprehensive temp file cleanup...")
        self._cleanup_temp_files()
        print("✅ Temp file cleanup completed")


def test_with_sample_video():
    """Test the alternative downloader with a sample video."""
    print("🚀 Testing YouTube Audio Downloader Alternative")
    print("=" * 60)
    
    # Use a short sample video for testing
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Short "Me at the zoo" video - first YouTube video
    print(f"🔗 Testing with: {test_url}")
    
    downloader = YouTubeAudioDownloaderAlternative()
    
    # Test 1: Check if pytube can access the video
    print("\n" + "=" * 60)
    print("TEST 1: Basic pytube functionality")
    print("=" * 60)
    
    success = downloader.test_pytube_download(test_url)
    
    if success:
        print("\n" + "=" * 60)
        print("TEST 2: Full download and conversion")
        print("=" * 60)
        
        # Test 2: Full download
        result = downloader.download_audio_pytube(test_url, index=999)
        
        if result:
            wav_file, duration = result
            print(f"\n🎉 SUCCESS! Downloaded: {wav_file}")
            print(f"📏 Duration: {duration}s")
            
            # Check file size
            file_size = Path(wav_file).stat().st_size
            print(f"📊 File size: {file_size} bytes ({file_size/1024/1024:.2f} MB)")
            
            # Keep test file for inspection
            # Path(wav_file).unlink()
            # print("🧹 Test file cleaned up")
            print(f"💾 Test file kept for inspection: {wav_file}")
        else:
            print("\n❌ Full download test failed")
    else:
        print("\n❌ Basic test failed - pytube cannot access YouTube")


if __name__ == "__main__":
    # Simple CLI: if args provided, treat as batch or single; else batch from default file
    import sys
    from pathlib import Path
    args = sys.argv[1:]
    base_dir = Path(__file__).parent
    default_urls_file = base_dir / 'youtube_url_outputs' / 'collected_video_urls.txt'
    # When executed directly, use final audio folder and manifest
    final_output_dir = 'final_audio_files'
    downloader = YouTubeAudioDownloaderAlternative(output_dir=final_output_dir)
    manifest_path = base_dir / final_output_dir / 'manifest.json'
    
    # Load and prepare manifest data
    manifest_manager = ManifestManager(manifest_path)
    manifest_data = manifest_manager.load_manifest()
    manifest_records = manifest_data.get('records', [])
    manifest_index = ManifestManager.index_manifest(manifest_records)

    # Initialize service classes
    manifest_manager = ManifestManager(manifest_path)
    backfill_service = TitleBackfillService(manifest_manager)
    processor = AudioDownloadProcessor(downloader, manifest_manager)
    batch_processor = BatchProcessor(processor)
    
    # Backfill missing titles
    backfill_service.backfill_missing_titles(manifest_data)
    
    # Process command line arguments
    if not args:
        batch_processor.process_default_urls_file(default_urls_file, manifest_data, manifest_index)
    else:
        # Support --from-file <path> or direct URL(s)
        if args[0] == '--from-file' and len(args) >= 2:
            batch_processor.process_urls_from_file(Path(args[1]), manifest_data, manifest_index)
        else:
            batch_processor.process_url_arguments(args, manifest_data, manifest_index)
