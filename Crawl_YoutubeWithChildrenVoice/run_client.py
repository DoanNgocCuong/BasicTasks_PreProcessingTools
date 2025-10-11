#!/usr/bin/env python3
"""
YouTube Output Filterer - Client Script

Simple script to run the client that connects to the API server
and processes your local files using the server's computational power.

Just run: python run_client.py
"""

import os
import sys
import json
from pathlib import Path

def main():
    print("=" * 60)
    print("🎵 YouTube Output Filterer - Client")
    print("=" * 60)
    print("This client will send your files to the server for processing")
    print("using the server's computational power.")
    print()
    
    # Configuration
    SERVER_URL = 'http://localhost:8001'  # Change this to your server's URL
    MANIFEST_PATH = './final_audio_files/manifest.json'
    AUDIO_DIR = './final_audio_files/audio_files'
    OUTPUT_DIR = './processed_results'
    
    print(f"🌐 Server URL: {SERVER_URL}")
    print(f"📄 Manifest: {MANIFEST_PATH}")
    print(f"🎵 Audio files: {AUDIO_DIR}")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print()
    
    # Check if files exist
    if not os.path.exists(MANIFEST_PATH):
        print(f"❌ Manifest not found: {MANIFEST_PATH}")
        print("Please ensure you have a manifest.json file in the final_audio_files directory")
        print("You can generate one using the YouTube crawler first.")
        return False
    
    if not os.path.exists(AUDIO_DIR):
        print(f"❌ Audio directory not found: {AUDIO_DIR}")
        print("Please ensure you have audio files in the final_audio_files/audio_files directory")
        return False
    
    # Count audio files
    audio_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith(('.wav', '.mp3', '.m4a', '.ogg'))]
    print(f"📊 Found {len(audio_files)} audio files")
    
    if len(audio_files) == 0:
        print("❌ No audio files found to process")
        return False
    
    try:
        # Import the client
        from api_youtube_filterer import YouTubeFiltererClient
        import requests
        
        print("🔗 Connecting to server...")
        client = YouTubeFiltererClient(SERVER_URL)
        
        # Test server connection
        try:
            response = requests.get(f"{SERVER_URL}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Server is healthy: {health_data['status']}")
                print(f"   Audio classifier ready: {health_data.get('audio_classifier_ready', 'unknown')}")
                print(f"   Active sessions: {health_data.get('active_sessions', 0)}")
            else:
                print(f"❌ Server responded with error: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot connect to server at {SERVER_URL}")
            print(f"   Error: {e}")
            print("   Make sure the server is running with: python start_api.py --port 8001")
            return False
        
        print()
        
        # Ask user what they want to do
        print("What would you like to do?")
        print("1. Dry run (preview what would be processed)")
        print("2. Full processing (upload, process, download)")
        print("3. Exit")
        
        try:
            choice = input("\nEnter your choice (1-3): ").strip()
        except KeyboardInterrupt:
            print("\n👋 Cancelled by user")
            return True
        
        if choice == '1':
            # Dry run
            print("\n🔍 Running dry run to preview what would be processed...")
            result = client.upload_and_process(
                manifest_path=MANIFEST_PATH,
                audio_files_dir=AUDIO_DIR,
                dry_run=True
            )
            
            if result.get('success'):
                dry_run_data = result.get('dry_run_results', {})
                unclassified_count = dry_run_data.get('unclassified_count', 0)
                print(f"\n✅ Dry run completed!")
                print(f"📊 Files that would be processed: {unclassified_count}")
                
                if unclassified_count > 0:
                    files_to_process = dry_run_data.get('files_to_process', [])
                    print("\n📋 Sample files that would be processed:")
                    for i, file_info in enumerate(files_to_process[:10], 1):
                        status = "✅" if file_info['file_uploaded'] else "❌"
                        print(f"   {i}. {status} {file_info['filename']}")
                    
                    if len(files_to_process) > 10:
                        remaining = dry_run_data.get('additional_files', 0)
                        print(f"   ... and {remaining} more files")
                else:
                    print("ℹ️  All files appear to be already processed.")
            else:
                print(f"❌ Dry run failed: {result.get('error')}")
                return False
                
        elif choice == '2':
            # Full processing
            print("\n🚀 Starting full processing workflow...")
            print("This will:")
            print("  1. Upload your manifest and audio files to the server")
            print("  2. Process them using the server's computational power")
            print("  3. Download the processed results back to your machine")
            print("  4. Update your local files")
            print()
            
            # Ask for final confirmation
            try:
                confirm = input("Continue? (y/N): ").strip().lower()
                if confirm not in ['y', 'yes']:
                    print("👋 Processing cancelled")
                    return True
            except KeyboardInterrupt:
                print("\n👋 Cancelled by user")
                return True
            
            print("\n📤 Starting upload and processing...")
            result = client.process_complete_workflow(
                manifest_path=MANIFEST_PATH,
                audio_files_dir=AUDIO_DIR,
                output_dir=OUTPUT_DIR
            )
            
            if result.get('success'):
                print("\n🎉 Processing completed successfully!")
                print(f"📁 Results saved to: {result.get('output_dir')}")
                print(f"🆔 Session ID: {result.get('session_id')}")
                print(f"🆔 Task ID: {result.get('task_id')}")
                
                # Show processing statistics
                stats = result.get('processing_stats', {})
                if stats:
                    print("\n📊 Processing Statistics:")
                    print(f"   Total processed: {stats.get('total_processed', 0)}")
                    print(f"   Files kept (children's voices): {stats.get('files_kept', 0)}")
                    print(f"   Files deleted (no children): {stats.get('files_deleted', 0)}")
                    print(f"   Processing time: {stats.get('processing_time', 0):.2f} seconds")
                
                print(f"\n✅ Your local files have been updated!")
                print(f"   Check the results in: {OUTPUT_DIR}")
            else:
                print(f"\n❌ Processing failed: {result.get('error')}")
                return False
                
        elif choice == '3':
            print("👋 Goodbye!")
            return True
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")
            return False
            
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import required modules: {e}")
        print("Make sure you're in the right directory and all dependencies are installed.")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    try:
        success = main()
        if success:
            print("\n✅ Client session completed successfully!")
        else:
            print("\n❌ Client session failed!")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Client stopped by user")
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)