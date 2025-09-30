#!/usr/bin/env python3
"""
Process Remaining URLs - Download and validate all URLs that haven't been processed yet

This script will:
1. Load the manifest.csv to see which URLs have already been downloaded
2. Read all URLs from multi_query_collected_video_urls.txt  
3. Process only the URLs that aren't in the manifest
4. Save validated audio files to final_audio_files directory
5. Update the manifest with processing results
"""

import os
import sys
from pathlib import Path

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from process_remaining_urls import TikTokAudioProcessor

def main():
    """Main function to process remaining URLs."""
    print("🚀 Starting TikTok Remaining URLs Processor...")
    print("=" * 60)
    
    try:
        # Initialize the processor
        processor = TikTokAudioProcessor()
        
        # Run the processing
        success = processor.process_remaining_urls()
        
        if success:
            print("\n🎉 Processing completed successfully!")
        else:
            print("\n❌ Processing completed with errors.")
            
    except KeyboardInterrupt:
        print("\n⚠️  Processing interrupted by user")
    except Exception as e:
        print(f"\n❌ Processing failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()