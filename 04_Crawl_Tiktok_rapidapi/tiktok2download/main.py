from pathlib import Path
from dotenv import load_dotenv
import os
import shutil
from datetime import datetime
from def_getListVideosTiktok import fetch_tiktok_videos
from utils_saveListVideosToExcel import save_videos_to_excel
from utils_sheet2DowloadAllVideo import download_all_videos_from_sheet
from utils_AllVideoToTranscription1RoleGrod import process_all_videos

def setup_environment():
    """Setup environment variables and directories"""
    current_dir = Path(__file__).parent
    
    # Setup directories
    excel_output_dir = current_dir / "excel_output"
    video_dir = current_dir / "video_downloaded"
    backup_dir = current_dir / "backups"
    
    # Create directories if not exist
    for dir_path in [excel_output_dir, video_dir, backup_dir]:
        dir_path.mkdir(exist_ok=True)
    
    # Load environment variables
    env_path = current_dir.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    
    api_key = os.getenv("TIKTOK_API_KEY")
    if not api_key:
        raise ValueError("Error: TIKTOK_API_KEY environment variable not set")
    
    return api_key, excel_output_dir, video_dir, backup_dir

def backup_excel_file(excel_path: Path, backup_dir: Path):
    """Create backup of existing Excel file"""
    if excel_path.exists():
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = backup_dir / f"MoxieRobot_Videos_backup_{timestamp}.xlsx"
        shutil.copy2(excel_path, backup_path)
        print(f"\nCreated backup: {backup_path}")

def main():
    """Main process to fetch videos, save to Excel, download videos and transcribe"""
    try:
        # Configuration
        USERNAME = "moxierobot"
        MAX_VIDEOS = 30
        
        # Setup
        api_key, excel_output_dir, video_dir, backup_dir = setup_environment()
        excel_file = "MoxieRobot_Videos.xlsx"
        excel_path = excel_output_dir / excel_file
        
        # Create backup of existing Excel file
        backup_excel_file(excel_path, backup_dir)
        
        print(f"\nStarting process for user: {USERNAME}")
        print(f"Maximum videos to process: {MAX_VIDEOS}")
        
        # Step 1: Fetch videos list
        print("\nFetching videos list...")
        videos = fetch_tiktok_videos(USERNAME, api_key, MAX_VIDEOS)
        if not videos:
            print("No videos found")
            return
        
        # Step 2: Save to Excel
        print("\nSaving to Excel...")
        excel_saved_path = save_videos_to_excel(
            videos, 
            output_dir=str(excel_output_dir),
            filename=excel_file
        )
        
        if not excel_saved_path:
            print("Failed to save Excel file")
            return
            
        # Step 3: Download videos from Excel
        print("\nDownloading videos from Excel...")
        download_all_videos_from_sheet(excel_path)
            
        # Step 4: Process transcriptions
        print("\nProcessing video transcriptions...")
        process_all_videos()
        
        print("\nProcess completed successfully!")
        print(f"Excel file: {excel_path}")
        print(f"Videos directory: {video_dir}")
        print(f"Backups directory: {backup_dir}")
        
    except Exception as e:
        print(f"\nError in main process: {str(e)}")
        raise

if __name__ == "__main__":
    main()