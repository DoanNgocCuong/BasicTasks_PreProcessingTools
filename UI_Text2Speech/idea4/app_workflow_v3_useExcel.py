import pandas as pd
import requests
from moviepy.editor import AudioFileClip, concatenate_audioclips
import os
import re
import unicodedata

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(SCRIPT_DIR, "temp")

# Create temp directory if it doesn't exist
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def text_to_speech(input_text=None, file_path=None, voice="en-AU-NatashaNeural", speed=1, output_file="output.mp3"):
    """Generate speech from text using the TTS API"""
    url = "http://103.253.20.13:25010/api/text-to-speech"
    headers = {"Content-Type": "application/json"}
    output_path = os.path.join(TEMP_DIR, output_file)
    
    # Handle text input from file or direct text
    if input_text:
        text = input_text
    elif file_path:
        with open(file_path, "r") as file:
            text = file.read()
    else:
        raise ValueError("Either input_text or file_path must be provided.")
    
    data = {"text": text, "voice": voice, "speed": speed}
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        with open(output_path, "wb") as file:
            file.write(response.content)
        print(f"Created: {output_file}")
        return output_file
    except Exception as e:
        print(f"Error creating {output_file}: {str(e)}")
        return None



def clean_text(text):
    """
    Clean text while preserving Vietnamese characters
    """
    if pd.isna(text):
        return None
        
    # Convert to string if not already
    text = str(text)
    
    # Replace smart quotes with regular quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    # Remove control characters but keep printable Unicode
    text = ''.join(char for char in text if not unicodedata.category(char).startswith('C'))
    
    # Replace multiple spaces with single space
    text = ' '.join(text.split())
    
    # Remove only specific problematic characters
    text = re.sub(r'[\\/*?:"<>|]', '', text)
    
    # Standardize remaining quotes
    text = text.replace('"', "'")
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text if text else None
# Cũng cần sửa lại hàm merge_audio_files để nhận full path
def merge_audio_files(input_files, output_file="final_output.mp3"):
    """Merge all audio files into one"""
    audio_clips = []
    # Use output_file directly as it now contains full path
    output_path = output_file
    
    try:
        # Read each audio file
        for file in input_files:
            # Check if the file is in temp directory or script directory
            temp_path = os.path.join(TEMP_DIR, file)
            script_path = os.path.join(SCRIPT_DIR, file)
            
            if os.path.exists(temp_path):
                file_path = temp_path
            elif os.path.exists(script_path):
                file_path = script_path
            else:
                print(f"Warning: File {file} not found")
                continue
                
            clip = AudioFileClip(file_path)
            audio_clips.append(clip)
        
        if audio_clips:
            # Merge clips
            final_clip = concatenate_audioclips(audio_clips)
            
            # Create output directory if it doesn't exist
            output_dir = os.path.dirname(output_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Save file
            final_clip.write_audiofile(output_path)
            
            # Close clips
            for clip in audio_clips:
                clip.close()
            final_clip.close()
            
            print(f"Successfully created {output_file}!")
            
            # Modify cleanup section to handle access denied errors
            try:
                # Clean up temp files (only files in temp directory)
                for file in input_files:
                    temp_path = os.path.join(TEMP_DIR, file)
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                            print(f"Deleted temp file: {file}")
                        except PermissionError:
                            print(f"Could not delete temp file: {file} - Permission denied")
                
                # Remove temp directory if empty
                if not os.listdir(TEMP_DIR):
                    try:
                        os.rmdir(TEMP_DIR)
                        print("Removed empty temp directory")
                    except PermissionError:
                        print("Could not remove temp directory - Permission denied")
            except Exception as e:
                print(f"Warning: Cleanup failed: {str(e)}")
                # Continue execution even if cleanup fails
                pass
            
            return True
            
    except Exception as e:
        print(f"Error merging audio files: {str(e)}")
        return False   
 
 
 
 
 
def process_excel_to_audio(excel_file, sheet_name="Sheet1", default_voice="en-AU-NatashaNeural", limit_rows=None):
    """
    Process each row in Excel file to create audio files
    limit_rows: Number of rows to process (None for all rows)
    """
    try:
        # Read Excel file
        df = pd.read_excel(excel_file, sheet_name=sheet_name)
        
        # Limit rows if specified
        if limit_rows:
            df = df.head(limit_rows)
            print(f"Processing first {limit_rows} rows only")
        
        # Xử lý các giá trị NaN trong các cột
        df['text'] = df['text'].fillna('')  # Chuyển NaN thành chuỗi rỗng
        df['voice'] = df['voice'].fillna(default_voice)  # Sử dụng giá trị mặc định cho voice
        df['speed'] = df['speed'].fillna(1.0)  # Sử dụng tốc độ mặc định là 1.0
        
        created_files = []
        empty_row_count = 0
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Get text and handle empty values
                text = clean_text(str(row['text']))
                if not text:
                    print(f"Skipping row {index + 1}: Empty text")
                    empty_row_count += 1
                    if empty_row_count >= 3:
                        print("Đã gặp 3 hàng trống liên tiếp. Dừng xử lý.")
                        break
                    continue
                
                # Reset empty row count if we have text
                empty_row_count = 0

                # Check if text is a direct MP3 reference
                if ".mp3" in text.lower():
                    output_file = text.strip()
                    print(f"Using direct MP3 reference: {output_file}")
                    created_files.append(output_file)
                    continue
                
                # Get parameters with defaults
                voice = str(row['voice']) if pd.notna(row['voice']) else default_voice
                speed = float(row['speed']) if pd.notna(row['speed']) else 1.0
                output_file = f"audio_{index + 1}.mp3"
                
                # Create audio file
                print(f"Processing row {index + 1}: {text[:50]}...")  # Print first 50 chars
                audio_file = text_to_speech(
                    input_text=text,
                    voice=voice,
                    speed=speed,
                    output_file=output_file
                )
                
                if not audio_file:
                    print(f"Error creating audio for row {index + 1}")
                    return []
                    
                created_files.append(audio_file)
                print(f"Successfully created: {output_file}")

            except Exception as e:
                print(f"Error processing row {index + 1}: {str(e)}")
                return []  # Dừng ngay khi có lỗi
        
        return created_files
    
    except Exception as e:
        print(f"Error processing Excel file: {str(e)}")
        return []
# Sửa lại phần main để merger theo output_file
if __name__ == "__main__":
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_file = os.path.join(script_dir, "SCRIPTS_idea3.xlsx")
    
    # Specify number of rows to process
    rows_to_process = 100  # Process first 5 rows
    
    print(f"Input Excel: {excel_file}")
    print(f"Processing first {rows_to_process} rows")
    
    excel_dir = os.path.dirname(os.path.abspath(excel_file))
    excel_name = os.path.splitext(os.path.basename(excel_file))[0]
    final_output = os.path.join(excel_dir, f"{excel_name}_final_5rows.mp3")
    
    print(f"Output will be saved to: {final_output}")
    
    print("\nStarting audio generation...")
    created_files = process_excel_to_audio(excel_file, limit_rows=rows_to_process)
    
    # Only proceed if all files were created successfully
    if created_files and len(created_files) > 0:
        print("\nMerging audio files...")
        success = merge_audio_files(created_files, final_output)
        if success:
            print(f"\nProcess completed successfully!")
            print(f"Output saved at: {final_output}")
        else:
            print("\nError occurred during merging. Process stopped.")
            # Clean up any created files on merge error
            for file in created_files:
                temp_path = os.path.join(TEMP_DIR, file)
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                        print(f"Cleaned up: {file}")
                    except:
                        pass
    else:
        print("\nProcess stopped due to errors in audio file creation.")