from moviepy.editor import AudioFileClip, CompositeAudioClip, concatenate_audioclips
import os

# Lấy đường dẫn của thư mục hiện tại
current_dir = os.path.dirname(os.path.abspath(__file__))

# Tạo đường dẫn đầy đủ đến các file
main_audio_path = os.path.join(current_dir, "SCRIPTS_idea3_final_5rows.mp3")
background_path = os.path.join(current_dir, "nhacphu.mp3")
output_path = os.path.join(current_dir, "idea3_final.mp3")

# In ra đường dẫn để kiểm tra
print(f"Main audio path: {main_audio_path}")
print(f"Background path: {background_path}")

# Load audio files
main_audio = AudioFileClip(main_audio_path)
background = AudioFileClip(background_path)

# Set common fps
fps = 44100  # standard audio sampling rate

# Nếu background ngắn hơn, tạo vòng lặp thủ công
if background.duration < main_audio.duration:
    n_loops = int(main_audio.duration / background.duration) + 1
    background_loops = [background] * n_loops
    background = concatenate_audioclips(background_loops)

# Cắt background cho khớp với độ dài main audio
background = background.subclip(0, main_audio.duration)

# Giảm volume của background (50%)
background = background.volumex(0.55)

# Kết hợp 2 audio mà không có fps được chỉ định
final_audio = CompositeAudioClip([main_audio, background])

# Xuất file
final_audio.write_audiofile(output_path, fps=fps)

# Dọn dẹp
main_audio.close()
background.close()
final_audio.close()