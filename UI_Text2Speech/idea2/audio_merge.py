from moviepy.editor import AudioFileClip, concatenate_audioclips
import os

# Lấy đường dẫn của file script hiện tại
script_dir = os.path.dirname(os.path.abspath(__file__))
print("Script directory:", script_dir)

def merge_audio_files(input_files, output_file):
    # Create list of audio clips
    audio_clips = []
    
    try:
        # Read each audio file
        for file in input_files:
            # Get base filename (without extension)
            base_name = file.rsplit('.', 1)[0] if '.' in file else file
            
            # Tạo đường dẫn tuyệt đối sử dụng thư mục của script
            mp3_path = os.path.join(script_dir, base_name + '.mp3')
            wav_path = os.path.join(script_dir, base_name + '.wav')
            
            # Check both versions of the file
            if os.path.exists(mp3_path):
                actual_file = mp3_path
            elif os.path.exists(wav_path):
                actual_file = wav_path
            else:
                print(f"Error: Could not find file {base_name} with .mp3 or .wav extension")
                print(f"Looked in: {mp3_path}")
                # Clean up any opened clips before returning
                for clip in audio_clips:
                    clip.close()
                return
                
            clip = AudioFileClip(actual_file)
            audio_clips.append(clip)
        
        # Merge clips
        final_clip = concatenate_audioclips(audio_clips)
        
        # Save file with absolute path
        output_path = os.path.join(script_dir, output_file)
        final_clip.write_audiofile(output_path)
        
        # Close clips to free memory
        for clip in audio_clips:
            clip.close()
        final_clip.close()
        
        print(f"Successfully created {output_path}!")
        
    except Exception as e:
        # Clean up any opened clips on error
        for clip in audio_clips:
            clip.close()
        print(f"Error: {str(e)}")

# In ra các file trong thư mục để kiểm tra
print("Files in script directory:", os.listdir(script_dir))

# Use the function
input_files = ["idea2_123.mp3", "interview_sceneTransition.mp3", "idea2_4.mp3"]

output_file = "idea2_final.mp3"

merge_audio_files(input_files, output_file)