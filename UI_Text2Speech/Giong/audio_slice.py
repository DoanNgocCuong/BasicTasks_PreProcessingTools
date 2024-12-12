from moviepy.editor import AudioFileClip

def slice_audio(input_file, output_file, start_time=0, duration=4):
    try:
        # Load audio file
        audio = AudioFileClip(input_file)
        
        # Cut first 5 seconds
        audio_cut = audio.subclip(start_time, start_time + duration)
        
        # Save to new file
        audio_cut.write_audiofile(output_file)
        
        # Close clips
        audio.close()
        audio_cut.close()
        
        print(f"Successfully created {output_file}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

# Cut first 5 seconds of Christmas music
input_file = "we-wish-you-a-merry-christmas-background-xmas-music-for-video-57-sec-256125.mp3"
output_file = "christmas_music_4sec.mp3"

slice_audio(input_file, output_file)