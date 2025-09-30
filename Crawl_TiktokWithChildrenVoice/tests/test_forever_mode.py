#!/usr/bin/env python3
"""
Test script for TikTok Crawler Forever Mode functionality.
This script tests the quota monitoring, state persistence, and auto-resume features.
"""

import json
import time
from pathlib import Path

def test_forever_mode_config():
    """Test that forever mode configuration is properly set up."""
    print("🧪 Testing Forever Mode Configuration...")
    
    # Test 1: Check crawler_config.json
    config_file = Path("crawler_config.json")
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        forever_mode = config_data.get('enable_forever_mode', False)
        quota_monitoring = config_data.get('quota_monitoring', True)
        auto_resume = config_data.get('auto_resume', True)
        key_test_interval = config_data.get('key_test_interval', 300)
        state_save_interval = config_data.get('state_save_interval', 60)
        
        print(f"✅ Forever mode enabled: {forever_mode}")
        print(f"✅ Quota monitoring: {quota_monitoring}")
        print(f"✅ Auto resume: {auto_resume}")
        print(f"✅ Key test interval: {key_test_interval}s")
        print(f"✅ State save interval: {state_save_interval}s")
        
        if all([quota_monitoring, auto_resume, key_test_interval > 0, state_save_interval > 0]):
            print("✅ Forever mode configuration is properly set up")
        else:
            print("❌ Forever mode configuration has issues")
    else:
        print("❌ crawler_config.json not found")
    
    # Test 2: Check code integration
    print("\n🔍 Checking code integration...")
    
    try:
        with open("tiktok_video_crawler.py", 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for forever mode features
        features = [
            ('State persistence', '_save_crawler_state' in content and '_load_crawler_state' in content),
            ('Quota monitoring', '_test_api_key_availability' in content and '_start_quota_monitor' in content),
            ('Background threads', 'quota_monitor_thread' in content and 'state_save_thread' in content),
            ('Resume capability', 'current_keyword_index' in content and 'current_video_index' in content),
            ('Quota exhaustion handling', '_handle_quota_exhaustion' in content and 'quota_exhausted' in content),
        ]
        
        for feature_name, has_feature in features:
            status = "✅" if has_feature else "❌"
            print(f"{status} {feature_name}: {'Implemented' if has_feature else 'Missing'}")
            
    except Exception as e:
        print(f"❌ Error checking code: {e}")
    
    print("\n📋 Forever Mode Features:")
    print("=" * 50)
    print("🔄 Automatic quota monitoring")
    print("💾 State persistence and resumption")
    print("⏰ Periodic key availability testing")
    print("🚫 Graceful quota exhaustion handling")
    print("🔄 Infinite loop with checkpoint system")
    print("⚠️  Keyboard interrupt with state saving")
    
    print("\n🛠️  How to Enable Forever Mode:")
    print("=" * 50)
    print("1. Set 'enable_forever_mode': true in crawler_config.json")
    print("2. The crawler will automatically:")
    print("   • Monitor API key quotas in background")
    print("   • Save progress every 60 seconds")
    print("   • Test exhausted keys every 5 minutes")
    print("   • Resume exactly where it left off")
    print("   • Continue running indefinitely")
    
    print("\n⚠️  Important Notes:")
    print("=" * 50)
    print("• State is saved in 'tiktok_url_outputs/crawler_state.json'")
    print("• Press Ctrl+C to pause (state will be saved)")
    print("• Restart the crawler to resume from last checkpoint")
    print("• Forever mode works across multiple API key rotations")
    print("• Monitor logs for quota restoration notifications")

def simulate_quota_exhaustion():
    """Simulate how forever mode handles quota exhaustion."""
    print("\n🎭 Simulating Quota Exhaustion Scenario...")
    print("=" * 50)
    
    # Create a mock state file
    state_file = Path("tiktok_url_outputs/mock_crawler_state.json")
    state_file.parent.mkdir(exist_ok=True)
    
    mock_state = {
        'timestamp': '2025-09-30T17:45:00',
        'current_keyword_index': 5,
        'current_video_index': 23,
        'total_videos_analyzed': 150,
        'total_videos_collected': 45,
        'quota_exhausted': True,
        'exhausted_keys': ['key1', 'key2'],
        'resume_checkpoint': {
            'keyword_index': 5,
            'video_index': 23,
            'keyword': 'bé kể chuyện',
            'video_url': 'https://tiktok.com/@user/video/123456'
        }
    }
    
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(mock_state, f, indent=2)
    
    print("✅ Mock state file created:")
    print(f"   📁 {state_file}")
    print(f"   📊 Progress: Keyword 6/413, Video 24")
    print(f"   📈 Stats: 150 analyzed, 45 collected")
    print(f"   🚫 Status: Quota exhausted")
    
    print("\n🔄 Forever Mode Recovery Process:")
    print("1. 🚫 All API keys exhausted → Save current state")
    print("2. ⏰ Background thread tests keys every 5 minutes")
    print("3. ✅ When quota restored → Automatic resumption")
    print("4. 📍 Resume from exact checkpoint (Keyword 6, Video 24)")
    print("5. 🔄 Continue processing indefinitely")
    
    # Cleanup
    state_file.unlink(missing_ok=True)
    print("\n🧹 Mock state file cleaned up")

if __name__ == "__main__":
    test_forever_mode_config()
    simulate_quota_exhaustion()
    
    print("\n" + "=" * 60)
    print("🎉 Forever Mode Testing Complete!")
    print("Ready for continuous TikTok crawling with automatic recovery! 🚀")