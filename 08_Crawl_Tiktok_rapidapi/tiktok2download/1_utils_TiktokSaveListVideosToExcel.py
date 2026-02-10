import pandas as pd
from datetime import datetime
import os
from pathlib import Path
from typing import List, Dict

def save_videos_to_excel(videos: List[Dict], output_dir: str = None, filename: str = None) -> str:
    """
    Save list of TikTok videos to Excel file.
    """
    try:
        # Create DataFrame from video list and ensure Video ID is a string
        df = pd.DataFrame(videos)
        
        # # Ensure Video ID is a string
        # df['id'] = df['id'].astype(str)
        # Add 'id' prefix to Video ID to prevent scientific notation
        df['id'] = 'id' + df['id'].astype(str)
        
        # Convert timestamp to datetime
        if 'create_time' in df.columns:
            df['create_time'] = pd.to_datetime(df['create_time'], unit='s')
        
        # Sort by creation time (newest first)
        if 'create_time' in df.columns:
            df = df.sort_values('create_time', ascending=False)
        
        # Rename columns for better readability
        column_mapping = {
            'id': 'Video ID',
            'description': 'Description',
            'create_time': 'Created',
            'duration': 'Duration',
            'play_count': 'Views',
            'like_count': 'Likes',
            'comment_count': 'Comments',
            'share_count': 'Shares',
            'download_url': 'Download URL',
            'play_url': 'Play URL',
            'cover_url': 'Cover URL',
            'url': 'Video URL',
            'hashtags': 'Hashtags'  # Added hashtags column
        }
        df = df.rename(columns=column_mapping)
        
        # Reorder columns
        columns_order = [
            'Video ID',
            'Description',
            'Created',
            'Duration',
            'Views',
            'Likes',
            'Comments',
            'Shares',
            'Hashtags',  # Added Hashtags to the order
            'Video URL',
            'Download URL',
            'Play URL',
            'Cover URL'
        ]
        df = df[columns_order]
        
        # Create filename with timestamp
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'MoxieRobot_Videos.xlsx'  # Changed to fixed name
        
        # Create output directory if it does not exist
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            file_path = Path(output_dir) / filename
        else:
            file_path = Path(filename)
            
        # Save Excel file with dtype to keep Video ID format
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
            # Set format for Video ID column as text
            worksheet = writer.sheets['Sheet1']
            worksheet.column_dimensions['A'].number_format = '@'
        
        print(f"\nSaved {len(videos)} videos to: {file_path}")
        
        return str(file_path)
        
    except Exception as e:
        print(f"Error saving to Excel: {str(e)}")
        return None

# Example usage
if __name__ == "__main__":
    # Import function fetch_tiktok_videos from get_list_videos.py
    from def_getListVideosTiktok import fetch_tiktok_videos
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Get video list
    username = "moxierobot"
    api_key = os.getenv("TIKTOK_API_KEY")
    max_videos = 1
    
    if not api_key:
        print("Error: TIKTOK_API_KEY environment variable not set")
        exit(1)
    
    videos = fetch_tiktok_videos(username, api_key, max_videos=max_videos)
    
    if videos:
        # Save to Excel
        output_dir = "excel_output"
        save_videos_to_excel(videos, output_dir=output_dir)
    else:
        print("No videos to save")