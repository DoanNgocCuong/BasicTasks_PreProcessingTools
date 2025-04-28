from pathlib import Path
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# Add folder configuration
SCRIPTS_FOLDER = Path(__file__).parent
VIDEO_DOWNLOAD_FOLDER = SCRIPTS_FOLDER / 'video_downloaded'

# Create download folder if it doesn't exist
VIDEO_DOWNLOAD_FOLDER.mkdir(exist_ok=True)

class TikTokDownloader:
    def __init__(self, author_uniqueid, video_id, tiktok_api_key):
        self.author_uniqueid = author_uniqueid
        self.video_id = video_id
        self.tiktok_api_key = tiktok_api_key
        self.tiktok_api_url = "https://tiktok-api23.p.rapidapi.com/api/download/video"
        self.tiktok_api_host = "tiktok-api23.p.rapidapi.com"

    def get_download_link(self):
        """Get the video download link from TikTok API."""
        tiktok_url = f"https://www.tiktok.com/@{self.author_uniqueid}/video/{self.video_id}"
        headers = {
            "x-rapidapi-key": self.tiktok_api_key,
            "x-rapidapi-host": self.tiktok_api_host
        }
        params = {"url": tiktok_url}
        
        # Thêm debug info
        print(f"URL being called: {self.tiktok_api_url}")
        print(f"Headers: {headers}")
        print(f"Params: {params}")
        
        try:
            response = requests.get(self.tiktok_api_url, headers=headers, params=params)
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")  # Xem nội dung lỗi chi tiết
            response.raise_for_status()
            data = response.json()
            return data.get("play")
        except requests.exceptions.RequestException as e:
            print(f"Error fetching download link: {e}")
            return None

    def download_video(self, filename):
        """Download the video and save it locally."""
        save_path = VIDEO_DOWNLOAD_FOLDER / filename
        
        # Skip if file already exists
        if save_path.exists():
            print(f"File already exists: {save_path}")
            return True
        
        download_link = self.get_download_link()
        if not download_link:
            print("Failed to retrieve download link.")
            return False
        
        try:
            print(f"Downloading video from: {download_link}")
            response = requests.get(download_link, stream=True)
            response.raise_for_status()
            
            # Get file size for progress tracking
            file_size = int(response.headers.get('content-length', 0))
            
            with open(save_path, "wb") as video_file:
                if file_size == 0:
                    video_file.write(response.content)
                else:
                    downloaded = 0
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            video_file.write(chunk)
                            downloaded += len(chunk)
                            # Print progress
                            progress = int(50 * downloaded / file_size)
                            print(f"\rDownloading: [{'=' * progress}{' ' * (50-progress)}] {downloaded}/{file_size} bytes", end='')
                    print()  # New line after progress bar
            
            print(f"Video saved to {save_path}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"Error downloading video: {e}")
            return False

# Example usage
author_uniqueid = "moxierobot"  # Username từ link
video_id = "7255473484782996778"  # ID video từ link
tiktok_api_key = os.getenv("TIKTOK_API_KEY")
print(tiktok_api_key[:5])
downloader = TikTokDownloader(author_uniqueid, video_id, tiktok_api_key)
downloader.download_video("video_test.mp4")  # Save the video as "video.mp4"

