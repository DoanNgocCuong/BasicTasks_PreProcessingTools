from moviepy.editor import AudioFileClip, concatenate_audioclips
import os

def merge_audio_files(input_files, output_file):
    audio_clips = []
    
    try:
        # Get script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        print(f"Looking for files in: {script_dir}")
        
        # List all files in directory to help debug
        print("Files in directory:", os.listdir(script_dir))
        
        # Read each audio file
        for file in input_files:
            # Get base filename (without extension)
            base_name = file.rsplit('.', 1)[0] if '.' in file else file
            
            # Only check in script directory
            full_path = os.path.join(script_dir, base_name)
            if os.path.exists(full_path + '.mp3'):
                actual_file = full_path + '.mp3'
            elif os.path.exists(full_path + '.wav'):
                actual_file = full_path + '.wav'
            else:
                print(f"Error: Could not find file {base_name} with .mp3 or .wav extension")
                print(f"Tried paths:\n{full_path}.mp3\n{full_path}.wav")
                # Clean up any opened clips before returning
                for clip in audio_clips:
                    clip.close()
                return
                
            try:
                clip = AudioFileClip(actual_file)
                audio_clips.append(clip)
                print(f"Loaded: {os.path.basename(actual_file)}")
            except Exception as e:
                print(f"Error loading {os.path.basename(actual_file)}: {str(e)}")
                # Clean up before raising
                for clip in audio_clips:
                    clip.close()
                raise
        
        print(f"Merging {len(audio_clips)} audio clips...")
        
        # Merge clips
        final_clip = concatenate_audioclips(audio_clips)
        
        # Save in same directory
        output_path = os.path.join(script_dir, output_file)
        print(f"Saving to: {output_file}")
        final_clip.write_audiofile(output_path)
        
        # Close clips to free memory
        for clip in audio_clips:
            clip.close()
        final_clip.close()
        
        print(f"Successfully created {output_file}!")
        
    except Exception as e:
        # Clean up any opened clips on error
        for clip in audio_clips:
            clip.close()
        print(f"Error during merge: {str(e)}")

# Use the function
input_files = [
    "idea1_1.mp3",
    "interview_sceneTransition.mp3",
    "idea1_2.mp3",
    "interview_sceneTransition.mp3",
    "idea1_3.mp3", 
    "interview_sceneTransition.mp3",
    "idea1_4.mp3",
    "interview_sceneTransition.mp3",
    "idea1_5.mp3"
]
output_file = "idea1_final.mp3"

merge_audio_files(input_files, output_file)