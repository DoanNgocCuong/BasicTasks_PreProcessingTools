from pathlib import Path

# Define package-level constants
PACKAGE_ROOT = Path(__file__).parent
VIDEO_DOWNLOAD_FOLDER = PACKAGE_ROOT / 'video_downloaded'
OUTPUT_FOLDER = PACKAGE_ROOT / 'output'

# Create necessary folders
VIDEO_DOWNLOAD_FOLDER.mkdir(exist_ok=True)
OUTPUT_FOLDER.mkdir(exist_ok=True)

# Export main functions
from .def_getListVideosTiktok import fetch_tiktok_videos
from .def_Tiktok2VideoDownload import TikTokDownloader
from .utils_sheet2DowloadAllVideo import download_all_videos_from_sheet
from .utils_Video2Text_RoleAssign import VideoTranscriber

__all__ = [
    'fetch_tiktok_videos',
    'TikTokDownloader',
    'download_all_videos_from_sheet',
    'VideoTranscriber',
    'PACKAGE_ROOT',
    'VIDEO_DOWNLOAD_FOLDER',
    'OUTPUT_FOLDER'
]
