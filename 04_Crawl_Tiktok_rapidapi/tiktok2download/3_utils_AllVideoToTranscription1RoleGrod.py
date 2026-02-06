from pathlib import Path
import pandas as pd
from def_video2Text_Grod1Role import transcribe_video

def extract_video_id(filename):
    """Extract the numeric ID from the video filename"""
    try:
        # Format: moxierobot_7120391571987533098.mp4
        return filename.split('_')[1].split('.')[0]  # Get the number between '_' and '.mp4'
    except:
        return None

def process_all_videos():
    # Get paths
    current_file = Path(__file__)
    video_folder = current_file.parent / "video_downloaded"
    excel_file = current_file.parent / "excel_output" / "MoxieRobot_Videos.xlsx"

    # Read Excel file with Video ID as string
    try:
        df = pd.read_excel(excel_file, dtype={'Video ID': str})
        print(f"Reading existing Excel file: {excel_file}")
        print("\nAvailable columns in Excel:")
        print(df.columns.tolist())
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # Add Transcriptions column if it doesn't exist
    if 'Transcriptions' not in df.columns:
        df['Transcriptions'] = ''

    # Process each video in the folder
    for video_path in video_folder.glob('*.mp4'):
        try:
            # Get video ID from filename
            video_id = extract_video_id(video_path.name)
            if not video_id:
                print(f"Could not extract ID from filename: {video_path.name}")
                continue

            print(f"\nProcessing video: {video_path}")
            print(f"Video ID from filename: {video_id}")
            
            # Check if ID exists in DataFrame (match with 'id' prefix)
            excel_id = f"id{video_id}"  # Add 'id' prefix to match Excel format
            mask = df['Video ID'] == excel_id
            if not any(mask):
                print(f"Warning: No matching Video ID found in Excel: {excel_id}")
                print("\nFirst few Video IDs in Excel:")
                print(df['Video ID'].head().tolist())
                continue

            # Get transcription
            transcription = transcribe_video(video_path)
            
            if transcription:
                # Update transcription for matching Video ID
                df.loc[mask, 'Transcriptions'] = transcription
                print(f"Updated transcription for Video ID: {excel_id}")
                print(f"Description from Excel: {df.loc[mask, 'Description'].iloc[0]}")

        except Exception as e:
            print(f"Error processing {video_path}: {e}")
            continue

    # Save updated DataFrame to Excel
    df.to_excel(excel_file, index=False)
    print(f"\nTranscriptions saved to {excel_file}")
    print(f"Total videos processed: {len(list(video_folder.glob('*.mp4')))}")

if __name__ == "__main__":
    process_all_videos()