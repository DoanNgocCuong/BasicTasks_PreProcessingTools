import requests
from moviepy.editor import AudioFileClip, concatenate_audioclips
import os

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Create temp directory path
TEMP_DIR = os.path.join(SCRIPT_DIR, "temp")

# Create temp directory if it doesn't exist
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def text_to_speech(input_text=None, file_path=None, voice="en-AU-NatashaNeural", speed=1, output_file="2_1.mp3"):
    url = "http://103.253.20.13:25010/api/text-to-speech"
    headers = {"Content-Type": "application/json"}
    
    # Create full path for output file in temp directory
    output_path = os.path.join(TEMP_DIR, output_file)
    
    if input_text:
        text = input_text
    elif file_path:
        with open(file_path, "r") as file:
            text = file.read()
    else:
        raise ValueError("Either input_text or file_path must be provided.")
    
    data = {"text": text, "voice": voice, "speed": speed}
    response = requests.post(url, headers=headers, json=data)
    with open(output_path, "wb") as file:
        file.write(response.content)
    print(f"Audio file saved as {output_path}")
    return output_file  # Return just filename for tracking

# Keep track of files created by text_to_speech
created_files = []

# Introduction
created_files.append(text_to_speech("Giờ, hãy tưởng tượng bạn là khách hàng. Mình sẽ đóng vai nhân viên pha chế, còn bạn trong vai người muốn đặt đồ uống nha.", 
                                  voice="vi-VN-HoaiMyNeural", output_file="intro.mp3"))

# Scenario 1
created_files.append(text_to_speech("Good morning! What can I get for you today?", 
                                  voice="en-AU-NatashaNeural", output_file="barista1.mp3"))
created_files.append(text_to_speech("Tới phiên bạn trả lời, bạn có thể nói:", 
                                  voice="vi-VN-HoaiMyNeural", output_file="prompt1.mp3"))
created_files.append(text_to_speech("Hi, I'd like a large cappuccino, please.", 
                                  voice="en-US-GuyNeural", output_file="customer1.mp3"))

# Scenario 2
created_files.append(text_to_speech("Would you like any flavor in that?", 
                                  voice="en-AU-NatashaNeural", output_file="barista2.mp3"))
created_files.append(text_to_speech("Tới phiên bạn trả lời. Bạn có thể nói:", 
                                  voice="vi-VN-HoaiMyNeural", output_file="prompt2.mp3"))
created_files.append(text_to_speech("Yes, can I add vanilla?", 
                                  voice="en-US-GuyNeural", output_file="customer2.mp3"))

# Scenario 3
created_files.append(text_to_speech("Are you paying with cash or card?", 
                                  voice="en-AU-NatashaNeural", output_file="barista3.mp3"))
created_files.append(text_to_speech("Tới phiên bạn trả lời. Bạn có thể nói:", 
                                  voice="vi-VN-HoaiMyNeural", output_file="prompt3.mp3"))
created_files.append(text_to_speech("Card, please.", 
                                  voice="en-US-GuyNeural", output_file="customer3.mp3"))

def merge_audio_files(input_files, output_file):
    audio_clips = []
    # Create full path for output file in script directory (not in temp)
    output_path = os.path.join(SCRIPT_DIR, output_file)
    
    try:
        # Read each audio file
        for file in input_files:
            # Check if the file is a temp file (one we created) or a resource file
            if file in created_files:
                file_path = os.path.join(TEMP_DIR, file)
            else:
                file_path = os.path.join(SCRIPT_DIR, file)
                
            if os.path.exists(file_path):
                clip = AudioFileClip(file_path)
                audio_clips.append(clip)
            else:
                print(f"Warning: File {file_path} not found")
        
        # Merge clips
        final_clip = concatenate_audioclips(audio_clips)
        
        # Save file
        final_clip.write_audiofile(output_path)
        
        # Close clips to free memory
        for clip in audio_clips:
            clip.close()
        final_clip.close()
        
        print(f"Successfully created {output_file}!")
        print(f"Final file is located at: {output_path}")
        
        # Only delete files that were created by text_to_speech from temp directory
        for file in created_files:
            file_path = os.path.join(TEMP_DIR, file)
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Deleted temp file: {file}")
        
        # Optionally remove temp directory if it's empty
        if not os.listdir(TEMP_DIR):
            os.rmdir(TEMP_DIR)
            print("Removed empty temp directory")
        
    except Exception as e:  
        print(f"Error: {str(e)}")

# List of all input files including existing background tracks
input_files = ["intro.mp3", 
               "barista1.mp3", "prompt1.mp3", "customer1.mp3", "silent_5sec.mp3",
               "barista2.mp3", "prompt2.mp3", "customer2.mp3", "silent_5sec.mp3", 
               "barista3.mp3", "prompt3.mp3", "customer3.mp3"]
output_file = "idea1_4.mp3"

merge_audio_files(input_files, output_file)