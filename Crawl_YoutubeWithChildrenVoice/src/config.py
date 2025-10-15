"""
Unified Configuration for YouTube Children's Voice Crawler

This module provides a centralized configuration system using dataclasses.
It consolidates all configuration from JSON files, environment variables,
and hardcoded defaults into a single, type-safe configuration object.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class YouTubeAPIConfig:
    """Configuration for YouTube Data API."""
    api_keys: List[str] = field(default_factory=list)
    poll_interval_seconds: int = 300
    max_retries: int = 3
    retry_delays: List[int] = field(default_factory=lambda: [1, 2, 4])
    min_request_interval: float = 0.1


@dataclass
class SearchConfig:
    """Configuration for video search and collection."""
    queries: List[str] = field(default_factory=lambda: SearchConfig._load_queries_from_file())
    target_videos_per_query: int = 20
    max_recommended_per_query: int = 100
    min_target_count: int = 1
    enable_channel_exploration: bool = True
    max_similar_videos_per_channel: int = 10

    @staticmethod
    def _load_queries_from_file() -> List[str]:
        """Load search queries from queries.txt file."""
        queries_file = Path("queries.txt")
        if queries_file.exists():
            try:
                with open(queries_file, 'r', encoding='utf-8') as f:
                    queries = [line.strip() for line in f if line.strip()]
                return queries if queries else [
                    "bé giới thiệu bản thân",
                    "bé tập nói tiếng Việt",
                    "trẻ em kể chuyện",
                    "bé hát ca dao",
                    "em bé học nói",
                    "trẻ con nói chuyện",
                    "bé đọc thơ"
                ]
            except Exception as e:
                print(f"Warning: Could not load queries from {queries_file}: {e}")
                return [
                    "bé giới thiệu bản thân",
                    "bé tập nói tiếng Việt",
                    "trẻ em kể chuyện",
                    "bé hát ca dao",
                    "em bé học nói",
                    "trẻ con nói chuyện",
                    "bé đọc thơ"
                ]
        else:
            # Fallback to default queries if file doesn't exist
            return [
                "bé giới thiệu bản thân",
                "bé tập nói tiếng Việt",
                "trẻ em kể chuyện",
                "bé hát ca dao",
                "em bé học nói",
                "trẻ con nói chuyện",
                "bé đọc thơ"
            ]


@dataclass
class DownloadConfig:
    """Configuration for audio downloading."""
    method: str = "api_assisted"  # "api_assisted" or "yt_dlp_only"
    yt_dlp_primary: bool = True
    batch_size: int = 1
    max_concurrent_downloads: int = 4
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
    cookie_settings: Optional[Dict[str, Any]] = None


@dataclass
class AnalysisConfig:
    """Configuration for audio analysis."""
    enable_language_detection: bool = True
    enable_chunking: bool = True
    max_chunk_duration_seconds: int = 1200  # 20 minutes
    chunk_overlap_seconds: int = 5
    max_consecutive_no_children: int = 3
    child_voice_threshold: float = 0.5
    language_confidence_threshold: float = 0.8


@dataclass
class AnalysisAPIConfig:
    """Configuration for the analysis API."""
    enabled: bool = False  # Default to offline/local mode
    server_url: str = "http://localhost:8002"
    timeout_seconds: int = 300
    max_retries: int = 3


@dataclass
class OutputConfig:
    """Configuration for output directories and files."""
    base_dir: Path = field(default_factory=lambda: Path("output"))
    url_outputs_dir: Path = field(default_factory=lambda: Path("output/url_outputs"))
    audio_outputs_dir: Path = field(default_factory=lambda: Path("output/audio_outputs"))
    final_audio_dir: Path = field(default_factory=lambda: Path("output/final_audio"))
    # Backup directories
    url_backups_dir: Path = field(default_factory=lambda: Path("output/url_outputs/backups"))
    audio_backups_dir: Path = field(default_factory=lambda: Path("output/audio_outputs/backups"))
    final_audio_backups_dir: Path = field(default_factory=lambda: Path("output/final_audio/backups"))
    manifest_file: str = "manifest.json"
    backup_prefix: str = "backup"


@dataclass
class LoggingConfig:
    """Configuration for logging and debugging."""
    debug_mode: bool = False
    log_level: str = "INFO"
    enable_progress_bars: bool = True
    save_timing_stats: bool = True


@dataclass
class CrawlerConfig:
    """
    Main configuration class for the YouTube Children's Voice Crawler.

    This consolidates all configuration options into a single, hierarchical structure.
    Configuration can be loaded from environment variables, JSON files, or provided directly.
    """

    # Core components
    youtube_api: YouTubeAPIConfig = field(default_factory=YouTubeAPIConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    analysis_api: AnalysisAPIConfig = field(default_factory=AnalysisAPIConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Derived properties
    @property
    def total_target_videos(self) -> int:
        """Calculate total target videos across all queries."""
        return self.search.target_videos_per_query * len(self.search.queries)

    @property
    def output_dirs_exist(self) -> bool:
        """Check if all output directories exist."""
        dirs_to_check = [
            self.output.base_dir,
            self.output.url_outputs_dir,
            self.output.audio_outputs_dir,
            self.output.final_audio_dir,
            self.output.url_backups_dir,
            self.output.audio_backups_dir,
            self.output.final_audio_backups_dir
        ]
        return all(dir_path.exists() for dir_path in dirs_to_check)

    def create_output_dirs(self) -> None:
        """Create all output directories if they don't exist."""
        dirs_to_create = [
            self.output.base_dir,
            self.output.url_outputs_dir,
            self.output.audio_outputs_dir,
            self.output.final_audio_dir,
            self.output.url_backups_dir,
            self.output.audio_backups_dir,
            self.output.final_audio_backups_dir
        ]
        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> 'CrawlerConfig':
        """Create configuration from environment variables."""
        # Load .env file if it exists
        load_dotenv()
        
        config = cls()

        # YouTube API keys
        api_keys_str = os.getenv('YOUTUBE_API_KEYS')
        if api_keys_str:
            config.youtube_api.api_keys = [key.strip() for key in api_keys_str.split(',') if key.strip()]
        else:
            # Fallback to individual keys
            for i in range(1, 11):  # Support up to 10 keys
                key = os.getenv(f'YOUTUBE_API_KEY_{i}')
                if key:
                    config.youtube_api.api_keys.append(key)

        # Poll interval
        if poll_interval := os.getenv('POLL_INTERVAL_SECONDS'):
            config.youtube_api.poll_interval_seconds = int(poll_interval)

        # Search configuration
        if target_count := os.getenv('TARGET_VIDEOS_PER_QUERY'):
            config.search.target_videos_per_query = int(target_count)

        queries_str = os.getenv('SEARCH_QUERIES')
        if queries_str:
            config.search.queries = [q.strip() for q in queries_str.split(',') if q.strip()]

        # Analysis configuration
        if chunk_duration := os.getenv('MAX_AUDIO_DURATION_SECONDS'):
            config.analysis.max_chunk_duration_seconds = int(chunk_duration)

        if child_threshold := os.getenv('CHILD_THRESHOLD'):
            config.analysis.child_voice_threshold = float(child_threshold)

        # Filterer API
        if filterer_url := os.getenv('ANALYSIS_API_URL'):
            config.analysis_api.server_url = filterer_url

        # Logging
        config.logging.debug_mode = os.getenv('DEBUG_MODE', 'false').lower() == 'true'

        return config

    @classmethod
    def from_json_file(cls, file_path: Path) -> 'CrawlerConfig':
        """Create configuration from JSON file."""
        import json

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        config = cls()

        # Parse nested configuration
        if 'youtube_api' in data:
            yt_data = data['youtube_api']
            config.youtube_api = YouTubeAPIConfig(**yt_data)

        if 'search' in data:
            search_data = data['search']
            config.search = SearchConfig(**search_data)

        if 'download' in data:
            download_data = data['download']
            config.download = DownloadConfig(**download_data)

        if 'analysis' in data:
            analysis_data = data['analysis']
            config.analysis = AnalysisConfig(**analysis_data)

        if 'analysis_api' in data:
            analysis_api_data = data['analysis_api']
            config.analysis_api = AnalysisAPIConfig(**analysis_api_data)

        if 'output' in data:
            output_data = data['output']
            # Convert string paths to Path objects
            for key, value in output_data.items():
                if 'dir' in key and isinstance(value, str):
                    output_data[key] = Path(value)
            config.output = OutputConfig(**output_data)

        if 'logging' in data:
            logging_data = data['logging']
            config.logging = LoggingConfig(**logging_data)

        return config

    def to_json_file(self, file_path: Path) -> None:
        """Save configuration to JSON file."""
        import json

        # Convert Path objects to strings for JSON serialization
        data = self.__dict__.copy()
        data['output'] = self.output.__dict__.copy()
        for key, value in data['output'].items():
            if isinstance(value, Path):
                data['output'][key] = str(value)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []

        # Check API keys
        if not self.youtube_api.api_keys:
            errors.append("No YouTube API keys configured")

        # Check search queries
        if not self.search.queries:
            errors.append("No search queries configured")

        if self.search.target_videos_per_query < self.search.min_target_count:
            errors.append(f"Target videos per query ({self.search.target_videos_per_query}) below minimum ({self.search.min_target_count})")

        # Check analysis settings
        if self.analysis.max_chunk_duration_seconds <= 0:
            errors.append("Max chunk duration must be positive")

        if not (0 <= self.analysis.child_voice_threshold <= 1):
            errors.append("Child voice threshold must be between 0 and 1")

        # Check analysis API
        if self.analysis_api.enabled and not self.analysis_api.server_url:
            errors.append("Analysis API enabled but no server URL configured")

        return errors


# Global configuration instance
_config_instance: Optional[CrawlerConfig] = None


def get_config() -> CrawlerConfig:
    """Get the global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = CrawlerConfig.from_env()
    return _config_instance


def set_config(config: CrawlerConfig) -> None:
    """Set the global configuration instance."""
    global _config_instance
    _config_instance = config


def load_config_from_file(file_path: Path) -> CrawlerConfig:
    """Load configuration from file and set as global instance."""
    config = CrawlerConfig.from_json_file(file_path)
    set_config(config)
    return config


def load_config(
    config_file: Optional[str] = None,
    env_file: Optional[str] = None,
    cli_overrides: Optional[Dict[str, Any]] = None
) -> CrawlerConfig:
    """
    Load configuration with multiple sources.

    Priority order: CLI overrides > config file > environment > defaults

    Args:
        config_file: Path to JSON config file
        env_file: Path to environment file
        cli_overrides: Dictionary of CLI overrides

    Returns:
        CrawlerConfig instance
    """
    cli_overrides = cli_overrides or {}

    # Start with environment/defaults
    config = CrawlerConfig.from_env()

    # Load from config file if specified (overrides env)
    if config_file:
        config_path = Path(config_file)
        if config_path.exists():
            file_config = CrawlerConfig.from_json_file(config_path)
            # Manually merge - copy attributes
            for attr in ['youtube_api', 'search', 'download', 'analysis', 'analysis_api', 'output', 'logging']:
                if hasattr(file_config, attr):
                    setattr(config, attr, getattr(file_config, attr))
        else:
            raise FileNotFoundError(f"Config file not found: {config_file}")

    # Apply CLI overrides
    if cli_overrides.get("queries"):
        config.search.queries = cli_overrides["queries"]

    if cli_overrides.get("max_videos"):
        config.search.target_videos_per_query = cli_overrides["max_videos"]

    if cli_overrides.get("output_dir"):
        # Update output directory paths
        base_dir = Path(cli_overrides["output_dir"])
        config.output.base_dir = base_dir
        config.output.url_outputs_dir = base_dir / "url_outputs"
        config.output.audio_outputs_dir = base_dir / "audio_outputs"
        config.output.final_audio_dir = base_dir / "final_audio"

    if cli_overrides.get("verbose"):
        config.logging.debug_mode = cli_overrides["verbose"]

    if cli_overrides.get("online"):
        # Enable online mode - use API servers for analysis
        config.analysis_api.enabled = True
        # Optionally change server URL if needed for online mode
        # config.analysis_api.server_url = "https://api.example.com"  # Uncomment if needed

    # Validate final configuration
    errors = config.validate()
    if errors:
        raise ValueError(f"Configuration validation failed: {errors}")

    # Set as global instance
    set_config(config)

    return config