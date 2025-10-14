"""
Data Models for YouTube Children's Voice Crawler

This module defines all the core data structures used throughout the crawler system
using Python dataclasses for type safety and immutability.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlparse


class VideoSource(Enum):
    """Source of video metadata."""
    YOUTUBE_API = "youtube_api"
    YOUTUBE_SCRAPING = "youtube_scraping"
    MANUAL = "manual"


class Language(Enum):
    """Supported languages for detection."""
    VIETNAMESE = "vi"
    ENGLISH = "en"
    OTHER = "other"
    UNKNOWN = "unknown"


class AnalysisStatus(Enum):
    """Status of video analysis."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class VideoMetadata:
    """Metadata for a YouTube video."""
    video_id: str
    title: str
    channel_id: str
    channel_title: str
    description: str = ""
    published_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    thumbnail_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    source: VideoSource = VideoSource.YOUTUBE_API

    @property
    def url(self) -> str:
        """Get the full YouTube URL for this video."""
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @property
    def is_valid(self) -> bool:
        """Check if video metadata is valid."""
        return bool(self.video_id and self.title and self.channel_id)

    @classmethod
    def from_youtube_api_response(cls, item: Dict[str, Any]) -> 'VideoMetadata':
        """Create VideoMetadata from YouTube Data API response."""
        snippet = item.get('snippet', {})
        content_details = item.get('contentDetails', {})
        statistics = item.get('statistics', {})

        # Handle different ID formats: search results have {'videoId': 'ID'}, details have 'ID'
        video_id = item['id']
        if isinstance(video_id, dict):
            video_id = video_id.get('videoId', '')

        # Parse duration from ISO 8601 format
        duration_seconds = None
        if duration_iso := content_details.get('duration'):
            duration_seconds = cls._parse_iso_duration(duration_iso)

        # Parse published date
        published_at = None
        if published_str := snippet.get('publishedAt'):
            try:
                published_at = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
            except ValueError:
                pass

        return cls(
            video_id=video_id,
            title=snippet.get('title', ''),
            channel_id=snippet.get('channelId', ''),
            channel_title=snippet.get('channelTitle', ''),
            description=snippet.get('description', ''),
            published_at=published_at,
            duration_seconds=duration_seconds,
            view_count=int(statistics.get('viewCount', 0)),
            like_count=int(statistics.get('likeCount', 0)),
            comment_count=int(statistics.get('commentCount', 0)),
            thumbnail_url=snippet.get('thumbnails', {}).get('high', {}).get('url'),
            tags=snippet.get('tags', []),
            source=VideoSource.YOUTUBE_API
        )

    @staticmethod
    def _parse_iso_duration(duration_iso: str) -> Optional[float]:
        """Parse ISO 8601 duration (PT4M13S) to seconds."""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
        if match:
            hours = int(match.group(1) or 0)
            minutes = int(match.group(2) or 0)
            seconds = int(match.group(3) or 0)
            return float(hours * 3600 + minutes * 60 + seconds)
        return None


@dataclass
class AudioFile:
    """Represents a downloaded audio file."""
    video_id: str
    file_path: Path
    duration_seconds: float
    format: str = "wav"
    sample_rate: int = 16000
    channels: int = 1
    download_timestamp: datetime = field(default_factory=datetime.now)
    file_size_bytes: Optional[int] = None

    @property
    def exists(self) -> bool:
        """Check if the audio file exists on disk."""
        return self.file_path.exists()

    @property
    def file_size_mb(self) -> Optional[float]:
        """Get file size in MB."""
        if self.file_size_bytes:
            return self.file_size_bytes / (1024 * 1024)
        return None

    def cleanup(self) -> bool:
        """Delete the audio file from disk."""
        try:
            if self.exists:
                self.file_path.unlink()
                return True
        except Exception:
            pass
        return False


@dataclass
class DownloadResult:
    """Result of downloading audio for a video."""
    video_id: str
    attempts: List[Any] = field(default_factory=list)  # DownloadAttempt objects
    success: bool = False
    output_path: Optional[Path] = None
    file_size: Optional[int] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """Check if download was successful."""
        return self.success and self.output_path is not None


@dataclass
class LanguageDetectionResult:
    """Result of language detection analysis."""
    is_vietnamese: bool
    detected_language: Language
    confidence: float
    detected_text: Optional[str] = None
    transcript_source: Optional[str] = None
    error: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """Check if language detection was successful."""
        return self.error is None

    @property
    def language_code(self) -> str:
        """Get language code string."""
        return self.detected_language.value


@dataclass
class VoiceDetectionResult:
    """Result of children's voice detection analysis."""
    has_children_voice: Optional[bool]
    confidence: float
    model_used: str = "unknown"
    processing_time_seconds: Optional[float] = None
    chunks_analyzed: int = 1
    positive_chunks: int = 0
    error: Optional[str] = None

    @property
    def is_successful(self) -> bool:
        """Check if voice detection was successful."""
        return self.error is None and self.has_children_voice is not None

    @property
    def detection_rate(self) -> Optional[float]:
        """Get the rate of positive chunks."""
        if self.chunks_analyzed > 0:
            return self.positive_chunks / self.chunks_analyzed
        return None


@dataclass
class AnalysisResult:
    """Complete analysis result for a video."""
    video_id: str
    language_detection: Optional[LanguageDetectionResult] = None
    voice_detection: Optional[VoiceDetectionResult] = None
    status: AnalysisStatus = AnalysisStatus.PENDING
    total_processing_time: float = 0.0
    analysis_timestamp: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None

    @property
    def is_vietnamese(self) -> Optional[bool]:
        """Check if video is in Vietnamese."""
        if self.language_detection:
            return self.language_detection.is_vietnamese
        return None

    @property
    def has_children_voice(self) -> Optional[bool]:
        """Check if video contains children's voice."""
        if self.voice_detection:
            return self.voice_detection.has_children_voice
        return None

    @property
    def is_suitable(self) -> bool:
        """Check if video is suitable for collection (Vietnamese + children's voice)."""
        return (
            self.is_vietnamese is True and
            self.has_children_voice is True and
            self.status == AnalysisStatus.COMPLETED
        )

    @property
    def confidence_score(self) -> float:
        """Get overall confidence score."""
        lang_conf = self.language_detection.confidence if self.language_detection else 0.0
        voice_conf = self.voice_detection.confidence if self.voice_detection else 0.0
        return (lang_conf + voice_conf) / 2.0


@dataclass
class Video:
    """Complete video object with metadata and analysis results."""
    metadata: VideoMetadata
    audio_file: Optional[AudioFile] = None
    analysis_result: Optional[AnalysisResult] = None
    collected_timestamp: datetime = field(default_factory=datetime.now)
    source_query: Optional[str] = None

    @property
    def video_id(self) -> str:
        """Get video ID."""
        return self.metadata.video_id

    @property
    def url(self) -> str:
        """Get video URL."""
        return self.metadata.url

    @property
    def title(self) -> str:
        """Get video title."""
        return self.metadata.title

    @property
    def is_analyzed(self) -> bool:
        """Check if video has been analyzed."""
        return (
            self.analysis_result is not None and
            self.analysis_result.status == AnalysisStatus.COMPLETED
        )

    @property
    def is_suitable(self) -> bool:
        """Check if video is suitable for collection."""
        if not self.is_analyzed or not self.analysis_result:
            return False
        return self.analysis_result.is_suitable

    @property
    def analysis_status(self) -> AnalysisStatus:
        """Get analysis status."""
        if self.analysis_result:
            return self.analysis_result.status
        return AnalysisStatus.PENDING


@dataclass
class QueryStatistics:
    """Statistics for a search query."""
    query: str
    videos_found: int = 0
    new_videos: int = 0
    total_videos_so_far: int = 0
    timestamp: Optional[datetime] = None
    videos_collected: int = 0
    videos_reviewed: int = 0
    videos_evaluated: int = 0
    videos_with_children_voice: int = 0
    videos_vietnamese: int = 0
    videos_not_vietnamese: int = 0
    total_analysis_time: float = 0.0
    efficiency_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "query": self.query,
            "videos_found": self.videos_found,
            "new_videos": self.new_videos,
            "total_videos_so_far": self.total_videos_so_far,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "videos_collected": self.videos_collected,
            "videos_reviewed": self.videos_reviewed,
            "videos_evaluated": self.videos_evaluated,
            "videos_with_children_voice": self.videos_with_children_voice,
            "videos_vietnamese": self.videos_vietnamese,
            "videos_not_vietnamese": self.videos_not_vietnamese,
            "total_analysis_time": self.total_analysis_time,
            "efficiency_rate": self.efficiency_rate,
            "children_voice_rate": self.children_voice_rate,
            "vietnamese_rate": self.vietnamese_rate,
        }

    @property
    def children_voice_rate(self) -> float:
        """Calculate children's voice detection rate."""
        if self.videos_evaluated > 0:
            return (self.videos_with_children_voice / self.videos_evaluated) * 100
        return 0.0

    @property
    def vietnamese_rate(self) -> float:
        """Calculate Vietnamese language detection rate."""
        total_checked = self.videos_vietnamese + self.videos_not_vietnamese
        if total_checked > 0:
            return (self.videos_vietnamese / total_checked) * 100
        return 0.0


@dataclass
class CrawlerSession:
    """Represents a complete crawler session."""
    session_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    config: Optional[Any] = None  # Forward reference to CrawlerConfig
    videos_collected: List[Video] = field(default_factory=list)
    query_statistics: List[QueryStatistics] = field(default_factory=list)
    total_api_requests: int = 0
    total_processing_time: float = 0.0
    status: str = "running"

    @property
    def duration(self) -> Optional[float]:
        """Get session duration in seconds."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def videos_suitable(self) -> int:
        """Count suitable videos collected."""
        return sum(1 for video in self.videos_collected if video.is_suitable)

    @property
    def completion_rate(self) -> float:
        """Calculate completion rate."""
        total_target = self.config.total_target_videos if self.config else 0
        if total_target > 0:
            return (len(self.videos_collected) / total_target) * 100
        return 0.0

    def complete(self) -> None:
        """Mark session as completed."""
        self.end_time = datetime.now()
        self.status = "completed"
        self.total_processing_time = self.duration or 0.0


@dataclass
class ManifestEntry:
    """Entry in the audio manifest file."""
    video_id: str
    title: str
    channel_title: str
    duration_seconds: float
    file_path: str
    url: str
    collected_timestamp: str
    analysis_result: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

    @classmethod
    def from_video(cls, video: Video) -> 'ManifestEntry':
        """Create manifest entry from Video object."""
        return cls(
            video_id=video.video_id,
            title=video.title,
            channel_title=video.metadata.channel_title,
            duration_seconds=video.audio_file.duration_seconds if video.audio_file else 0.0,
            file_path=str(video.audio_file.file_path) if video.audio_file else "",
            url=video.url,
            collected_timestamp=video.collected_timestamp.isoformat(),
            analysis_result=video.analysis_result.__dict__ if video.analysis_result else None,
            metadata=video.metadata.__dict__ if video.metadata else None
        )


@dataclass
class ProcessingBatch:
    """Represents a batch of videos being processed together."""
    batch_id: str
    videos: List[Video] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: str = "pending"
    errors: List[str] = field(default_factory=list)

    @property
    def duration(self) -> Optional[float]:
        """Get batch processing duration."""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    @property
    def success_rate(self) -> float:
        """Calculate success rate of batch processing."""
        if not self.videos:
            return 0.0
        successful = sum(1 for video in self.videos if video.is_analyzed and video.analysis_result and not video.analysis_result.error)
        return (successful / len(self.videos)) * 100

    def complete(self) -> None:
        """Mark batch as completed."""
        self.end_time = datetime.now()
        self.status = "completed"