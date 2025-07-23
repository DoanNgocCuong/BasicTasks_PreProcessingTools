from __future__ import unicode_literals
import yt_dlp
import ffmpeg
import sys
import os

ydl_opts = {
    'format': 'bestaudio/best'
}
def download_audio_from_yturl(url, index=0):
    # Determine the parent directory of the script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(base_dir, 'youtube-audio')

    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Update the output template dynamically to include the index
    ydl_opts['outtmpl'] = os.path.join(output_dir, f'output_{index}.m4a')

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    input_file = os.path.join(output_dir, f'output_{index}.m4a')
    output_file = os.path.join(output_dir, f'output_{index}.wav')
    stream = ffmpeg.input(input_file)
    stream = ffmpeg.output(stream, output_file)
    ffmpeg.run(stream)

    # Remove the intermediate .m4a file
    if os.path.exists(input_file):
        os.remove(input_file)

    # Return the output .wav file path if it exists
    if os.path.exists(output_file):
        return output_file
    else:
        return None

if __name__ == "__main__":
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        args = sys.argv[1:]
        if len(args) > 1:
            print("Too many arguments.")
            print("Usage: python youtubetowav.py <optional link>")
            print("If a link is given it will automatically convert it to .wav. Otherwise a prompt will be shown")
            exit()
        if len(args) == 0:
            url = input("Enter Youtube URL: ")
            download_audio_from_yturl(url)
        else:
            download_audio_from_yturl(args[0])

