#!/usr/bin/env python3
"""
YouTube Audio Downloader Alternative using pytube

This module provides alternative functionality for downloading audio from YouTube videos
using pytube instead of yt-dlp. Created as a fallback when yt-dlp fails due to YouTube
blocking or cookie issues.

Author: Assistant
"""

import os
import sys
import time
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import ffmpeg

try:
    from pytubefix import YouTube
    print("✅ Using pytubefix (maintained fork)")
except ImportError:
    try:
        from pytube import YouTube
        print("⚠️ Using original pytube (may have issues)")
    except ImportError:
        print("❌ Neither pytube nor pytubefix installed. Install with: pip install pytubefix")
        sys.exit(1)


class YouTubeAudioDownloaderAlternative:
    """Alternative YouTube audio downloader using pytube."""
    
    def __init__(self, output_dir: str = "youtube_audio_outputs"):
        """
        Initialize the alternative downloader.
        
        Args:
            output_dir (str): Directory to save audio files
        """
        self.base_dir = Path(__file__).parent
        self.output_dir = self.base_dir / output_dir
        self.output_dir.mkdir(exist_ok=True)
        
        print(f"📁 Alternative downloader initialized. Output dir: {self.output_dir}")
    
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
            yt = YouTube(url)
            
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
            yt = YouTube(url)
            
            print(f"📺 Video: {yt.title[:50]}...")
            print(f"📏 Duration: {yt.length//60}m {yt.length%60}s")
            
            # No duration limit here; crawler decides whether to skip by length
            
            # Get best audio stream
            print("🔍 Getting audio streams...")
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            
            if not audio_stream:
                print("❌ No audio streams available")
                return None
            
            print(f"🎯 Selected: {audio_stream.mime_type} - {audio_stream.abr}")
            
            # Download audio
            print("⏬ Downloading audio...")
            temp_filename = f"tmp_{index}.{audio_stream.subtype}"
            temp_audio_file = self.output_dir / temp_filename
            
            audio_stream.download(output_path=str(self.output_dir), filename=temp_filename)
            
            if not temp_audio_file.exists():
                print("❌ Download failed - file not created")
                return None
            
            print(f"✅ Downloaded: {temp_audio_file.stat().st_size} bytes")
            
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
                    return None
                    
            except Exception as ffmpeg_error:
                print(f"❌ FFmpeg conversion failed: {ffmpeg_error}")
                return None
                
        except Exception as e:
            print(f"❌ Pytube download error: {e}")
            return None
            
        finally:
            # Clean up temporary audio file (keeping WAV file for inspection)
            if temp_audio_file and temp_audio_file.exists():
                try:
                    temp_audio_file.unlink()
                    print("🧹 Temporary audio file cleaned up (WAV file kept)")
                except Exception as cleanup_error:
                    print(f"⚠️ Could not clean up temp file: {cleanup_error}")


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
    
    def _load_manifest(path: Path):
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding='utf-8'))
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
    
    def _save_manifest(path: Path, manifest_data):
        try:
            path.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            print(f"⚠️ Unable to write manifest: {e}")
    
    def _index_manifest(records):
        by_id = {}
        for rec in records:
            vid = rec.get('video_id')
            if vid:
                by_id[vid] = rec
        return by_id
    
    import json
    manifest_data = _load_manifest(manifest_path)
    manifest_records = manifest_data.get('records', [])
    manifest_index = _index_manifest(manifest_records)

    # Backfill missing titles by downloading and then deleting the file
    def _backfill_missing_titles_by_download():
        updated = False
        updated_count = 0
        total_missing = sum(1 for r in manifest_records if r.get('status') == 'success' and not r.get('title'))
        if total_missing:
            print(f"🔧 Backfilling titles for {total_missing} records without titles...")
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
                        continue
                    title_val = None
                    # Download to a temporary directory and delete afterward
                    with tempfile.TemporaryDirectory() as tmpdir:
                        try:
                            yt_tmp2 = YouTube(url_val)
                            audio_stream = yt_tmp2.streams.filter(only_audio=True).order_by('abr').desc().first()
                            if audio_stream is not None:
                                temp_name = f"tmp_title_fetch.{audio_stream.subtype}"
                                temp_path = Path(tmpdir) / temp_name
                                audio_stream.download(output_path=tmpdir, filename=temp_name)
                                # We only needed to perform a download; we don't keep the file
                                title_val = yt_tmp2.title
                                try:
                                    if temp_path.exists():
                                        temp_path.unlink()
                                except Exception:
                                    pass
                            else:
                                # Even if no stream, try to use the title if accessible
                                title_val = yt_tmp2.title
                        except Exception:
                            title_val = None
                    if title_val:
                        rec['title'] = title_val
                        updated = True
                        updated_count += 1
                        try:
                            vid_print = rec.get('video_id') or url_val
                            print(f"📝 Title added for {vid_print}: {title_val}")
                        except Exception:
                            pass
                        # Persist incrementally so progress is visible
                        try:
                            manifest_data['records'] = manifest_records
                            _save_manifest(manifest_path, manifest_data)
                        except Exception:
                            pass
            except Exception:
                pass
        if updated:
            try:
                manifest_data['total_duration_seconds'] = float(sum(float(r.get('duration_seconds', 0) or 0) for r in manifest_records))
            except Exception:
                manifest_data['total_duration_seconds'] = 0.0
            manifest_data['records'] = manifest_records
            _save_manifest(manifest_path, manifest_data)
            print(f"✅ Backfill complete. Updated titles for {updated_count} record(s).")
        elif total_missing:
            print("⚠️ Backfill attempted, but no titles could be updated.")

    _backfill_missing_titles_by_download()

    def _to_camel_case_lower_suffix(text: str, max_len: int = 40) -> str:
        try:
            import re
            words = re.split(r'[^a-z0-9]+', (text or '').lower())
            words = [w for w in words if w]
            camel = ''.join(w.capitalize() for w in words)
            return camel[:max_len] if camel else 'NoTitle'
        except Exception:
            return 'NoTitle'

    def _build_basename(idx: int, url: str) -> str:
        # Try to derive title via pytube (cheap; already used later)
        title = None
        try:
            yt_tmp = YouTube(url)
            title = yt_tmp.title
        except Exception:
            title = None
        # Extract video id
        vid_local = None
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            if 'youtube.com' in parsed.netloc:
                vid_local = parse_qs(parsed.query).get('v', [None])[0]
            elif 'youtu.be' in parsed.netloc:
                vid_local = parsed.path[1:]
        except Exception:
            pass
        camel = _to_camel_case_lower_suffix(title)
        short_id = (vid_local or 'noid')[:8]
        return f"{idx:04d}_{short_id}_{camel}"

    def run_single(url: str, index: int):
        vid = None
        # Simple video_id extract
        try:
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            if 'youtube.com' in parsed.netloc:
                vid = parse_qs(parsed.query).get('v', [None])[0]
            elif 'youtu.be' in parsed.netloc:
                vid = parsed.path[1:]
        except Exception:
            vid = None
        if vid and vid in manifest_index and manifest_index[vid].get('status') == 'success':
            print("⏭️  Already downloaded (manifest) - skipping")
            return
        try:
            downloader._current_basename = _build_basename(index, url)
        except Exception:
            downloader._current_basename = None
        result = downloader.download_audio_pytube(url, index=index)
        downloader._current_basename = None
        if result:
            wav_file, duration = result
            print(f"✅ Saved: {wav_file} ({duration}s)")
            # Update manifest
            # Try to fetch full title for manifest
            title_val = ''
            try:
                yt_tmp2 = YouTube(url)
                title_val = yt_tmp2.title or ''
            except Exception:
                title_val = ''
            record = {
                'video_id': vid or '',
                'url': url,
                'output_path': wav_file,
                'status': 'success',
                'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                'duration_seconds': duration,
                'title': title_val
            }
            if vid:
                manifest_index[vid] = record
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

            _save_manifest(manifest_path, manifest_data)
        else:
            print("❌ Download failed")

    if not args:
        if default_urls_file.exists():
            urls = [line.strip() for line in default_urls_file.read_text(encoding='utf-8').splitlines() if line.strip().startswith('http')]
            print(f"📋 Batch download from: {default_urls_file} ({len(urls)} URLs)")
            for idx, url in enumerate(urls, start=1):
                print(f"\n===== [{idx}/{len(urls)}] {url} =====")
                run_single(url, idx)
            print("\n🎉 Batch download completed")
        else:
            print("⚠️ No URLs file found. Usage: python youtube_audio_downloader_alternative.py <url>|--from-file <path>")
            test_with_sample_video()
    else:
        # Support --from-file <path> or direct URL(s)
        if args[0] == '--from-file' and len(args) >= 2:
            file_path = Path(args[1])
            if not file_path.exists():
                print("❌ URLs file not found")
                sys.exit(1)
            urls = [line.strip() for line in file_path.read_text(encoding='utf-8').splitlines() if line.strip().startswith('http')]
            print(f"📋 Batch download from: {file_path} ({len(urls)} URLs)")
            for idx, url in enumerate(urls, start=1):
                print(f"\n===== [{idx}/{len(urls)}] {url} =====")
                run_single(url, idx)
            print("\n🎉 Batch download completed")
        else:
            for i, url in enumerate(args, start=1):
                run_single(url, i)
