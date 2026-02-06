import pandas as pd
from def_Tiktok2VideoDownload import TikTokDownloader
import os  
from dotenv import load_dotenv
import time
from pathlib import Path

load_dotenv()

def extract_video_id(video_id: str) -> str:
    """Extract numeric ID from string with 'id' prefix"""
    return video_id.replace('id', '') if video_id.startswith('id') else video_id

def download_all_videos_from_sheet(sheet_path: str):
    """Download all videos from a sheet"""
    try:
        # Read the Excel file with Video ID as string
        df = pd.read_excel(sheet_path, dtype={'Video ID': str})
        print(f"\nReading Excel file: {sheet_path}")
        print("Available columns:", df.columns.tolist())

        # Check required columns
        required_columns = ['Video ID', 'Video URL']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        # Create video_downloaded folder if not exists
        video_folder = Path(__file__).parent / "video_downloaded"
        video_folder.mkdir(exist_ok=True)

        total_videos = len(df)
        success_count = 0
        failed_videos = []

        for index, row in df.iterrows():
            try:
                # Extract numeric ID from Video ID column
                raw_video_id = str(row['Video ID'])  # e.g. "id7395372017270263071"
                video_id = extract_video_id(raw_video_id)  # e.g. "7395372017270263071"
                video_url = row['Video URL']
                
                print(f"\nProcessing video {index + 1}/{total_videos}")
                print(f"Raw Video ID: {raw_video_id}")
                print(f"Extracted Video ID: {video_id}")
                print(f"URL: {video_url}")
                
                # Extract username from the URL
                username = video_url.split('@')[1].split('/')[0]
                
                # Check if video already exists
                filename = f"{username}_{video_id}.mp4"  # e.g. "moxierobot_7395372017270263071.mp4"
                video_path = video_folder / filename
                
                if video_path.exists():
                    print(f"Video already exists: {filename}")
                    success_count += 1
                    continue
                
                # Create a downloader instance
                tiktok_api_key = os.getenv("TIKTOK_API_KEY")
                downloader = TikTokDownloader(username, video_id, tiktok_api_key)
                
                # Download with retry
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        if downloader.download_video(filename):
                            success_count += 1
                            print(f"Successfully downloaded: {filename}")
                            break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            print(f"Failed to download after {max_retries} attempts: {filename}")
                            failed_videos.append((video_url, str(e)))
                        else:
                            print(f"Attempt {attempt + 1} failed, retrying...")
                            time.sleep(2)
                            
            except Exception as e:
                print(f"Error processing row {index}: {str(e)}")
                if 'video_url' in locals():
                    failed_videos.append((video_url, str(e)))
                else:
                    failed_videos.append((f"Row {index}", str(e)))
                
            # Add delay between downloads
            time.sleep(1)
        
        # Print summary
        print(f"\nDownload Summary:")
        print(f"Total videos: {total_videos}")
        print(f"Successfully downloaded: {success_count}")
        print(f"Failed: {len(failed_videos)}")
        
        if failed_videos:
            print("\nFailed videos:")
            for url, error in failed_videos:
                print(f"- {url}: {error}")

    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        raise

if __name__ == "__main__":
    download_all_videos_from_sheet("excel_output/MoxieRobot_Videos.xlsx")
