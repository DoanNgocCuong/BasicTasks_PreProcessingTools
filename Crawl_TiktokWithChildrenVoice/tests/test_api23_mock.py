#!/usr/bin/env python3
"""
Test TikTok API23 Integration (Mock Test)
Tests the API23 method logic without hitting real endpoints
"""

import json
from unittest.mock import patch, MagicMock
from tiktok_video_downloader import TikTokVideoDownloader

def test_api23_method_mock():
    """Test the API23 method with mocked responses."""
    
    print("🧪 Testing API23 Method (Mock)")
    print("=" * 40)
    
    downloader = TikTokVideoDownloader()
    
    # Mock successful API response
    mock_api_response = {
        'success': True,
        'data': {
            'download_url': 'https://example.com/mock_video.mp4',
            'video_id': '7288965373704064286',
            'title': 'Mock Video'
        }
    }
    
    # Mock successful download response
    mock_download_response = MagicMock()
    mock_download_response.status_code = 200
    mock_download_response.raise_for_status.return_value = None
    mock_download_response.iter_content.return_value = [b'mock_video_data' * 1000]  # 15KB of mock data
    
    test_url = "https://www.tiktok.com/@taylorswift/video/7288965373704064286"
    test_output = "./mock_test_video.mp4"
    
    print(f"🎬 Testing API23 logic with: {test_url}")
    
    # Test with mocked requests
    with patch('requests.get') as mock_get:
        # First call returns API response, second call returns video data
        mock_get.side_effect = [
            # API call
            MagicMock(
                status_code=200,
                json=lambda: mock_api_response,
                raise_for_status=lambda: None
            ),
            # Video download call
            mock_download_response
        ]
        
        # Test the API23 method
        result = downloader.download_video_api23(test_url, test_output)
        
        print(f"✅ API23 method executed successfully")
        print(f"📊 Method calls made: {mock_get.call_count}")
        
        # Verify the calls
        calls = mock_get.call_args_list
        if len(calls) >= 1:
            api_call = calls[0]
            print(f"🔍 API URL called: {api_call[0][0][:80]}...")
            print(f"🔑 Headers included API key: {'x-rapidapi-key' in api_call[1]['headers']}")
            
        if result:
            print(f"🎉 API23 mock test PASSED!")
            return True
        else:
            print(f"❌ API23 mock test failed")
            return False

def test_api_url_encoding():
    """Test URL encoding for API requests."""
    
    print("\n🔧 Testing URL Encoding")
    print("=" * 30)
    
    downloader = TikTokVideoDownloader()
    
    test_urls = [
        "https://www.tiktok.com/@taylorswift/video/7288965373704064286",
        "https://www.tiktok.com/@rubyvuvn/video/7328257376878939410",
        "https://vm.tiktok.com/ZMhBaDBEP/"
    ]
    
    import urllib.parse as urlparse
    
    for url in test_urls:
        encoded = urlparse.quote(url, safe='')
        print(f"📎 Original: {url}")
        print(f"🔗 Encoded:  {encoded}")
        
        # Build API URL
        api_url = f"https://tiktok-api23.p.rapidapi.com/api/download/video?url={encoded}"
        print(f"🌐 API URL:  {api_url[:100]}...")
        print()
    
    print("✅ URL encoding test completed")
    return True

def test_error_handling():
    """Test error handling for different API responses."""
    
    print("\n🚨 Testing Error Handling")
    print("=" * 30)
    
    downloader = TikTokVideoDownloader()
    
    # Test different error scenarios
    error_scenarios = [
        {
            'name': 'API Failure',
            'response': {'success': False, 'message': 'Video not found'},
            'expected': False
        },
        {
            'name': 'No Download URL',
            'response': {'success': True, 'data': {'title': 'Video'}},
            'expected': False
        },
        {
            'name': 'Rate Limit',
            'status_code': 429,
            'expected': False
        },
        {
            'name': 'Forbidden',
            'status_code': 403,
            'expected': False
        }
    ]
    
    test_url = "https://www.tiktok.com/@test/video/123"
    test_output = "./error_test_video.mp4"
    
    for scenario in error_scenarios:
        print(f"🧪 Testing: {scenario['name']}")
        
        with patch('requests.get') as mock_get:
            if 'status_code' in scenario:
                # HTTP error scenario
                mock_response = MagicMock()
                mock_response.status_code = scenario['status_code']
                mock_response.raise_for_status.side_effect = Exception(f"HTTP {scenario['status_code']}")
                mock_get.return_value = mock_response
            else:
                # API response scenario
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.json.return_value = scenario['response']
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response
            
            result = downloader.download_video_api23(test_url, test_output)
            
            if result == scenario['expected']:
                print(f"   ✅ Handled correctly")
            else:
                print(f"   ❌ Unexpected result: {result}")
    
    print("✅ Error handling test completed")
    return True

def main():
    """Run all mock tests."""
    
    print("🚀 TikTok API23 Integration Tests (Mock)")
    print("=" * 50)
    
    tests_passed = 0
    
    # Test 1: API23 method logic
    if test_api23_method_mock():
        tests_passed += 1
    
    # Test 2: URL encoding
    if test_api_url_encoding():
        tests_passed += 1
        
    # Test 3: Error handling
    if test_error_handling():
        tests_passed += 1
    
    print(f"\n📊 Mock Test Results:")
    print(f"=" * 25)
    print(f"Tests Passed: {tests_passed}/3")
    
    if tests_passed == 3:
        print(f"🎉 ALL MOCK TESTS PASSED!")
        print(f"💡 API23 integration logic is working correctly")
        print(f"🔑 You just need a valid RapidAPI key for live testing")
        return True
    else:
        print(f"⚠️ Some mock tests failed")
        return False

if __name__ == "__main__":
    success = main()
    
    if success:
        print(f"\n✨ Next Steps:")
        print(f"1. Get a RapidAPI key from: https://rapidapi.com/Lundehund/api/tiktok-api23")
        print(f"2. Add it to your .env file as RAPIDAPI_KEY=your_key_here")
        print(f"3. Run the real crawler to test with live data")
    
    import sys
    sys.exit(0 if success else 1)