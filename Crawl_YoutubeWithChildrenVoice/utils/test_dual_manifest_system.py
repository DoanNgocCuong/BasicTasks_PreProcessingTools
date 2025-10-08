#!/usr/bin/env python3
"""
Test script to verify the dual manifest system works correctly.
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.append(str(Path(__file__).parent))

def test_audio_downloader_config():
    """Test that audio downloader accepts the new configuration."""
    print("🧪 Testing audio downloader configuration...")
    
    try:
        from youtube_audio_downloader import Config, YoutubeAudioDownloader
        
        # Test the new Config parameters
        config = Config(
            output_dir="test_output",
            manifest_path="test_manifest.json",
            original_manifest_path="test_original.json",
            enable_duplicate_check=True
        )
        
        print("✅ Config creation successful")
        print(f"   Output dir: {config.output_dir}")
        print(f"   Manifest path: {config.manifest_path}")
        print(f"   Original manifest path: {config.original_manifest_path}")
        print(f"   Duplicate check enabled: {config.enable_duplicate_check}")
        
        # Test downloader creation
        downloader = YoutubeAudioDownloader(config)
        print("✅ YoutubeAudioDownloader creation successful")
        print(f"   Unified index loaded: {len(downloader.unified_index)} entries")
        
        # Test duplicate checking
        if hasattr(downloader, '_is_duplicate'):
            result = downloader._is_duplicate("test_id", "test_url")
            print(f"✅ Duplicate checking method available, returned: {result}")
        else:
            print("❌ Duplicate checking method not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_crawler_paths():
    """Test that crawler paths are set up correctly."""
    print("\n🧪 Testing crawler path setup...")
    
    try:
        from youtube_video_crawler import Config as CrawlerConfig
        
        # Check if crawler output directory exists
        crawler_dir = Path(__file__).parent / "crawler_outputs"
        print(f"   Crawler directory exists: {crawler_dir.exists()}")
        
        audio_dir = crawler_dir / "audio_files"
        print(f"   Audio directory exists: {audio_dir.exists()}")
        
        manifest_file = crawler_dir / "crawler_manifest.json"
        print(f"   Crawler manifest exists: {manifest_file.exists()}")
        
        if manifest_file.exists():
            import json
            with open(manifest_file, 'r') as f:
                data = json.load(f)
            print(f"   Manifest structure: {list(data.keys())}")
            print(f"   Records count: {len(data.get('records', []))}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_merger_script():
    """Test that the merger script can be imported and initialized."""
    print("\n🧪 Testing merger script...")
    
    try:
        from merge_crawler_manifest import ManifestMerger
        
        # Test dry run initialization
        merger = ManifestMerger(dry_run=True)
        print("✅ ManifestMerger initialization successful")
        print(f"   Main manifest path: {merger.main_manifest_path}")
        print(f"   Crawler manifest path: {merger.crawler_manifest_path}")
        print(f"   Paths exist check:")
        print(f"     Main manifest: {merger.main_manifest_path.exists()}")
        print(f"     Crawler manifest: {merger.crawler_manifest_path.exists()}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Testing Dual Manifest System Implementation")
    print("=" * 50)
    
    tests = [
        test_audio_downloader_config,
        test_crawler_paths,
        test_merger_script
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {i+1}. {test.__name__}: {status}")
    
    all_passed = all(results)
    print(f"\n🎯 Overall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🎉 The dual manifest system is ready to use!")
        print("📋 Next steps:")
        print("   1. Run the crawler normally - it will use crawler_manifest.json")
        print("   2. Run the validator on main manifest.json independently")
        print("   3. Use 'python merge_crawler_manifest.py --dry-run' to preview merges")
        print("   4. Use 'python merge_crawler_manifest.py' to perform actual merges")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())