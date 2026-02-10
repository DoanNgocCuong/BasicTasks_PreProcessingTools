from scipy.io import wavfile
import numpy as np
from moviepy.editor import AudioFileClip

def create_silent_audio(duration=5, output_file="silent.mp3", sample_rate=44100):
    """
    Tạo file âm thanh im lặng sử dụng scipy và chuyển đổi sang MP3
    """
    try:
        # Tạo file WAV im lặng
        temp_wav = "temp_silent.wav"
        
        # Tính số mẫu cần thiết
        num_samples = int(duration * sample_rate)
        
        # Tạo mảng zeros cho stereo audio
        audio_data = np.zeros((num_samples, 2), dtype=np.float32)
        
        # Lưu file WAV
        wavfile.write(temp_wav, sample_rate, audio_data)
        
        # Chuyển đổi WAV sang MP3
        audio = AudioFileClip(temp_wav)
        audio.write_audiofile(
            output_file,
            fps=sample_rate,
            nbytes=2,
            codec='libmp3lame',
            bitrate='128k'
        )
        audio.close()
        
        # Kiểm tra độ dài
        check_clip = AudioFileClip(output_file)
        actual_duration = check_clip.duration
        check_clip.close()
        
        # Xóa file WAV tạm thời
        import os
        os.remove(temp_wav)
        
        print(f"Đã tạo file âm thanh im lặng: {output_file}")
        print(f"Độ dài yêu cầu: {duration} giây")
        print(f"Độ dài thực tế: {actual_duration:.2f} giây")
        
    except Exception as e:
        print(f"Lỗi: {str(e)}")

if __name__ == "__main__":
    create_silent_audio(3, "silent_3sec.mp3")