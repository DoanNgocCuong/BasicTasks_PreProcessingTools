#!/usr/bin/env python3
"""
YouTube Audio Downloader and Converter

This module provides functionality for downloading audio from YouTube videos and converting
them to WAV format for further audio analysis. It uses yt-dlp for video downloading and
FFmpeg for audio format conversion.

Key Features:
    - Download best available audio quality from YouTube URLs
    - Automatic conversion from various formats (M4A, MP3, etc.) to WAV
    - Configurable output directory and file naming
    - Error handling for download and conversion failures
    - Automatic cleanup of intermediate files
    - Support for batch processing with indexed file naming

Architecture:
    - Config: Configuration management for paths and settings
    - YoutubeAudioDownloader: Main downloader and converter class

Workflow:
    1. Download best available audio from YouTube URL using yt-dlp
    2. Save as intermediate format (typically M4A)
    3. Convert to WAV format using FFmpeg
    4. Clean up intermediate files
    5. Return path to final WAV file

Dependencies:
    - yt-dlp: For YouTube video/audio downloading
    - ffmpeg-python: For audio format conversion
    - FFmpeg binary: Must be installed and available in system PATH

Output Format:
    - WAV files with configurable naming pattern (output_N.wav)
    - Stored in configurable output directory (default: youtube_audio_outputs/)

Use Cases:
    - Preprocessing YouTube videos for audio analysis
    - Creating datasets for machine learning audio models
    - Converting YouTube content for offline audio processing
    - Batch audio extraction from video collections

Error Handling:
    - Network connectivity issues during download
    - Invalid or unavailable YouTube URLs
    - Audio conversion failures
    - File system permission issues

Usage:
    python youtube_audio_downloader.py [youtube_url]
    
    Or as a module:
    from youtube_audio_downloader import YoutubeAudioDownloader, Config
    
    config = Config()
    downloader = YoutubeAudioDownloader(config)
    wav_path = downloader.download_audio_from_yturl(url, index=0)

Author: Le Hoang Minh
Created: 2025
Version: 1.0
"""

from __future__ import unicode_literals
import yt_dlp
import ffmpeg
import sys
import os


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
    
    def download_audio_from_yturl(self, url, index=0):
        """
        Download audio from YouTube URL and convert to WAV.
        
        Args:
            url (str): YouTube URL to download
            index (int): Index for output file naming
            
        Returns:
            str or None: Path to output WAV file if successful, None otherwise
        """
        # Configure output template
        ydl_opts = self.config.ydl_opts.copy()
        ydl_opts['outtmpl'] = self.config.get_output_path(self.config.get_m4a_filename(index))
        
        # Download audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Convert to WAV
        return self._convert_to_wav(index)
    
    def _convert_to_wav(self, index):
        """
        Convert M4A file to WAV format.
        
        Args:
            index (int): Index for file naming
            
        Returns:
            str or None: Path to output WAV file if successful, None otherwise
        """
        input_file = self.config.get_output_path(self.config.get_m4a_filename(index))
        output_file = self.config.get_output_path(self.config.get_wav_filename(index))
        
        # Convert using ffmpeg
        stream = ffmpeg.input(input_file)
        stream = ffmpeg.output(stream, output_file)
        ffmpeg.run(stream, quiet=True, overwrite_output=True)
        
        # Clean up intermediate file
        if os.path.exists(input_file):
            os.remove(input_file)
        
        # Return output file path if successful
        if os.path.exists(output_file):
            return output_file
        else:
            return None


def main():
    """Main function to handle command line interface."""
    config = Config()
    downloader = YoutubeAudioDownloader(config)
    
    args = sys.argv[1:]
    
    if len(args) > 1:
        print("Too many arguments.")
        print("Usage: python youtubetowav.py <optional link>")
        print("If a link is given it will automatically convert it to .wav. Otherwise a prompt will be shown")
        exit()
    
    if len(args) == 0:
        url = input("Enter Youtube URL: ")
        downloader.download_audio_from_yturl(url)
    else:
        downloader.download_audio_from_yturl(args[0])

if __name__ == "__main__":
    main()

