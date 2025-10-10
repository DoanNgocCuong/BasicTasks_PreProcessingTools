#!/usr/bin/env python3
"""
Baseline Test Suite for YouTube Crawler Refactoring

This test suite validates that all major components can be imported and initialized
without errors. It serves as a baseline to ensure no existing functionality is broken
during the refactoring process.

Usage:
    python test_baseline.py

Author: Refactoring Assistant
"""

import sys
import traceback
from pathlib import Path
from typing import List, Tuple, Optional


class BaselineTest:
    """Test runner for baseline functionality validation."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.results: List[Tuple[str, bool, Optional[str]]] = []
    
    def run_test(self, test_name: str, test_func) -> bool:
        """Run a single test and track results."""
        print(f"🧪 Testing: {test_name}")
        try:
            result = test_func()
            if result:
                print(f"✅ PASSED: {test_name}")
                self.passed += 1
                self.results.append((test_name, True, None))
                return True
            else:
                print(f"❌ FAILED: {test_name}")
                self.failed += 1
                self.results.append((test_name, False, "Test returned False"))
                return False
        except Exception as e:
            print(f"❌ ERROR: {test_name} - {e}")
            self.failed += 1
            self.results.append((test_name, False, str(e)))
            return False
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("BASELINE TEST SUMMARY")
        print("="*60)
        print(f"Total tests: {self.passed + self.failed}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%" if (self.passed + self.failed) > 0 else "N/A")
        
        if self.failed > 0:
            print("\nFAILED TESTS:")
            for test_name, success, error in self.results:
                if not success:
                    print(f"  ❌ {test_name}: {error}")
        
        print("="*60)


def test_env_config_import():
    """Test that environment configuration can be imported."""
    try:
        from env_config import config
        # Verify basic properties exist
        _ = config.DEBUG_MODE
        _ = config.MAX_WORKERS
        return True
    except Exception:
        return False


def test_youtube_language_classifier_import():
    """Test YouTube language classifier import."""
    try:
        from youtube_language_classifier import YouTubeLanguageClassifier
        classifier = YouTubeLanguageClassifier()
        return True
    except Exception:
        return False


def test_youtube_audio_downloader_import():
    """Test YouTube audio downloader import."""
    try:
        from youtube_audio_downloader import YoutubeAudioDownloader, Config as AudioConfig
        # Test basic initialization
        config = AudioConfig()
        return True
    except Exception:
        return False


def test_youtube_audio_classifier_import():
    """Test YouTube audio classifier import."""
    try:
        from youtube_audio_classifier import AudioClassifier
        return True
    except Exception:
        return False


def test_youtube_video_crawler_import():
    """Test main YouTube video crawler import."""
    try:
        from youtube_video_crawler import YouTubeVideoCrawler
        from models.crawler_models import CrawlerConfig
        return True
    except Exception:
        return False


def test_youtube_output_analyzer_import():
    """Test YouTube output analyzer import."""
    try:
        from youtube_output_analyzer import YouTubeOutputAnalyzer
        from models.analytics_models import QueryStatistics
        return True
    except Exception:
        return False


def test_youtube_output_validator_import():
    """Test YouTube output validator import."""
    try:
        from youtube_output_validator import YouTubeURLValidator
        from models.validation_models import ValidationResult
        return True
    except Exception:
        return False


def test_required_directories_exist():
    """Test that required directories exist or can be created."""
    try:
        base_dir = Path(__file__).parent
        required_dirs = [
            "youtube_url_outputs",
            "youtube_audio_outputs",
            "final_audio_files",
            "crawler_outputs"
        ]
        
        for dir_name in required_dirs:
            dir_path = base_dir / dir_name
            if not dir_path.exists():
                dir_path.mkdir(exist_ok=True)
        
        return True
    except Exception:
        return False


def test_config_files_exist():
    """Test that configuration files exist or can be created."""
    try:
        base_dir = Path(__file__).parent
        
        # Check for .env file
        env_file = base_dir / ".env"
        if not env_file.exists():
            print("⚠️  .env file not found - some tests may fail")
        
        # Check for crawler config
        crawler_config = base_dir / "crawler_config.json"
        if not crawler_config.exists():
            print("⚠️  crawler_config.json not found - will be created on first run")
        
        return True
    except Exception:
        return False


def test_basic_file_operations():
    """Test basic file operations in the workspace."""
    try:
        base_dir = Path(__file__).parent
        test_file = base_dir / "test_temp.txt"
        
        # Write test
        test_file.write_text("test content", encoding='utf-8')
        
        # Read test
        content = test_file.read_text(encoding='utf-8')
        assert content == "test content"
        
        # Cleanup
        test_file.unlink()
        
        return True
    except Exception:
        return False


def main():
    """Run all baseline tests."""
    print("YouTube Crawler Baseline Test Suite")
    print("="*60)
    print("This test suite validates core functionality before refactoring.")
    print()
    
    tester = BaselineTest()
    
    # Run all tests
    tests = [
        ("Environment Configuration", test_env_config_import),
        ("Required Directories", test_required_directories_exist),
        ("Configuration Files", test_config_files_exist),
        ("Basic File Operations", test_basic_file_operations),
        ("YouTube Language Classifier", test_youtube_language_classifier_import),
        ("YouTube Audio Downloader", test_youtube_audio_downloader_import),
        ("YouTube Audio Classifier", test_youtube_audio_classifier_import),
        ("YouTube Video Crawler", test_youtube_video_crawler_import),
        ("YouTube Output Analyzer", test_youtube_output_analyzer_import),
        ("YouTube Output Validator", test_youtube_output_validator_import),
    ]
    
    for test_name, test_func in tests:
        tester.run_test(test_name, test_func)
        print()  # Add spacing between tests
    
    tester.print_summary()
    
    # Return exit code
    return 0 if tester.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())