#!/usr/bin/env python3
"""
YouTube Output Filterer API Test Script

Simple test script to verify the API is working correctly.
"""

import json
import time
import requests
import sys
from pathlib import Path

def test_api_endpoint(base_url: str = "http://localhost:8000"):
    """Test all API endpoints."""
    print("YouTube Output Filterer API Test")
    print("=" * 50)
    print(f"Testing API at: {base_url}")
    print()
    
    success_count = 0
    total_tests = 0
    
    def run_test(test_name: str, test_func):
        nonlocal success_count, total_tests
        total_tests += 1
        
        print(f"🧪 {test_name}... ", end="", flush=True)
        
        try:
            result = test_func()
            if result:
                print("✅ PASS")
                success_count += 1
            else:
                print("❌ FAIL")
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    # Test 1: Health Check
    def test_health():
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"\n   Status: {data.get('status')}")
            print(f"   Version: {data.get('version')}")
            print(f"   Manifest accessible: {data.get('manifest_accessible')}")
            print(f"   Audio classifier ready: {data.get('audio_classifier_ready')}")
            return data.get('status') == 'healthy'
        return False
    
    # Test 2: Statistics
    def test_statistics():
        response = requests.get(f"{base_url}/stats", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"\n   Total records: {data.get('total_records')}")
            print(f"   Unclassified: {data.get('unclassified_records')}")
            print(f"   With children voice: {data.get('files_with_children_voice')}")
            return 'total_records' in data
        return False
    
    # Test 3: Dry Run
    def test_dry_run():
        payload = {"dry_run": True}
        response = requests.post(f"{base_url}/filter", json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"\n   Success: {data.get('success')}")
            if data.get('dry_run_results'):
                unclassified = data['dry_run_results'].get('unclassified_count', 0)
                print(f"   Unclassified count: {unclassified}")
            return data.get('success', False)
        return False
    
    # Test 4: List Tasks (should be empty initially)
    def test_list_tasks():
        response = requests.get(f"{base_url}/tasks", timeout=10)
        if response.status_code == 200:
            data = response.json()
            task_count = len(data.get('tasks', []))
            print(f"\n   Active tasks: {task_count}")
            return 'tasks' in data
        return False
    
    # Test 5: Invalid task status (should return 404)
    def test_invalid_task():
        response = requests.get(f"{base_url}/status/invalid_task_id", timeout=10)
        success = response.status_code == 404
        print(f"\n   Expected 404, got: {response.status_code}")
        return success
    
    # Connection test
    print("🔌 Testing connection... ", end="", flush=True)
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print("✅ CONNECTED")
        print()
    except requests.exceptions.ConnectionError:
        print("❌ FAILED")
        print(f"\n💡 Make sure the API server is running:")
        print(f"   python start_api.py")
        print(f"   # or")
        print(f"   python api_youtube_filterer.py")
        return
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return
    
    # Run all tests
    run_test("Health Check", test_health)
    run_test("Statistics", test_statistics)
    run_test("Dry Run", test_dry_run)
    run_test("List Tasks", test_list_tasks)
    run_test("Invalid Task (404)", test_invalid_task)
    
    # Summary
    print()
    print("=" * 50)
    print(f"TEST SUMMARY: {success_count}/{total_tests} tests passed")
    print("=" * 50)
    
    if success_count == total_tests:
        print("🎉 All tests passed! API is working correctly.")
        
        # Show next steps
        print("\n📋 Next Steps:")
        print(f"   1. Open API docs: {base_url}/docs")
        print(f"   2. Run example client: python api_client_example.py")
        print(f"   3. Start filtering: POST {base_url}/filter")
        
    else:
        print(f"⚠️  {total_tests - success_count} test(s) failed. Check the API server.")
        sys.exit(1)

def main():
    """Main test function."""
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    else:
        base_url = "http://localhost:8000"
    
    test_api_endpoint(base_url)

if __name__ == "__main__":
    main()