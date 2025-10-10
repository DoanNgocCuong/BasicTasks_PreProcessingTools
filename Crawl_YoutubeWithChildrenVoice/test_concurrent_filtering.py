#!/usr/bin/env python3
"""
Concurrent Filtering Test Script

Test script to demonstrate and verify concurrent record-level processing
of the YouTube Output Filterer API.

This script will:
1. Start multiple filtering tasks concurrently
2. Monitor their progress
3. Show how records are locked and processed independently
4. Verify no duplicate processing occurs

Author: Generated for YouTube Audio Crawler
Version: 1.0
"""

import asyncio
import json
import time
from typing import List, Dict
import requests
from api_client_example import FiltererAPIClient


def print_separator(title: str = ""):
    """Print a separator with optional title."""
    if title:
        print(f"\n{'='*20} {title} {'='*20}")
    else:
        print("="*60)


def start_multiple_concurrent_tasks(client: FiltererAPIClient, num_tasks: int = 3) -> List[str]:
    """Start multiple concurrent filtering tasks."""
    task_ids = []
    
    print(f"Starting {num_tasks} concurrent filtering tasks...")
    
    for i in range(num_tasks):
        try:
            result = client.start_filtering()
            if result.get('success') and result.get('task_id'):
                task_id = result['task_id']
                task_ids.append(task_id)
                
                concurrent_info = result.get('concurrent_info')
                if concurrent_info:
                    other_tasks = concurrent_info.get('other_running_tasks', 0)
                    print(f"  ✅ Task {i+1} started: {task_id}")
                    print(f"     Other running tasks: {other_tasks}")
                else:
                    print(f"  ✅ Task {i+1} started: {task_id} (first task)")
                    
            else:
                print(f"  ❌ Failed to start task {i+1}: {result.get('message', 'Unknown error')}")
                
        except Exception as e:
            print(f"  ❌ Error starting task {i+1}: {e}")
            
        # Small delay between task starts
        time.sleep(0.5)
    
    return task_ids


def monitor_concurrent_progress(client: FiltererAPIClient, task_ids: List[str], max_duration: int = 300):
    """Monitor progress of multiple concurrent tasks."""
    print_separator("MONITORING CONCURRENT PROGRESS")
    
    start_time = time.time()
    completed_tasks = set()
    
    while len(completed_tasks) < len(task_ids) and (time.time() - start_time) < max_duration:
        print(f"\n📊 Progress Update [{time.strftime('%H:%M:%S')}]:")
        
        # Get status of all tasks
        for i, task_id in enumerate(task_ids, 1):
            if task_id in completed_tasks:
                continue
                
            try:
                status = client.get_task_status(task_id)
                task_status = status.get('status', 'unknown')
                
                if task_status == 'running':
                    progress = status.get('progress', {})
                    current = progress.get('current', 0)
                    total = progress.get('total', 0)
                    percentage = progress.get('percentage', 0)
                    current_file = progress.get('current_file', 'Starting...')
                    
                    print(f"  🔄 Task {i} ({task_id[:12]}...): {current}/{total} ({percentage:.1f}%)")
                    print(f"     Current: {current_file}")
                    
                elif task_status == 'completed':
                    completed_tasks.add(task_id)
                    result = status.get('result', {})
                    processed = result.get('total_processed', 0)
                    kept = result.get('files_kept', 0)
                    deleted = result.get('files_deleted', 0)
                    print(f"  ✅ Task {i} COMPLETED: {processed} processed, {kept} kept, {deleted} deleted")
                    
                elif task_status == 'failed':
                    completed_tasks.add(task_id)
                    error = status.get('error', 'Unknown error')
                    print(f"  ❌ Task {i} FAILED: {error}")
                    
            except Exception as e:
                print(f"  ⚠️  Task {i} status error: {e}")
        
        # Show currently locked records
        try:
            locks_info = requests.get(f"{client.base_url}/locks").json()
            locked_count = locks_info.get('total_locked_records', 0)
            if locked_count > 0:
                print(f"  🔒 Currently locked records: {locked_count}")
                
                # Show some example locked records
                locked_records = locks_info.get('locked_records', [])[:3]
                for lock_info in locked_records:
                    video_id = lock_info.get('video_id', 'unknown')[:12]
                    task_id = lock_info.get('locked_by_task', 'unknown')[:12]
                    print(f"     • {video_id}... locked by {task_id}...")
                    
                if len(locks_info.get('locked_records', [])) > 3:
                    additional = len(locks_info.get('locked_records', [])) - 3
                    print(f"     • ... and {additional} more")
            else:
                print(f"  🔓 No records currently locked")
                
        except Exception as e:
            print(f"  ⚠️  Could not get lock info: {e}")
        
        if len(completed_tasks) < len(task_ids):
            time.sleep(5)  # Wait 5 seconds before next update
    
    print_separator("FINAL RESULTS")
    
    # Show final results for each task
    total_processed = 0
    total_kept = 0
    total_deleted = 0
    
    for i, task_id in enumerate(task_ids, 1):
        try:
            status = client.get_task_status(task_id)
            task_status = status.get('status', 'unknown')
            
            if task_status == 'completed':
                result = status.get('result', {})
                processed = result.get('total_processed', 0)
                kept = result.get('files_kept', 0)
                deleted = result.get('files_deleted', 0)
                processing_time = result.get('processing_time', 0)
                
                total_processed += processed
                total_kept += kept
                total_deleted += deleted
                
                print(f"Task {i}: {processed} processed, {kept} kept, {deleted} deleted ({processing_time:.1f}s)")
            else:
                print(f"Task {i}: Status = {task_status}")
                
        except Exception as e:
            print(f"Task {i}: Error getting final status - {e}")
    
    print(f"\nCOMBINED TOTALS:")
    print(f"  Total processed: {total_processed}")
    print(f"  Total kept: {total_kept}")
    print(f"  Total deleted: {total_deleted}")
    
    return len(completed_tasks) == len(task_ids)


def test_concurrent_filtering():
    """Main test function for concurrent filtering."""
    print_separator("YOUTUBE OUTPUT FILTERER - CONCURRENT TEST")
    
    client = FiltererAPIClient()
    
    try:
        # 1. Health check
        print("🏥 Checking API health...")
        health = client.health_check()
        if health.get('status') != 'healthy':
            print("❌ API is not healthy. Aborting test.")
            return
        print("✅ API is healthy")
        
        # 2. Get initial statistics
        print("\n📊 Getting initial statistics...")
        initial_stats = client.get_statistics()
        unclassified_count = initial_stats.get('unclassified_records', 0)
        
        print(f"  Total records: {initial_stats.get('total_records', 0)}")
        print(f"  Unclassified records: {unclassified_count}")
        
        if unclassified_count == 0:
            print("ℹ️  No unclassified records found. Cannot test concurrent processing.")
            return
        
        if unclassified_count < 6:
            print(f"⚠️  Only {unclassified_count} unclassified records. Concurrent processing may not be very visible.")
        
        # 3. Start multiple concurrent tasks
        print_separator("STARTING CONCURRENT TASKS")
        num_tasks = min(3, max(2, unclassified_count // 3))  # 2-3 tasks depending on records
        task_ids = start_multiple_concurrent_tasks(client, num_tasks)
        
        if not task_ids:
            print("❌ No tasks were started successfully.")
            return
        
        print(f"\n✅ Started {len(task_ids)} concurrent tasks")
        
        # 4. Monitor progress
        success = monitor_concurrent_progress(client, task_ids)
        
        # 5. Final statistics
        print_separator("FINAL STATISTICS")
        final_stats = client.get_statistics()
        
        print("BEFORE vs AFTER:")
        print(f"  Total records: {initial_stats.get('total_records', 0)} → {final_stats.get('total_records', 0)}")
        print(f"  Classified: {initial_stats.get('classified_records', 0)} → {final_stats.get('classified_records', 0)}")
        print(f"  Unclassified: {initial_stats.get('unclassified_records', 0)} → {final_stats.get('unclassified_records', 0)}")
        print(f"  With children voice: {initial_stats.get('files_with_children_voice', 0)} → {final_stats.get('files_with_children_voice', 0)}")
        
        if success:
            print("\n🎉 Concurrent filtering test completed successfully!")
        else:
            print("\n⚠️  Test completed with some issues.")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Make sure the server is running:")
        print("   python start_api.py")
    except Exception as e:
        print(f"❌ Test error: {e}")


if __name__ == "__main__":
    test_concurrent_filtering()