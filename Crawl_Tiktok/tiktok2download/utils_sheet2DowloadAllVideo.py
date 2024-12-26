import pandas as pd
from def_Tiktok2VideoDownload import TikTokDownloader
import os  
from dotenv import load_dotenv
import time

load_dotenv()
def download_all_videos_from_sheet(sheet_path: str):
    """Download all videos from a sheet
    
    Sử dụng hàm @Cuong_Tiktok2VideoDownload.py để download video
    
    """
    
    # Read the Excel file
    df = pd.read_excel(sheet_path)

    total_videos = len(df)
    success_count = 0
    failed_videos = []

    for index, row in df.iterrows():
        try:
            video_id = row['Video ID']
            video_url = row['URL']
            
            print(f"\nProcessing video {index + 1}/{total_videos}")
            
            # Extract username from the URL
            username = video_url.split('@')[1].split('/')[0]
            
            # Create a downloader instance
            tiktok_api_key = os.getenv("TIKTOK_API_KEY")
            downloader = TikTokDownloader(username, video_id, tiktok_api_key)
            
            # Download with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    filename = f"{username}_{video_id}.mp4"
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
                        time.sleep(2)  # Delay between retries
                        
        except Exception as e:
            print(f"Error processing row {index}: {str(e)}")
            failed_videos.append((video_url, str(e)))
            
        # Add delay between downloads to avoid rate limiting
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

# Sử dụng hàm này
download_all_videos_from_sheet("MoxieRobot_Videos_TEST.xlsx")