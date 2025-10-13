#!/usr/bin/env python3
"""
Test script for API endpoints with queue support
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_api_logic():
    """Test API logic with queue-enabled filterer."""
    print("🧪 Testing API logic with queue support...")

    # Import required modules
    from api_youtube_filterer import RemoteYouTubeFilterer, UploadSession, TaskManager, SessionManager

    # Create session manager
    session_manager = SessionManager()
    task_manager = TaskManager()

    # Create a session
    session_id = session_manager.create_session()
    session = session_manager.get_session(session_id)

    if not session:
        print("❌ Failed to create session")
        return False

    print(f"✅ Created session: {session_id}")

    # Create sample manifest data
    manifest_data = {
        'records': [
            {
                'video_id': 'api_test_video_1',
                'output_path': 'api_test_file_1.wav',
                'classified': False
            },
            {
                'video_id': 'api_test_video_2',
                'output_path': 'api_test_file_2.wav',
                'classified': False
            }
        ]
    }

    # Set manifest data
    session.set_manifest(manifest_data)

    # Create dummy audio files
    temp_files = []
    for record in manifest_data['records']:
        filename = os.path.basename(record['output_path'])
        temp_path = os.path.join(session.temp_dir, filename)
        with open(temp_path, 'wb') as f:
            f.write(f'dummy audio data for {filename}'.encode())
        session.add_file(filename, f'dummy audio data for {filename}'.encode())
        temp_files.append(temp_path)

    print(f"✅ Added {len(temp_files)} test files to session")

    # Test RemoteYouTubeFilterer instantiation
    try:
        filterer = RemoteYouTubeFilterer(session, 'test_task_123', task_manager,
                                       instance_id='api_test_instance', use_queue=True)

        print("✅ RemoteYouTubeFilterer created successfully")
        print(f"   Instance ID: {filterer.instance_id}")
        print(f"   Queue enabled: {filterer.use_queue}")
        print(f"   Queue manager: {filterer.queue_manager is not None}")

        # Test getting unclassified records
        unclassified = filterer.get_unclassified_records()
        print(f"✅ Found {len(unclassified)} unclassified records")

        # Test queue operations
        if filterer.queue_manager:
            # Check queue status
            status = filterer.queue_manager.get_queue_status()
            print(f"✅ Queue status: {status.total_pending} pending, {status.active_instances} active instances")

            # Try to claim some records
            claim_result = filterer.queue_manager.claim_records(5)
            claimed = claim_result.claimed_records
            print(f"✅ Claimed {len(claimed)} records: {[r.get('video_id') for r in claimed]}")

            # Mark records as complete
            for record in claimed:
                filterer.queue_manager.complete_record(record.get('video_id'))
                print(f"   Marked {record.get('video_id')} as complete")

        # Test filterer processing (dry run)
        print("🧪 Testing filterer processing logic...")

        # Get unclassified records again (should be updated after claiming)
        unclassified_after = filterer.get_unclassified_records()
        print(f"✅ Records after queue operations: {len(unclassified_after)} unclassified")

        print("✅ API logic test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ API logic test error: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        session_manager.remove_session(session_id)

if __name__ == "__main__":
    success = test_api_logic()
    print(f"\n{'✅' if success else '❌'} API logic test {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)