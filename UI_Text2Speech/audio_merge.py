from moviepy.editor import AudioFileClip, concatenate_audioclips
import os

def merge_audio_files(input_files, output_file):
    # Create list of audio clips
    audio_clips = []
    
    try:
        # Read each audio file
        for file in input_files:
            # Get base filename (without extension)
            base_name = file.rsplit('.', 1)[0] if '.' in file else file
            
            # Check both versions of the file
            if os.path.exists(base_name + '.mp3'):
                actual_file = base_name + '.mp3'
            elif os.path.exists(base_name + '.wav'):
                actual_file = base_name + '.wav'
            else:
                print(f"Error: Could not find file {base_name} with .mp3 or .wav extension")
                return
                
            clip = AudioFileClip(actual_file)
            audio_clips.append(clip)
        
        # Merge clips
        final_clip = concatenate_audioclips(audio_clips)
        
        # Save file
        final_clip.write_audiofile(output_file)
        
        # Close clips to free memory
        for clip in audio_clips:
            clip.close()
        final_clip.close()
        
        print(f"Successfully created {output_file}!")
        
    except Exception as e:  
        print(f"Error: {str(e)}")

# Use the function
# Use the function
input_files = ["intro", "interview_background_5sec",
               # interview_background_5sec khi vào các phần
               "scenario1_intro", "scenario1_waiter", "scenario1_option1", "scenario1_option2", "scenario1_option3", 
                        "BanChonOptionNao", "silent_5sec", "scenario1_feedback", "interview_background_5sec",
               "scenario2_intro", "scenario2_waiter", "scenario2_option1", "scenario2_option2", "scenario2_option3",
                        "BanChonOptionNao", "silent_5sec", "scenario2_feedback", "interview_background_5sec",
               "scenario3_intro", "scenario3_waiter", "scenario3_option1", "scenario3_option2", "scenario3_option3", 
                        "BanChonOptionNao", "silent_5sec", "scenario3_feedback", "interview_background_5sec",
               "scenario4_intro", "scenario4_waiter", "scenario4_option1", "scenario4_option2", "scenario4_option3",
                        "BanChonOptionNao", "silent_5sec", "scenario4_feedback", "interview_background_5sec",
               "scenario5_intro", "scenario5_waiter", "scenario5_option1", "scenario5_option2", "scenario5_option3",
                        "BanChonOptionNao", "silent_5sec", "scenario5_feedback", "interview_background_5sec",
               "wrapup_intro", "review1", "silent_5sec", "review2", "silent_5sec", "review3", "silent_5sec",
               "review4", "silent_5sec", "review5", "silent_5sec", "final_message", "interview_background_5sec"]
output_file = "complete_lesson.mp3"

merge_audio_files(input_files, output_file)