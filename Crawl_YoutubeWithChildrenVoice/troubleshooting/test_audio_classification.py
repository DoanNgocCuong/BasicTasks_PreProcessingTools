#!/usr/bin/env python3
"""
Test audio classification logic with dummy files
"""

import json
import os
import shutil
import tempfile
import numpy as np
import soundfile as sf
from datetime import datetime
from youtube_output_filterer import YouTubeOutputFilterer

def create_dummy_audio_file(filepath, duration=2.0, sample_rate=16000):
    """Create a dummy audio file for testing"""
    # Generate simple sine wave
    t = np.linspace(0, duration, int(sample_rate * duration))
    frequency = 440  # A4 note
    audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    # Save as WAV file
    sf.write(filepath, audio_data, sample_rate)
    print(f"Created dummy audio file: {filepath}")

def test_audio_classification():
    """Test the filterer with actual audio files"""
    print("\n" + "="*50)
    print("TESTING AUDIO CLASSIFICATION")
    print("="*50)
    
    # Create backup first
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"final_audio_files/manifest.backup_audio_test_{timestamp}.json"
    shutil.copy2("final_audio_files/manifest.json", backup_path)
    print(f"Created backup: {backup_path}")
    
    # Create temporary directory for test audio files
    temp_dir = tempfile.mkdtemp(prefix="filterer_test_")
    print(f"Using temp directory: {temp_dir}")
    
    try:
        # Load manifest and modify first few records
        with open('final_audio_files/manifest.json', 'r', encoding='utf-8') as f:
            manifest = json.load(f)
        
        records = manifest.get('records', [])
        test_count = min(3, len(records))  # Test with 3 records
        
        # Create dummy audio files and update paths
        for i in range(test_count):
            record = records[i]
            # Create new path in temp directory
            new_filename = f"test_audio_{i+1}.wav"
            new_path = os.path.join(temp_dir, new_filename)
            
            # Create dummy audio file
            create_dummy_audio_file(new_path)
            
            # Update record
            record['classified'] = False
            record['output_path'] = new_path
            if 'classification_timestamp' in record:
                del record['classification_timestamp']
        
        # Save modified manifest
        with open('final_audio_files/manifest.json', 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        print(f"Modified {test_count} records with dummy audio files")
        
        # Run the filterer
        print("\nRunning filterer on dummy audio files...")
        result = YouTubeOutputFilterer.run_filterer()
        
        print(f"\nAudio Classification Test Results:")
        print(f"  Total processed: {result.total_processed}")
        print(f"  Files kept: {result.files_kept}")
        print(f"  Files deleted: {result.files_deleted}")
        print(f"  Files not found: {result.files_not_found}")
        print(f"  Errors: {result.errors}")
        print(f"  Processing time: {result.processing_time:.2f} seconds")
        
        if result.error_details:
            print(f"\nError details:")
            for error in result.error_details:
                print(f"  - {error}")
        
        # Check what happened to our test files
        print(f"\nChecking test files:")
        for i in range(test_count):
            test_file = os.path.join(temp_dir, f"test_audio_{i+1}.wav")
            exists = os.path.exists(test_file)
            print(f"  test_audio_{i+1}.wav: {'EXISTS' if exists else 'DELETED'}")
        
    finally:
        # Cleanup
        print(f"\nCleaning up...")
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"Removed temp directory: {temp_dir}")
        
        # Restore original manifest
        shutil.copy2(backup_path, "final_audio_files/manifest.json")
        print(f"Restored manifest from: {backup_path}")
        print("Audio classification test completed!")

if __name__ == "__main__":
    test_audio_classification()