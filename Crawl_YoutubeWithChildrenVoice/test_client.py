#!/usr/bin/env python3
"""
Test Client for YouTube Output Filterer API - Client-Server Architecture

This script demonstrates how to use the YouTubeFiltererClient to:
1. Upload manifest and audio files to a remote server
2. Process them using the server's computational resources
3. Download the processed results back to the client machine

This allows you to utilize a powerful server's computing power while
modifying files on your local machine.
"""

import os
import json
import sys
from pathlib import Path

# Import the client class
from api_youtube_filterer import YouTubeFiltererClient

def test_client_workflow():
    """Test the complete client workflow."""
    print("=" * 60)
    print("YouTube Output Filterer - Client-Server Test")
    print("=" * 60)
    
    # Configuration
    server_url = "http://localhost:8001"
    manifest_path = "./final_audio_files/manifest.json"
    audio_files_dir = "./final_audio_files/audio_files"
    output_dir = "./test_processed_results"
    
    print(f"Server URL: {server_url}")
    print(f"Manifest: {manifest_path}")
    print(f"Audio files directory: {audio_files_dir}")
    print(f"Output directory: {output_dir}")
    print()
    
    # Check if files exist
    if not os.path.exists(manifest_path):
        print(f"❌ Manifest file not found: {manifest_path}")
        print("Please ensure you have a manifest.json file in the final_audio_files directory")
        return False
    
    if not os.path.exists(audio_files_dir):
        print(f"❌ Audio files directory not found: {audio_files_dir}")
        print("Please ensure you have audio files in the final_audio_files/audio_files directory")
        return False
    
    # Count audio files
    audio_files = [f for f in os.listdir(audio_files_dir) if f.endswith(('.wav', '.mp3', '.m4a'))]
    print(f"Found {len(audio_files)} audio files in {audio_files_dir}")
    
    if len(audio_files) == 0:
        print("❌ No audio files found to process")
        return False
    
    # Initialize client
    print("\n🔗 Connecting to server...")
    client = YouTubeFiltererClient(server_url)
    
    try:
        # Test server health
        import requests
        response = requests.get(f"{server_url}/health")
        if response.status_code != 200:
            print(f"❌ Server not responding: {response.status_code}")
            return False
        
        health_data = response.json()
        print(f"✅ Server is healthy: {health_data['status']}")
        print(f"   Audio classifier ready: {health_data['audio_classifier_ready']}")
        print(f"   Active sessions: {health_data['active_sessions']}")
        
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Make sure the server is running with: python start_api.py --port 8001")
        return False
    
    # Perform dry run first
    print("\n🔍 Performing dry run to see what would be processed...")
    try:
        dry_run_result = client.upload_and_process(
            manifest_path=manifest_path,
            audio_files_dir=audio_files_dir,
            dry_run=True
        )
        
        if dry_run_result.get('success'):
            dry_run_data = dry_run_result.get('dry_run_results', {})
            unclassified_count = dry_run_data.get('unclassified_count', 0)
            print(f"✅ Dry run completed")
            print(f"   Files to process: {unclassified_count}")
            
            if unclassified_count == 0:
                print("ℹ️  No unclassified files found. All files may already be processed.")
                return True
            
            # Show sample files
            files_to_process = dry_run_data.get('files_to_process', [])
            print("   Sample files that would be processed:")
            for file_info in files_to_process[:5]:  # Show first 5
                print(f"     - {file_info['filename']} (uploaded: {file_info['file_uploaded']})")
            
            if dry_run_data.get('additional_files', 0) > 0:
                print(f"     ... and {dry_run_data['additional_files']} more files")
        else:
            print(f"❌ Dry run failed: {dry_run_result.get('error')}")
            return False
    
    except Exception as e:
        print(f"❌ Dry run error: {e}")
        return False
    
    # Ask for confirmation
    print(f"\n❓ Do you want to proceed with actual processing of {unclassified_count} files? (y/N): ", end="")
    try:
        response = input().strip().lower()
        if response not in ['y', 'yes']:
            print("Processing cancelled by user")
            return True
    except KeyboardInterrupt:
        print("\nProcessing cancelled by user")
        return True
    
    # Perform actual processing
    print(f"\n🚀 Starting complete workflow...")
    print("This will: upload files → process → download results")
    
    try:
        result = client.process_complete_workflow(
            manifest_path=manifest_path,
            audio_files_dir=audio_files_dir,
            output_dir=output_dir,
            dry_run=False
        )
        
        if result.get('success'):
            print("✅ Complete workflow finished successfully!")
            print(f"   Session ID: {result.get('session_id')}")
            print(f"   Task ID: {result.get('task_id')}")
            print(f"   Output directory: {result.get('output_dir')}")
            print(f"   Results ZIP: {result.get('results_zip')}")
            
            # Show processing statistics
            stats = result.get('processing_stats', {})
            if stats:
                print("   Processing statistics:")
                print(f"     - Total processed: {stats.get('total_processed', 0)}")
                print(f"     - Files kept: {stats.get('files_kept', 0)}")
                print(f"     - Files deleted: {stats.get('files_deleted', 0)}")
                print(f"     - Processing time: {stats.get('processing_time', 0):.2f}s")
            
            print(f"\n📁 Check the results in: {output_dir}")
            return True
        else:
            print(f"❌ Workflow failed: {result.get('error')}")
            return False
    
    except Exception as e:
        print(f"❌ Workflow error: {e}")
        return False

def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print(__doc__)
        print("\nUsage:")
        print("  python test_client.py          # Run the test workflow")
        print("  python test_client.py --help   # Show this help")
        return
    
    success = test_client_workflow()
    
    if success:
        print("\n✅ Client test completed successfully!")
        print("\nNext steps:")
        print("1. Check the processed results in the output directory")
        print("2. The updated manifest.json shows which files were kept/deleted")
        print("3. Only files with children's voices are kept")
        print("4. The server's computational power was used for processing")
    else:
        print("\n❌ Client test failed!")
        print("\nTroubleshooting:")
        print("1. Make sure the server is running: python start_api.py --port 8001")
        print("2. Ensure you have audio files in final_audio_files/audio_files/")
        print("3. Check that manifest.json exists and references the audio files")

if __name__ == "__main__":
    main()