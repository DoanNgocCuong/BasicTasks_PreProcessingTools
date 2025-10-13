#!/usr/bin/env python3
"""
Test script for multi-instance queue coordination
"""

import sys
import os
import tempfile
import json
import shutil
import threading
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import required modules
from youtube_output_filterer import YouTubeOutputFilterer

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

def test_multi_instance_coordination():
    """Test that multiple instances coordinate via queue to avoid duplicate processing."""
    print("🧪 Testing multi-instance queue coordination...")

    # Create shared manifest data
    manifest_data = {
        'records': [
            {
                'video_id': 'shared_video_1',
                'output_path': 'shared_file_1.wav',
                'classified': False
            },
            {
                'video_id': 'shared_video_2',
                'output_path': 'shared_file_2.wav',
                'classified': False
            },
            {
                'video_id': 'shared_video_3',
                'output_path': 'shared_file_3.wav',
                'classified': False
            }
        ]
    }

    # Create shared session
    session = MockUploadSession('shared_session_123')
    session.manifest_data = manifest_data

    task_manager = MockTaskManager()

    results = []
    errors = []

    def run_instance(instance_id):
        """Run a single filterer instance."""
        try:
            filterer = TestRemoteYouTubeFilterer(session, f'task_{instance_id}', task_manager,
                                               instance_id=instance_id, use_queue=True)

            # Get records that this instance claims
            claimed_result = filterer.queue_manager.claim_records(10)  # Try to claim all
            claimed_records = claimed_result.claimed_records

            print(f"Instance {instance_id} claimed {len(claimed_records)} records: {[r.get('video_id') for r in claimed_records]}")

            # Process claimed records
            processed_count = 0
            for record in claimed_records:
                video_id = record.get('video_id')
                print(f"Instance {instance_id} processing {video_id}")

                # Simulate processing by marking as complete
                filterer.queue_manager.complete_record(video_id)
                processed_count += 1

                # Small delay to allow interleaving
                time.sleep(0.1)

            results.append({
                'instance_id': instance_id,
                'processed_count': processed_count,
                'claimed_records': [r.get('video_id') for r in claimed_records]
            })

        except Exception as e:
            print(f"Error in instance {instance_id}: {e}")
            errors.append(f"Instance {instance_id}: {e}")

    # Start multiple instances concurrently
    threads = []
    num_instances = 3

    print(f"Starting {num_instances} concurrent instances...")

    for i in range(num_instances):
        instance_id = f"instance_{i+1}"
        thread = threading.Thread(target=run_instance, args=(instance_id,))
        threads.append(thread)
        thread.start()

    # Wait for all instances to complete
    for thread in threads:
        thread.join()

    # Check results
    print("\n📊 Results summary:")
    total_processed = 0
    all_claimed_records = set()

    for result in results:
        print(f"  {result['instance_id']}: processed {result['processed_count']} records")
        print(f"    Claimed: {result['claimed_records']}")
        total_processed += result['processed_count']
        all_claimed_records.update(result['claimed_records'])

    print(f"\nTotal records processed across all instances: {total_processed}")
    print(f"Unique records claimed: {len(all_claimed_records)}")
    print(f"Expected unique records: {len(manifest_data['records'])}")

    # Verify no duplicates
    expected_records = {r['video_id'] for r in manifest_data['records']}
    if all_claimed_records == expected_records:
        print("✅ All expected records were claimed exactly once")
        success = True
    else:
        print("❌ Record claiming mismatch!")
        print(f"  Expected: {expected_records}")
        print(f"  Actual: {all_claimed_records}")
        success = False

    # Check for over-processing
    if total_processed == len(manifest_data['records']):
        print("✅ No duplicate processing detected")
    else:
        print(f"❌ Duplicate processing detected! Total processed: {total_processed}, expected: {len(manifest_data['records'])}")
        success = False

    if errors:
        print(f"❌ Errors occurred: {errors}")
        success = False

    # Cleanup
    shutil.rmtree(session.temp_dir, ignore_errors=True)

    return success

if __name__ == "__main__":
    success = test_multi_instance_coordination()
    print(f"\n{'✅' if success else '❌'} Multi-instance coordination test {'PASSED' if success else 'FAILED'}")
    sys.exit(0 if success else 1)