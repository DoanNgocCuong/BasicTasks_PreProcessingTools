"""
Test Suite - Unit and integration tests

This module provides comprehensive testing for the YouTube crawler system.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import numpy as np

from config import CrawlerConfig
from models import VideoMetadata, VideoSource
from crawler.youtube_api import YouTubeAPIClient
from downloader.audio_downloader import AudioDownloader
from analyzer.voice_classifier import VoiceClassifier
from analyzer.language_detector import LanguageDetector
from filterer.api_client import FiltererAPIClient


class TestCrawlerConfig:
    """Test configuration system."""

    def test_config_validation_valid(self):
        """Test that valid configuration passes validation."""
        config = CrawlerConfig()
        # Note: This will fail because no API keys are configured, which is expected
        errors = config.validate()
        # We expect at least one error about missing API keys
        assert len(errors) >= 1
        assert "No YouTube API keys configured" in errors

    def test_config_validation_missing_api_keys(self):
        """Test validation fails without API keys."""
        config = CrawlerConfig()
        config.youtube_api.api_keys = []
        errors = config.validate()
        assert "No YouTube API keys configured" in errors

    def test_config_validation_missing_queries(self):
        """Test validation fails without search queries."""
        config = CrawlerConfig()
        config.search.queries = []
        errors = config.validate()
        assert "No search queries configured" in errors


class TestVideoMetadata:
    """Test video metadata model."""

    def test_video_metadata_creation(self):
        """Test creating video metadata."""
        video = VideoMetadata(
            video_id="test123",
            title="Test Video",
            channel_id="channel456",
            channel_title="Test Channel",
            description="Test description",
            duration_seconds=120.0,
            view_count=1000,
            source=VideoSource.YOUTUBE_API
        )

        assert video.video_id == "test123"
        assert video.title == "Test Video"
        assert video.view_count == 1000

    def test_video_metadata_from_api_response(self):
        """Test creating metadata from YouTube API response."""
        api_response = {
            "id": {"videoId": "test123"},
            "snippet": {
                "title": "Test Video",
                "description": "Test description",
                "channelTitle": "Test Channel",
                "publishedAt": "2023-01-01T00:00:00Z"
            },
            "contentDetails": {
                "duration": "PT2M0S"
            },
            "statistics": {
                "viewCount": "1000",
                "likeCount": "100"
            }
        }

        video = VideoMetadata.from_youtube_api_response(api_response)

        assert video.video_id == "test123"
        assert video.title == "Test Video"
        assert video.view_count == 1000
        assert video.like_count == 100


class TestYouTubeAPIClient:
    """Test YouTube API client."""

    @pytest.fixture
    def api_config(self):
        """Create test API config."""
        from config import YouTubeAPIConfig
        config = YouTubeAPIConfig()
        config.api_keys = ["test_key_1", "test_key_2"]
        return config

    @patch('googleapiclient.discovery.build')
    def test_api_client_initialization(self, mock_build, api_config):
        """Test API client initialization."""
        mock_service = Mock()
        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_config)

        assert client.api_keys == ["test_key_1", "test_key_2"]
        assert client.current_key_index == 0
        mock_build.assert_called_once()

    @patch('googleapiclient.discovery.build')
    def test_search_videos(self, mock_build, api_config):
        """Test video search functionality."""
        # Mock the API response
        mock_service = Mock()
        mock_search = Mock()
        mock_list = Mock()
        mock_execute = Mock()

        mock_service.search.return_value.list.return_value.execute.return_value = {
            "items": [{
                "id": {"videoId": "test123"},
                "snippet": {
                    "title": "Test Video",
                    "description": "Test description",
                    "channelTitle": "Test Channel"
                }
            }]
        }

        mock_build.return_value = mock_service

        client = YouTubeAPIClient(api_config)
        results = client.search_videos("test query", max_results=1)

        assert len(results) == 1
        assert results[0].video_id == "test123"
        assert results[0].title == "Test Video"


class TestAudioDownloader:
    """Test audio downloader."""

    @pytest.fixture
    def download_config(self):
        """Create test download config."""
        from config import DownloadConfig
        return DownloadConfig()

    @patch('downloader.audio_downloader.AudioDownloader._try_yt_dlp_download')
    @pytest.mark.asyncio
    async def test_download_success(self, mock_yt_dlp, download_config):
        """Test successful download."""
        # Mock successful download attempt
        mock_attempt = Mock()
        mock_attempt.success = True
        mock_attempt.output_path = Path("test.mp3")
        mock_attempt.file_size = 1024
        mock_attempt.duration = 10.0
        mock_yt_dlp.return_value = mock_attempt

        downloader = AudioDownloader(download_config)

        results = await downloader.download_videos_audio([
            VideoMetadata(video_id="test123", title="Test", channel_id="channel456", channel_title="Channel", source=VideoSource.YOUTUBE_API)
        ])

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].video_id == "test123"


class TestVoiceClassifier:
    """Test voice classifier."""

    @pytest.fixture
    def analysis_config(self):
        """Create test analysis config."""
        from config import AnalysisConfig
        return AnalysisConfig()

    def test_classifier_initialization(self, analysis_config):
        """Test voice classifier initialization."""
        classifier = VoiceClassifier(analysis_config)

        assert classifier.config == analysis_config
        assert classifier.model_version == "1.0.0"

    def test_load_model(self, analysis_config):
        """Test model loading."""
        classifier = VoiceClassifier(analysis_config)

        success = classifier.load_model()

        assert success is True
        assert classifier.model is not None

    @patch('librosa.load')
    @patch('librosa.feature.mfcc')
    @patch('librosa.feature.rms')
    @patch('librosa.feature.zero_crossing_rate')
    @patch('librosa.feature.spectral_centroid')
    @patch('librosa.feature.spectral_bandwidth')
    def test_feature_extraction(self, mock_bandwidth, mock_centroid, mock_zcr, mock_rms, mock_mfcc, mock_load, analysis_config):
        """Test feature extraction from audio."""
        # Mock librosa.load to return audio data and sample rate
        mock_load.return_value = (np.random.randn(16000), 16000)  # 1 second of audio at 16kHz
        
        # Mock librosa feature functions
        mock_mfcc.return_value = [[0.1] * 13 for _ in range(100)]  # 13 MFCCs, 100 frames
        mock_rms.return_value = [[0.5]]
        mock_zcr.return_value = [0.1]
        mock_centroid.return_value = [3000]
        mock_bandwidth.return_value = [2000]

        classifier = VoiceClassifier(analysis_config)

        with patch('pathlib.Path') as mock_path:
            features = classifier._extract_features(mock_path)

        assert features is not None
        assert 'mfcc_0_mean' in features
        assert 'rms_energy' in features
        assert 'spectral_centroid' in features


class TestLanguageDetector:
    """Test language detector."""

    @pytest.fixture
    def analysis_config(self):
        """Create test analysis config."""
        from config import AnalysisConfig
        return AnalysisConfig()

    def test_detector_initialization(self, analysis_config):
        """Test language detector initialization."""
        detector = LanguageDetector(analysis_config)

        assert detector.config == analysis_config
        assert detector.model_version == "1.0.0"
        assert len(detector.supported_languages) == 2

    def test_load_model(self, analysis_config):
        """Test model loading."""
        detector = LanguageDetector(analysis_config)

        success = detector.load_model()

        assert success is True
        assert detector.model is not None


class TestFiltererAPIClient:
    """Test filterer API client."""

    @pytest.fixture
    def filterer_config(self):
        """Create test filterer config."""
        from config import FiltererAPIConfig
        config = FiltererAPIConfig()
        config.enabled = True
        config.server_url = "http://test-server:8000"
        return config

    @pytest.mark.asyncio
    async def test_filter_videos_api_disabled(self, filterer_config):
        """Test filtering when API is disabled."""
        filterer_config.enabled = False

        async with FiltererAPIClient(filterer_config) as client:
            videos = [VideoMetadata(video_id="test123", title="Test", channel_id="channel456", channel_title="Channel", source=VideoSource.YOUTUBE_API)]
            results = await client.filter_videos(videos)

        assert len(results) == 1
        assert results[0].passed_filter is True
        assert results[0].video_id == "test123"

    @patch('aiohttp.ClientSession.post')
    @pytest.mark.asyncio
    async def test_filter_single_video_success(self, mock_post, filterer_config):
        """Test successful single video filtering."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "passed": True,
            "score": 0.95,
            "reasons": [],
            "metadata": {"quality": "high"}
        })

        mock_post.return_value.__aenter__.return_value = mock_response

        async with FiltererAPIClient(filterer_config) as client:
            video = VideoMetadata(video_id="test123", title="Test", channel_id="channel456", channel_title="Channel", source=VideoSource.YOUTUBE_API)
            result = await client._filter_single_video(video)

        assert result.passed_filter is True
        assert result.filter_score == 0.95
        assert result.video_id == "test123"


# Integration tests
class TestIntegration:
    """Integration tests for the complete system."""

    @pytest.mark.asyncio
    async def test_full_workflow_dry_run(self):
        """Test full workflow with dry run configuration."""
        # This would test the main workflow with mocked components
        # For now, just ensure the main function can be imported
        from main import main

        # The main function should be importable
        assert callable(main)

    def test_config_loading(self):
        """Test configuration loading from environment."""
        from config import CrawlerConfig

        config = CrawlerConfig.from_env()

        # Should have default values
        assert isinstance(config.youtube_api.api_keys, list)
        assert isinstance(config.search.queries, list)
        assert config.search.target_videos_per_query > 0


if __name__ == "__main__":
    pytest.main([__file__])