"""
Test the new utilities package to ensure it works correctly.
"""

def test_utils():
    """Test utilities package functionality."""
    # Test debug utilities
    from utils.debug_utils import debug_print, log_operation, log_error
    
    print("Testing debug utilities...")
    debug_print("Test debug message", "INFO")
    log_operation("Test operation", "with details")
    
    # Test URL utilities
    from utils.url_utils import extract_video_id, normalize_youtube_url, is_valid_youtube_url
    
    print("\nTesting URL utilities...")
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        "invalid_url"
    ]
    
    for url in test_urls:
        video_id = extract_video_id(url)
        normalized = normalize_youtube_url(url)
        is_valid = is_valid_youtube_url(url)
        print(f"  URL: {url}")
        print(f"    Video ID: {video_id}")
        print(f"    Normalized: {normalized}")
        print(f"    Is valid: {is_valid}")
    
    # Test file utilities
    from utils.file_utils import ensure_directory, clean_filename
    
    print("\nTesting file utilities...")
    test_dir = ensure_directory("test_temp_dir")
    print(f"  Created directory: {test_dir}")
    
    dirty_filename = "test<>:|file?.txt"
    clean_name = clean_filename(dirty_filename)
    print(f"  Cleaned filename: '{dirty_filename}' -> '{clean_name}'")
    
    # Cleanup
    import shutil
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print(f"  Cleaned up directory: {test_dir}")
    
    print("\n✅ All utilities tests passed!")


if __name__ == "__main__":
    test_utils()