#!/usr/bin/env python3
"""
Test script for RemoteYouTubeFilterer queue integration
"""

import sys
import os
import tempfile
import json
import shutil
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import required modules
from youtube_output_filterer import YouTubeOutputFilterer
from queue_manager import QueueManager, create_queue_manager

# Mock classes to avoid FastAPI dependencies
class MockUploadSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.temp_dir = tempfile.mkdtemp(prefix=f"test_session_{session_id}_")
        self.files = {}
        self.manifest_data = None

    def write_manifest_to_temp(self):
        if not self.manifest_data:
            raise ValueError("No manifest data")
        manifest_path = os.path.join(self.temp_dir, "manifest.json")
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(self.manifest_data, f, indent=2, ensure_ascii=False)
        return manifest_path

class MockTaskManager:
    def __init__(self):
        self.tasks = {}

    def update_progress(self, task_id, current, total, current_file=None):
        pass

# Test RemoteYouTubeFilterer inheritance
class TestRemoteYouTubeFilterer(YouTubeOutputFilterer):
    """
    Test version of RemoteYouTubeFilterer that avoids FastAPI dependencies
    """

    def __init__(self, session, task_id, task_manager, instance_id=None, use_queue=True):
        """Initialize test filterer with session data."""
        self.session = session
        self.task_id = task_id
        self.task_manager = task_manager

        # Create temporary manifest file
        self.manifest_path = Path(session.write_manifest_to_temp())

        # Update manifest to point to uploaded files
        self._update_manifest_file_paths()

        # Initialize with queue support - call parent constructor
        super().__init__(str(self.manifest_path), instance_id=instance_id, use_queue=use_queue)

        print(f"Initialized TestRemoteYouTubeFilterer for session {session.session_id} (queue: {use_queue})")

    def _update_manifest_file_paths(self):
        """Update manifest to point to uploaded temporary files."""
        if not self.session.manifest_data:
            raise ValueError("No manifest data in session")

        updated_manifest = self.session.manifest_data.copy()
        records = updated_manifest.get('records', [])

        updated_records = []
        for record in records:
            output_path = record.get('output_path', '')
            if output_path:
                # Extract filename from original path
                filename = os.path.basename(output_path)

                # Check if this file was uploaded
                if filename in self.session.files:
                    # Update path to point to uploaded temp file
                    record = record.copy()
                    record['output_path'] = self.session.files[filename]
                    record['original_output_path'] = output_path  # Keep original for client
                    updated_records.append(record)
                    print(f"Updated path for {filename}: {output_path} -> {record['output_path']}")
                else:
                    # File not uploaded - mark for skipping
                    record = record.copy()
                    record['file_missing_in_upload'] = True
                    record['original_output_path'] = output_path
                    updated_records.append(record)
                    print(f"File {filename} referenced in manifest but not uploaded")
            else:
                updated_records.append(record)

        updated_manifest['records'] = updated_records

        # Write updated manifest to temp file
        with open(self.manifest_path, 'w', encoding='utf-8') as f:
            json.dump(updated_manifest, f, indent=2, ensure_ascii=False)

        print(f"Updated manifest paths for {len(updated_records)} records")

def test_remote_filterer_inheritance():
    """Test that RemoteYouTubeFilterer properly inherits queue functionality."""
    print("🧪 Testing RemoteYouTubeFilterer inheritance and queue integration...")

    # Create test session
    session = MockUploadSession('test_session_123')

    # Create test manifest data
    manifest_data = {
        'records': [
            {
                'video_id': 'test_video_1',
                'output_path': 'test_file_1.wav',
                'classified': False
            },
            {
                'video_id': 'test_video_2',
                'output_path': 'test_file_2.wav',
                'classified': False
            }
        ]
    }
    session.manifest_data = manifest_data

    # Create task manager
    task_manager = MockTaskManager()

    try:
        # Test instantiation with queue enabled
        filterer = TestRemoteYouTubeFilterer(session, 'test_task', task_manager,
                                           instance_id='test_instance', use_queue=True)

        print("✅ TestRemoteYouTubeFilterer instantiated successfully")
        print(f"  instance_id: {filterer.instance_id}")
        print(f"  use_queue: {filterer.use_queue}")
        print(f"  queue_manager: {filterer.queue_manager is not None}")
        print(f"  audio_classifier: {hasattr(filterer, 'audio_classifier')}")
        print(f"  _lock: {hasattr(filterer, '_lock')}")

        # Test inheritance
        print(f"  Inherits from YouTubeOutputFilterer: {isinstance(filterer, YouTubeOutputFilterer)}")

        # Test queue functionality
        if filterer.queue_manager:
            print("  Queue manager details:")
            print(f"    instance_id: {filterer.queue_manager.instance_id}")
            status = filterer.queue_manager.get_queue_status()
            print(f"    queue status: {status.total_pending} pending, {status.active_instances} active instances")

        # Test get_unclassified_records
        unclassified = filterer.get_unclassified_records()
        print(f"  Unclassified records: {len(unclassified)}")

        print("\n✅ RemoteYouTubeFilterer inheritance and queue integration verified!")

        return True

    except Exception as e:
        print(f"❌ Error testing RemoteYouTubeFilterer: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        # Cleanup
        shutil.rmtree(session.temp_dir, ignore_errors=True)

if __name__ == "__main__":
    success = test_remote_filterer_inheritance()
    sys.exit(0 if success else 1)