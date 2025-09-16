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
        
        # Generate unique output filename
        timestamp = int(time.time() * 1000)
        process_id = os.getpid()
        wav_file = self.output_dir / f"youtube_audio_pytube_{index}_{timestamp}_{process_id}.wav"
        temp_audio_file = None
        
        try:
            # Step 1: Download using pytube
            print("📡 Creating YouTube object...")
            yt = YouTube(url)
            
            print(f"📺 Video: {yt.title[:50]}...")
            print(f"📏 Duration: {yt.length//60}m {yt.length%60}s")
            
            # Check duration limit (5 minutes = 300 seconds)
            if yt.length > 300:
                print(f"⏭️  Video too long ({yt.length//60}m {yt.length%60}s > 5m), skipping...")
                return None
            
            # Get best audio stream
            print("🔍 Getting audio streams...")
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            
            if not audio_stream:
                print("❌ No audio streams available")
                return None
            
            print(f"🎯 Selected: {audio_stream.mime_type} - {audio_stream.abr}")
            
            # Download audio
            print("⏬ Downloading audio...")
            temp_filename = f"temp_audio_{index}_{timestamp}.{audio_stream.subtype}"
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
                stream = ffmpeg.output(
                    stream, 
                    str(wav_file),
                    acodec='pcm_s16le',  # WAV PCM format
                    ar=16000,  # 16kHz sample rate
                    ac=1,  # Mono
                    t=300  # Max 5 minutes
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
    downloader = YouTubeAudioDownloaderAlternative()

    def run_single(url: str, index: int):
        result = downloader.download_audio_pytube(url, index=index)
        if result:
            wav_file, duration = result
            print(f"✅ Saved: {wav_file} ({duration}s)")
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
