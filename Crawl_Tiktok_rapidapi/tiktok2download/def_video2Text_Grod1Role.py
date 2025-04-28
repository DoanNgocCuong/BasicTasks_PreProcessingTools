from pathlib import Path
from groq import Groq
from dotenv import load_dotenv
import os

def transcribe_video(video_path):
    """
    Transcribe a single video file using Groq API
    
    Args:
        video_path (Path or str): Path to the video file
    
    Returns:
        str: Transcription text, or None if error occurs
    """
    try:
        # Convert to Path object if string
        video_path = Path(video_path)
        
        # Initialize Groq client
        groq_key = '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'
        client = Groq(api_key=groq_key)

        # Check if file exists
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found at: {video_path}")

        # Transcribe video
        with open(video_path, "rb") as file:
            transcription = client.audio.transcriptions.create(
                file=(str(video_path), file.read()),
                model="whisper-large-v3",
                response_format="verbose_json",
            )
            return transcription.text

    except Exception as e:
        print(f"Error transcribing {video_path}: {e}")
        return None

# For testing the function directly
if __name__ == "__main__":
    current_file = Path(__file__).resolve()
    test_video = current_file.parent / "video_downloaded" / "video_test.mp4"
    result = transcribe_video(test_video)
    print(f"Transcription: {result}")