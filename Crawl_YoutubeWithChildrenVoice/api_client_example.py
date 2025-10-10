#!/usr/bin/env python3
"""
YouTube Output Filterer API Client Example

Example client for interacting with the YouTube Output Filterer API.
Demonstrates how to use all API endpoints.

Author: Generated for YouTube Audio Crawler
Version: 1.0
"""

import asyncio
import json
import time
from typing import Optional

import aiohttp
import requests


class FiltererAPIClient:
    """Client for YouTube Output Filterer API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize client with API base URL."""
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def health_check(self) -> dict:
        """Check API health status."""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def get_statistics(self, manifest_path: Optional[str] = None) -> dict:
        """Get manifest statistics."""
        params = {}
        if manifest_path:
            params['manifest_path'] = manifest_path
        
        response = self.session.get(f"{self.base_url}/stats", params=params)
        response.raise_for_status()
        return response.json()
    
    def start_filtering(self, manifest_path: Optional[str] = None, dry_run: bool = False) -> dict:
        """Start filtering process."""
        data = {
            "manifest_path": manifest_path,
            "dry_run": dry_run
        }
        
        response = self.session.post(f"{self.base_url}/filter", json=data)
        response.raise_for_status()
        return response.json()
    
    def get_task_status(self, task_id: str) -> dict:
        """Get status of a filtering task."""
        response = self.session.get(f"{self.base_url}/status/{task_id}")
        response.raise_for_status()
        return response.json()
    
    def list_tasks(self) -> dict:
        """List all active tasks."""
        response = self.session.get(f"{self.base_url}/tasks")
        response.raise_for_status()
        return response.json()
    
    def cancel_task(self, task_id: str) -> dict:
        """Cancel/remove a task."""
        response = self.session.delete(f"{self.base_url}/tasks/{task_id}")
        response.raise_for_status()
        return response.json()
    
    def wait_for_task_completion(self, task_id: str, max_wait_seconds: int = 3600, 
                               poll_interval: int = 5) -> dict:
        """Wait for a task to complete with progress updates."""
        start_time = time.time()
        
        print(f"Waiting for task {task_id} to complete...")
        print("Press Ctrl+C to stop waiting (task will continue running)")
        
        try:
            while True:
                elapsed = time.time() - start_time
                if elapsed > max_wait_seconds:
                    print(f"Timeout reached ({max_wait_seconds}s). Task is still running.")
                    break
                
                status = self.get_task_status(task_id)
                
                if status['status'] == 'completed':
                    print("\n✅ Task completed successfully!")
                    return status
                elif status['status'] == 'failed':
                    print(f"\n❌ Task failed: {status.get('error', 'Unknown error')}")
                    return status
                elif status['status'] == 'running':
                    progress = status.get('progress', {})
                    current = progress.get('current', 0)
                    total = progress.get('total', 0)
                    percentage = progress.get('percentage', 0)
                    current_file = progress.get('current_file', 'Processing...')
                    
                    print(f"\r🔄 Progress: {current}/{total} ({percentage:.1f}%) - {current_file}", end='', flush=True)
                
                time.sleep(poll_interval)
                
        except KeyboardInterrupt:
            print(f"\n⏸️  Stopped waiting. Task {task_id} is still running in background.")
            return self.get_task_status(task_id)
        
        return self.get_task_status(task_id)


def print_json(data: dict, title: str = "Response"):
    """Pretty print JSON data."""
    print(f"\n{title}:")
    print("=" * len(title))
    print(json.dumps(data, indent=2))
    print()


def main():
    """Example usage of the API client."""
    print("YouTube Output Filterer API Client Example")
    print("=" * 50)
    
    # Initialize client
    client = FiltererAPIClient()
    
    try:
        # 1. Health check
        print("1. Checking API health...")
        health = client.health_check()
        print_json(health, "Health Status")
        
        if not health.get('manifest_accessible'):
            print("⚠️  Warning: Default manifest file not accessible")
        if not health.get('audio_classifier_ready'):
            print("⚠️  Warning: Audio classifier not ready")
        
        # 2. Get statistics
        print("2. Getting manifest statistics...")
        stats = client.get_statistics()
        print_json(stats, "Manifest Statistics")
        
        unclassified_count = stats.get('unclassified_records', 0)
        
        if unclassified_count == 0:
            print("ℹ️  No unclassified records found. Nothing to process.")
            return
        
        # 3. Dry run first
        print("3. Performing dry run...")
        dry_run_result = client.start_filtering(dry_run=True)
        print_json(dry_run_result, "Dry Run Result")
        
        # Ask user if they want to proceed
        print(f"Found {unclassified_count} unclassified records.")
        proceed = input("Do you want to start the actual filtering? (y/N): ").lower().strip()
        
        if proceed != 'y':
            print("Filtering cancelled by user.")
            return
        
        # 4. Start actual filtering
        print("4. Starting filtering process...")
        filter_result = client.start_filtering()
        print_json(filter_result, "Filter Start Result")
        
        task_id = filter_result.get('task_id')
        if not task_id:
            print("❌ Failed to start filtering task")
            return
        
        # 5. Wait for completion with progress updates
        print("5. Monitoring task progress...")
        final_status = client.wait_for_task_completion(task_id)
        print_json(final_status, "Final Task Status")
        
        # 6. Show final statistics
        if final_status.get('status') == 'completed':
            print("6. Getting updated statistics...")
            final_stats = client.get_statistics()
            print_json(final_stats, "Updated Statistics")
            
            result = final_status.get('result', {})
            print("\n📊 Processing Summary:")
            print(f"   Total processed: {result.get('total_processed', 0)}")
            print(f"   Files kept (children's voice): {result.get('files_kept', 0)}")
            print(f"   Files deleted (no children's voice): {result.get('files_deleted', 0)}")
            print(f"   Files not found: {result.get('files_not_found', 0)}")
            print(f"   Errors: {result.get('errors', 0)}")
            print(f"   Processing time: {result.get('processing_time', 0):.2f} seconds")
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Make sure the server is running:")
        print("   python api_youtube_filterer.py")
    except requests.exceptions.HTTPError as e:
        print(f"❌ API error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_detail = e.response.json()
                print_json(error_detail, "Error Details")
            except:
                print(f"Response text: {e.response.text}")
    except KeyboardInterrupt:
        print("\n⏸️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")


if __name__ == "__main__":
    main()