#!/usr/bin/env python3
"""
Debug concurrent filtering by monitoring locks in real-time
"""

import requests
import time
import json
from concurrent.futures import ThreadPoolExecutor

def start_filtering_task():
    """Start a single filtering task and return task ID"""
    try:
        response = requests.post("http://localhost:8000/filter", json={"dry_run": False})
        result = response.json()
        if result.get('success'):
            return result.get('task_id')
        else:
            print(f"Failed to start task: {result.get('message')}")
            return None
    except Exception as e:
        print(f"Error starting task: {e}")
        return None

def monitor_locks_and_tasks():
    """Monitor locks and task status simultaneously"""
    print("Starting 2 filtering tasks with detailed monitoring...")
    
    # Start tasks with short delay
    task1 = start_filtering_task()
    time.sleep(0.5)  # Small delay
    task2 = start_filtering_task()
    
    if not task1 or not task2:
        print("Failed to start tasks")
        return
    
    print(f"Started tasks: {task1}, {task2}")
    
    # Monitor for 15 seconds
    for i in range(15):
        try:
            # Get locks info
            locks_response = requests.get("http://localhost:8000/locks")
            locks_data = locks_response.json()
            
            # Get task status
            task1_response = requests.get(f"http://localhost:8000/status/{task1}")
            task2_response = requests.get(f"http://localhost:8000/status/{task2}")
            
            task1_data = task1_response.json()
            task2_data = task2_response.json()
            
            # Print status
            print(f"\n[{i+1:2d}] Time: {time.strftime('%H:%M:%S')}")
            print(f"    Locks: {locks_data.get('total_locked_records', 0)} records")
            
            # Show locked records
            for lock in locks_data.get('locked_records', [])[:3]:
                video_id = lock.get('video_id', 'unknown')[:10]
                locked_by = lock.get('locked_by_task', 'unknown')[:12]
                print(f"      • {video_id} locked by {locked_by}")
            
            # Show task progress
            for task_id, task_data, task_num in [(task1, task1_data, 1), (task2, task2_data, 2)]:
                status = task_data.get('status', 'unknown')
                progress = task_data.get('progress', {})
                current = progress.get('current', 0)
                total = progress.get('total', 0)
                current_file = progress.get('current_file', '')
                
                print(f"    Task {task_num} ({task_id[:8]}): {status} - {current}/{total}")
                if current_file:
                    print(f"      Processing: {current_file}")
                
                if status in ['completed', 'failed']:
                    if status == 'completed':
                        result = task_data.get('result', {})
                        processed = result.get('total_processed', 0)
                        print(f"      Result: {processed} records processed")
            
            # Check if both tasks are done
            if (task1_data.get('status') in ['completed', 'failed'] and 
                task2_data.get('status') in ['completed', 'failed']):
                print(f"\nBoth tasks completed!")
                break
                
        except Exception as e:
            print(f"Error monitoring: {e}")
        
        time.sleep(1)

if __name__ == "__main__":
    monitor_locks_and_tasks()