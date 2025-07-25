#!/usr/bin/env python3
"""
YouTube Audio Downloader and Converter with Video Length Tracking

This module provides functionality for downloading audio from YouTube videos and converting
them to WAV format for further audio analysis. It uses yt-dlp for video downloading and
FFmpeg for audio format conversion, with enhanced capabilities for video duration tracking.

Author: Le Hoang Minh
"""

from __future__ import unicode_literals
import yt_dlp
import ffmpeg
import sys
import os
import json


class Config:
    """Configuration class to store paths and settings."""
    
    def __init__(self):
        # Determine the parent directory of the script
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        # Store audio in youtube_audio_outputs relative to the parent directory
        self.output_dir = os.path.join(self.base_dir, 'youtube_audio_outputs')
        
        # Audio format settings
        self.ydl_opts = {
            'format': 'bestaudio/best'
        }
        
        # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)
    
    def get_output_path(self, filename):
        """Get the full path for an output file."""
        return os.path.join(self.output_dir, filename)
    
    def get_m4a_filename(self, index):
        """Get the m4a filename for a given index."""
        return f'output_{index}.m4a'
    
    def get_wav_filename(self, index):
        """Get the wav filename for a given index."""
        return f'output_{index}.wav'


class YoutubeAudioDownloader:
    """Class to handle YouTube audio downloading and conversion."""
    
    def __init__(self, config):
        self.config = config
    
    def get_video_info_with_duration(self, url):
        """
        Get video information including duration without downloading.
        
        Args:
            url (str): YouTube URL to get information from
            
        Returns:
            dict or None: Video information with duration if successful, None otherwise
            Dictionary contains: {'duration': float, 'title': str, 'uploader': str, etc.}
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info is not None:
                    duration_raw = info.get('duration')
                    return {
                        'duration': float(duration_raw) if duration_raw is not None else None,
                        'title': info.get('title', ''),
                        'uploader': info.get('uploader', ''),
                        'upload_date': info.get('upload_date', ''),
                        'view_count': info.get('view_count', 0),
                        'like_count': info.get('like_count', 0),
                        'description': info.get('description', '')
                    }
                return None
        except Exception as e:
            print(f"⚠️ Error getting video info: {e}")
            return None

    def get_video_duration(self, url):
        """
        Get video duration from YouTube URL without downloading.
        
        Args:
            url (str): YouTube URL to get duration from
            
        Returns:
            float or None: Video duration in seconds if successful, None otherwise
        """
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info is not None:
                    duration = info.get('duration')
                    return float(duration) if duration is not None else None
                return None
        except Exception as e:
            print(f"⚠️ Error getting video duration: {e}")
            return None
    
    def get_audio_length_from_file(self, audio_file_path):
        """
        Get audio length from an audio file using ffprobe.
        
        Args:
            audio_file_path (str): Path to the audio file
            
        Returns:
            float or None: Audio length in seconds if successful, None otherwise
        """
        try:
            probe = ffmpeg.probe(audio_file_path)
            duration = float(probe['streams'][0]['duration'])
            return duration
        except Exception as e:
            print(f"⚠️ Error getting audio length: {e}")
            return None
    
    def download_audio_from_yturl(self, url, index=0):
        """
        Download audio from YouTube URL and convert to WAV.
        
        Args:
            url (str): YouTube URL to download
            index (int): Index for output file naming
            
        Returns:
            tuple: (wav_file_path, audio_duration) where audio_duration is in seconds,
                   returns (None, None) if failed
        """
        # Get video duration first (without downloading)
        video_duration = self.get_video_duration(url)
        
        # Ensure output directory exists (thread-safe)
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # Clean up any existing files with the same index to prevent conflicts
        m4a_file = self.config.get_output_path(self.config.get_m4a_filename(index))
        wav_file = self.config.get_output_path(self.config.get_wav_filename(index))
        part_file = m4a_file + '.part'
        
        # Remove existing files that might cause conflicts
        for file_path in [m4a_file, wav_file, part_file]:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass  # File might be in use by another process
        
        # Configure output template
        ydl_opts = self.config.ydl_opts.copy()
        ydl_opts['outtmpl'] = m4a_file
        
        try:
            # Download audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            
            # Convert to WAV and get actual audio length
            wav_path, audio_length = self._convert_to_wav_with_duration(index)
            
            # Use actual audio length if available, otherwise fall back to video duration
            final_duration = audio_length if audio_length is not None else video_duration
            
            return wav_path, final_duration
            
        except Exception as e:
            print(f"⚠️ Error downloading audio: {e}")
            # Clean up any partial files on error
            for file_path in [m4a_file, wav_file, part_file]:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
            return None, None
    
    def _convert_to_wav_with_duration(self, index):
        """
        Convert M4A file to WAV format and return both path and duration.
        
        Args:
            index (int): Index for file naming
            
        Returns:
            tuple: (wav_file_path, audio_duration_seconds) or (None, None) if failed
        """
        input_file = self.config.get_output_path(self.config.get_m4a_filename(index))
        output_file = self.config.get_output_path(self.config.get_wav_filename(index))
        
        # Check if input file exists before conversion
        if not os.path.exists(input_file):
            print(f"⚠️ Input file not found: {input_file}")
            return None, None
        
        try:
            # Remove output file if it already exists to prevent conflicts
            if os.path.exists(output_file):
                try:
                    os.remove(output_file)
                except OSError:
                    pass
            
            # Convert using ffmpeg
            stream = ffmpeg.input(input_file)
            stream = ffmpeg.output(stream, output_file)
            ffmpeg.run(stream, quiet=True, overwrite_output=True)
            
            # Verify conversion was successful
            if not os.path.exists(output_file):
                print(f"⚠️ Conversion failed: output file not created")
                return None, None
            
            # Get audio duration from the converted WAV file
            audio_duration = None
            try:
                audio_duration = self.get_audio_length_from_file(output_file)
            except Exception as duration_error:
                print(f"⚠️ Warning: Could not get audio duration: {duration_error}")
                # Continue anyway, duration is not critical
            
            # Clean up intermediate file
            if os.path.exists(input_file):
                try:
                    os.remove(input_file)
                except OSError as cleanup_error:
                    print(f"⚠️ Warning: Could not remove intermediate file: {cleanup_error}")
            
            return output_file, audio_duration
                
        except Exception as e:
            print(f"⚠️ Error converting to WAV: {e}")
            # Clean up both intermediate and output files on error
            for file_path in [input_file, output_file]:
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
            return None, None
    
    def _convert_to_wav(self, index):
        """
        Convert M4A file to WAV format.
        
        Args:
            index (int): Index for file naming
            
        Returns:
            str or None: Path to output WAV file if successful, None otherwise
        """
        wav_path, _ = self._convert_to_wav_with_duration(index)
        return wav_path


    def test_video_duration_extraction(self, url):
        """
        Test method to verify video duration extraction without downloading.
        
        Args:
            url (str): YouTube URL to test
            
        Returns:
            dict: Test results with duration and metadata
        """
        print(f"🧪 Testing video duration extraction for: {url}")
        
        # Test duration extraction
        duration = self.get_video_duration(url)
        print(f"📏 Video duration: {duration} seconds")
        if duration:
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            print(f"📏 Video duration formatted: {minutes}:{seconds:02d}")
        
        # Test full video info extraction
        video_info = self.get_video_info_with_duration(url)
        if video_info:
            print(f"📺 Video title: {video_info.get('title', 'N/A')}")
            print(f"👤 Uploader: {video_info.get('uploader', 'N/A')}")
            print(f"📅 Upload date: {video_info.get('upload_date', 'N/A')}")
            print(f"👁️ View count: {video_info.get('view_count', 'N/A')}")
        
        return {
            'url': url,
            'duration_seconds': duration,
            'video_info': video_info,
            'success': duration is not None
        }

def main():
    """Main function to handle command line interface."""
    config = Config()
    downloader = YoutubeAudioDownloader(config)
    
    args = sys.argv[1:]
    
    if len(args) > 2:
        print("Too many arguments.")
        print("Usage: python youtube_audio_downloader.py <optional link> [--test-duration]")
        print("If a link is given it will automatically convert it to .wav. Otherwise a prompt will be shown")
        print("Use --test-duration to test video duration extraction without downloading")
        exit()
    
    # Check for test duration flag
    test_duration = False
    if "--test-duration" in args:
        test_duration = True
        args.remove("--test-duration")
    
    if len(args) == 0:
        url = input("Enter Youtube URL: ")
        if test_duration:
            downloader.test_video_duration_extraction(url)
        else:
            result = downloader.download_audio_from_yturl(url)
            if isinstance(result, tuple):
                wav_path, duration = result
                print(f"✅ Audio downloaded to: {wav_path}")
                if duration:
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    print(f"📏 Video duration: {minutes}:{seconds:02d}")
            else:
                # Handle backward compatibility
                print(f"✅ Audio downloaded to: {result}")
    else:
        url = args[0]
        if test_duration:
            downloader.test_video_duration_extraction(url)
        else:
            result = downloader.download_audio_from_yturl(url)
            if isinstance(result, tuple):
                wav_path, duration = result
                print(f"✅ Audio downloaded to: {wav_path}")
                if duration:
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    print(f"📏 Video duration: {minutes}:{seconds:02d}")
            else:
                # Handle backward compatibility
                print(f"✅ Audio downloaded to: {result}")

if __name__ == "__main__":
    main()

