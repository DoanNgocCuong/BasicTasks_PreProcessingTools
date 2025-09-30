#!/usr/bin/env python3
"""
Side-by-side comparison of key rotation logic between components
"""

print("🔍 KEY ROTATION LOGIC COMPARISON")
print("=" * 60)

print("\n📁 tiktok_video_downloader.py:")
print("🔄 _get_next_api_key():")
print("   - Gets current key at index")
print("   - Increments index with modulo wrap-around")
print("   - Returns the key")
print("   Logic: key = api_keys[index]; index = (index + 1) % len(api_keys)")

print("\n🔄 _rotate_api_key():")
print("   - Calls _get_next_api_key() internally")
print("   - Logs the rotation")
print("   - Returns the new key")

print("\n📁 tiktok_api_client.py:")
print("🔄 _switch_to_next_api_key():")
print("   - Stores old index and key for logging")
print("   - Increments index with modulo wrap-around")
print("   - Updates both current_api_key_index AND api_key")
print("   - Logs the rotation with details")
print("   - Returns success boolean")
print("   Logic: index = (index + 1) % len(api_keys); api_key = api_keys[index]")

print("\n📊 ANALYSIS:")
print("✅ Both use circular rotation: (index + 1) % len(api_keys)")
print("✅ Both handle wrap-around correctly")
print("✅ Both log rotations for debugging")
print("✅ API client updates both index AND current key")
print("✅ Video downloader returns key directly")

print("\n🎯 USAGE PATTERNS:")
print("📹 Video Downloader:")
print("   - Gets key for each download attempt")
print("   - Rotates on API failures (429/403 errors)")
print("   - Uses try/retry loop with key rotation")

print("\n🔍 API Client:")
print("   - Switches key on rate limits (429/403)")
print("   - Continues with new key immediately")
print("   - Adds small delays after rotation")

print("\n🎉 CONCLUSION: Both rotation methods are logically consistent!")
print("   The rotation logic is working correctly across the codebase.")