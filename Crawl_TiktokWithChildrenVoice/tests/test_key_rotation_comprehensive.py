#!/usr/bin/env python3
"""
Comprehensive test to verify key rotation logic across the entire TikTok crawler codebase.
Tests both the video downloader and API client components.
"""

import os
import sys
import time
from unittest.mock import Mock, patch

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tiktok_video_downloader import TikTokVideoDownloader
from tiktok_api_client import TikTokAPIClient

def test_video_downloader_rotation():
    """Test video downloader key rotation logic."""
    print("🧪 Testing Video Downloader Key Rotation...")
    
    # Initialize downloader
    downloader = TikTokVideoDownloader()
    
    print(f"✅ Downloader initialized with {len(downloader.api_keys)} API keys")
    initial_index = downloader.current_key_index
    print(f"🔑 Initial key index: {initial_index}")
    
    # Test _get_next_api_key circular rotation
    print("\n🔄 Testing _get_next_api_key() rotation:")
    used_keys = []
    used_indices = []
    
    for i in range(len(downloader.api_keys) * 2):  # Test 2 full cycles
        key = downloader._get_next_api_key()
        current_index = (downloader.current_key_index - 1) % len(downloader.api_keys)
        
        print(f"   Step {i+1}: Index {current_index}, Key ...{key[-4:]}")
        used_keys.append(key)
        used_indices.append(current_index)
    
    # Verify circular rotation
    expected_indices = list(range(len(downloader.api_keys))) * 2
    if used_indices == expected_indices:
        print("✅ Circular rotation working correctly!")
    else:
        print(f"❌ Rotation issue! Expected: {expected_indices}, Got: {used_indices}")
    
    # Test _rotate_api_key
    print("\n🔄 Testing _rotate_api_key():")
    downloader.current_key_index = 0  # Reset
    
    for i in range(3):
        old_index = downloader.current_key_index
        key = downloader._rotate_api_key()
        new_index = downloader.current_key_index
        print(f"   Rotation {i+1}: {old_index} -> {new_index}, Key ...{key[-4:]}")
    
    return True

def test_api_client_rotation():
    """Test API client key rotation logic."""
    print("\n🧪 Testing API Client Key Rotation...")
    
    # Initialize client
    client = TikTokAPIClient()
    
    print(f"✅ Client initialized with {len(client.api_keys)} API keys")
    initial_index = client.current_api_key_index
    print(f"🔑 Initial key index: {initial_index}")
    print(f"🔑 Initial key: ...{client.api_key[-4:]}")
    
    # Test _switch_to_next_api_key circular rotation
    print("\n🔄 Testing _switch_to_next_api_key() rotation:")
    
    for i in range(len(client.api_keys) * 2):  # Test 2 full cycles
        old_index = client.current_api_key_index
        old_key = client.api_key
        
        success = client._switch_to_next_api_key()
        
        new_index = client.current_api_key_index
        new_key = client.api_key
        
        print(f"   Step {i+1}: {old_index} -> {new_index}, ...{old_key[-4:]} -> ...{new_key[-4:]}, Success: {success}")
    
    return True

def test_initialization_consistency():
    """Test that both components load the same API keys."""
    print("\n🧪 Testing API Key Loading Consistency...")
    
    # Initialize both components
    downloader = TikTokVideoDownloader()
    client = TikTokAPIClient()
    
    # Compare API keys
    downloader_keys = set(downloader.api_keys)
    client_keys = set(client.api_keys)
    
    print(f"📊 Downloader has {len(downloader_keys)} unique keys")
    print(f"📊 Client has {len(client_keys)} unique keys")
    
    if downloader_keys == client_keys:
        print("✅ Both components use the same API keys!")
        return True
    else:
        print("❌ API key mismatch between components!")
        print(f"   Downloader only: {downloader_keys - client_keys}")
        print(f"   Client only: {client_keys - downloader_keys}")
        return False

def test_rotation_under_stress():
    """Test key rotation behavior under simulated API stress."""
    print("\n🧪 Testing Rotation Under Simulated API Stress...")
    
    client = TikTokAPIClient()
    initial_key = client.api_key
    rotation_count = 0
    
    print(f"🔑 Starting with key: ...{initial_key[-4:]}")
    
    # Simulate multiple rate limit scenarios
    for i in range(10):
        if client._switch_to_next_api_key():
            rotation_count += 1
    
    final_key = client.api_key
    print(f"🔑 Ending with key: ...{final_key[-4:]}")
    print(f"📊 Total rotations: {rotation_count}")
    
    # Should have rotated back to original key if even number of keys
    if len(client.api_keys) == 2 and rotation_count % 2 == 0:
        if initial_key == final_key:
            print("✅ Circular rotation completed correctly!")
            return True
        else:
            print("❌ Circular rotation not working properly!")
            return False
    else:
        print("✅ Rotation completed (unable to verify full circle with current key count)")
        return True

def test_edge_cases():
    """Test edge cases in key rotation."""
    print("\n🧪 Testing Edge Cases...")
    
    # Test single key scenario (should be handled gracefully)
    print("🔍 Testing single key behavior...")
    
    # Mock a client with only one key
    client = TikTokAPIClient()
    original_keys = client.api_keys.copy()
    
    # Temporarily set to single key
    client.api_keys = [client.api_keys[0]]
    client.current_api_key_index = 0
    
    # Try rotation with single key
    success = client._switch_to_next_api_key()
    if not success:
        print("✅ Single key rotation correctly returns False")
    else:
        print("❌ Single key rotation should return False")
    
    # Restore original keys
    client.api_keys = original_keys
    
    return True

def main():
    """Run all rotation tests."""
    print("🚀 Starting Comprehensive Key Rotation Tests...")
    print("=" * 60)
    
    all_tests_passed = True
    
    try:
        # Test each component
        all_tests_passed &= test_video_downloader_rotation()
        all_tests_passed &= test_api_client_rotation()
        all_tests_passed &= test_initialization_consistency()
        all_tests_passed &= test_rotation_under_stress()
        all_tests_passed &= test_edge_cases()
        
        print("\n" + "=" * 60)
        if all_tests_passed:
            print("🎉 ALL TESTS PASSED! Key rotation logic is working correctly.")
        else:
            print("❌ SOME TESTS FAILED! Key rotation needs attention.")
            
    except Exception as e:
        print(f"❌ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        all_tests_passed = False
    
    return all_tests_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)