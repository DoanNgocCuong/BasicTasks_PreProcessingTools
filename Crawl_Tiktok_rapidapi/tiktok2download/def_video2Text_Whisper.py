# import os
# from moviepy import VideoFileClip
# import whisperx
# import json

# # Step 1: Extract Audio from Video
# def extract_audio_from_video(video_path, audio_path):
#     """
#     Extract audio from a video file.
#     """
#     try:
#         print("Extracting audio from video...")
#         video = VideoFileClip(video_path)
#         video.audio.write_audiofile(audio_path)
#         video.close()
#         print(f"Audio extracted to: {audio_path}")
#     except Exception as e:
#         print(f"Error extracting audio: {str(e)}")
#         raise

# # Step 2: Transcribe with WhisperX (including diarization)
# def transcribe_with_diarization(audio_path, model_size="small"):
#     """
#     Transcribe audio with WhisperX and perform diarization (speaker separation).
#     """
#     try:
#         print("Loading Whisper model...")
#         device = "cuda" if whisperx.utils.get_gpu_memory() > 0 else "cpu"
#         model = whisperx.load_model(model_size, device)

#         print("Transcribing audio...")
#         transcription = model.transcribe(audio_path)

#         # Check if audio has speech before diarization
#         if not transcription["segments"]:
#             return {"segments": []}

#         print("Performing diarization...")
#         diarize_model = whisperx.DiarizationPipeline(use_auth_token=None, device=device)
#         diarization_result = diarize_model(audio_path)

#         print("Aligning transcription with diarization...")
#         result = whisperx.align(transcription["segments"], diarization_result, model.metadata["language"])
        
#         print("Transcription with diarization completed.")
#         return result
#     except Exception as e:
#         print(f"Error in diarization: {str(e)}")
#         raise

# # Step 3: Save Transcription to File
# def save_transcription(result, output_path):
#     """
#     Save the transcription result with speaker information to a JSON file.
#     """
#     formatted_transcript = []
#     for segment in result["segments"]:
#         speaker = segment.get("speaker", "Unknown")
#         formatted_transcript.append({
#             "start": segment["start"],
#             "end": segment["end"],
#             "speaker": speaker,
#             "text": segment["text"]
#         })

#     with open(output_path, "w", encoding="utf-8") as f:
#         json.dump(formatted_transcript, f, ensure_ascii=False, indent=2)
#     print(f"Transcription saved to: {output_path}")

# # Step 4: Format Transcription for Display
# def format_transcription(result):
#     """
#     Format transcription for easy reading.
#     """
#     formatted_text = []
#     for segment in result["segments"]:
#         speaker = segment.get("speaker", "Unknown")
#         start_time = segment["start"]
#         end_time = segment["end"]
#         text = segment["text"]
#         formatted_text.append(f"[{start_time:.2f}s - {end_time:.2f}s] Speaker {speaker}: {text}")
    
#     print("\n".join(formatted_text))

# # Main function to run the pipeline
# def video_to_transcription_pipeline(video_path, audio_path, transcription_output_path):
#     """
#     Full pipeline: Convert video -> audio -> transcription with diarization.
#     """
#     # Step 1: Extract audio from video
#     extract_audio_from_video(video_path, audio_path)

#     # Step 2: Transcribe audio with diarization
#     result = transcribe_with_diarization(audio_path)

#     # Step 3: Save transcription result
#     save_transcription(result, transcription_output_path)

#     # Step 4: Display formatted transcription
#     format_transcription(result)

# # Example usage
# if __name__ == "__main__":
#     try:
#         # Check if input video exists
#         video_file = "video_downloaded/video_test.mp4"
#         if not os.path.exists(video_file):
#             raise FileNotFoundError(f"Video file not found: {video_file}")

#         # Create output directory if it doesn't exist
#         os.makedirs(os.path.dirname(video_file), exist_ok=True)

#         audio_file = "output_audio.wav"
#         transcription_file = "transcription.json"

#         video_to_transcription_pipeline(video_file, audio_file, transcription_file)
#     except Exception as e:
#         print(f"Error in pipeline: {str(e)}")
