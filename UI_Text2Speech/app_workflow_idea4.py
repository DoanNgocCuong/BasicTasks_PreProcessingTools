import requests

def text_to_speech(input_text=None, file_path=None, voice="en-AU-NatashaNeural", speed=1, output_file="2_1.mp3"):
    url = "http://103.253.20.13:25010/api/text-to-speech"
    headers = {"Content-Type": "application/json"}
    
    if input_text:
        text = input_text
    elif file_path:
        with open(file_path, "r") as file:
            text = file.read()
    else:
        raise ValueError("Either input_text or file_path must be provided.")
    
    data = {"text": text, "voice": voice, "speed": speed}
    response = requests.post(url, headers=headers, json=data)
    with open(output_file, "wb") as file:
        file.write(response.content)
    print(f"Audio file saved as {output_file}")

# Introduction
text_to_speech("Chào mừng bạn đến với bài luyện tập shadowing hôm nay! Bạn sẽ học cách nói chuyện khi đặt phòng khách sạn, với từng câu được chia thành các phần nhỏ để bạn dễ dàng luyện tập. Khi luyện shadowing, bạn sẽ nghe và lặp lại từng phần, dần dần ghép lại thành câu hoàn chỉnh. Hãy sẵn sàng, và bắt đầu nào!", voice="vi-VN-HoaiMyNeural", output_file="intro.mp3")

# Part 1: Individual Chunks
text_to_speech("Chúng ta sẽ bắt đầu bằng cách luyện từng cụm từ ngắn. Hãy lắng nghe rồi lặp lại theo mình.", voice="vi-VN-HoaiMyNeural", output_file="part1_intro.mp3")

# Chunk 1
text_to_speech("I'd like to book a room.", voice="en-AU-NatashaNeural", output_file="chunk1.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause1.mp3")
text_to_speech("Tốt lắm! Một lần nữa nhé.", voice="vi-VN-HoaiMyNeural", output_file="repeat1.mp3")
text_to_speech("I'd like to book a room.", voice="en-AU-NatashaNeural", output_file="chunk1_repeat.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause2.mp3")

# Chunk 2
text_to_speech("For three nights.", voice="en-AU-NatashaNeural", output_file="chunk2.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause3.mp3")
text_to_speech("Thử thêm lần nữa nào.", voice="vi-VN-HoaiMyNeural", output_file="repeat2.mp3")
text_to_speech("For three nights.", voice="en-AU-NatashaNeural", output_file="chunk2_repeat.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause4.mp3")

# Chunk 3
text_to_speech("Starting this Friday.", voice="en-AU-NatashaNeural", output_file="chunk3.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause5.mp3")
text_to_speech("Rất tốt! Hãy lặp lại lần nữa.", voice="vi-VN-HoaiMyNeural", output_file="repeat3.mp3")
text_to_speech("Starting this Friday.", voice="en-AU-NatashaNeural", output_file="chunk3_repeat.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause6.mp3")

# Part 2: Building Phrases
text_to_speech("Bây giờ, hãy ghép các cụm từ lại thành các câu dài hơn. Lắng nghe và lặp lại sau mình.", voice="vi-VN-HoaiMyNeural", output_file="part2_intro.mp3")

# Phrase 1
text_to_speech("I'd like to book a room for three nights.", voice="en-AU-NatashaNeural", output_file="phrase1.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause7.mp3")
text_to_speech("Rất tốt, hãy lặp lại một lần nữa nào.", voice="vi-VN-HoaiMyNeural", output_file="repeat4.mp3")
text_to_speech("I'd like to book a room for three nights.", voice="en-AU-NatashaNeural", output_file="phrase1_repeat.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause8.mp3")

# Phrase 2
text_to_speech("Starting this Friday, for three nights.", voice="en-AU-NatashaNeural", output_file="phrase2.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause9.mp3")
text_to_speech("Thử lại lần nữa nhé!", voice="vi-VN-HoaiMyNeural", output_file="repeat5.mp3")
text_to_speech("Starting this Friday, for three nights.", voice="en-AU-NatashaNeural", output_file="phrase2_repeat.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause10.mp3")

# Part 3: Complete Sentences
text_to_speech("Cuối cùng, chúng ta sẽ ghép tất cả thành một câu hoàn chỉnh. Hãy nghe và lặp lại cả câu này nhé.", voice="vi-VN-HoaiMyNeural", output_file="part3_intro.mp3")

# Complete sentence (slow)
text_to_speech("I'd like to book a room for three nights, starting this Friday.", speed=0.8, voice="en-AU-NatashaNeural", output_file="complete_slow.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause11.mp3")
text_to_speech("Rất tốt! Hãy lặp lại lần nữa với tốc độ tự nhiên.", voice="vi-VN-HoaiMyNeural", output_file="repeat6.mp3")

# Complete sentence (natural pace)
text_to_speech("I'd like to book a room for three nights, starting this Friday.", voice="en-AU-NatashaNeural", output_file="complete_natural.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause12.mp3")

# Role-play practice
text_to_speech("Bây giờ, hãy tưởng tượng bạn đang thực sự đặt phòng. Tôi sẽ đóng vai nhân viên khách sạn và bạn sẽ lặp lại câu trả lời của mình.", voice="vi-VN-HoaiMyNeural", output_file="roleplay_intro.mp3")
text_to_speech("Hello, this is Ocean View Hotel. How can I help you?", voice="en-AU-NatashaNeural", output_file="receptionist.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause13.mp3")

# Wrap-up
text_to_speech("Rất tuyệt! Bạn đã hoàn thành phần luyện tập shadowing của mình.", voice="vi-VN-HoaiMyNeural", output_file="wrapup_intro.mp3")
text_to_speech("Hôm nay, bạn đã luyện tập cách đặt phòng khách sạn bằng phương pháp shadowing. Hãy nhớ cấu trúc câu mà bạn đã học để sử dụng khi cần nhé.", voice="vi-VN-HoaiMyNeural", output_file="review_intro.mp3")

# Final review
text_to_speech("I'd like to book a room.", voice="en-AU-NatashaNeural", output_file="review1.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause14.mp3")
text_to_speech("For three nights.", voice="en-AU-NatashaNeural", output_file="review2.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause15.mp3")
text_to_speech("Starting this Friday.", voice="en-AU-NatashaNeural", output_file="review3.mp3")
text_to_speech("silent_5sec.mp3", voice="en-AU-NatashaNeural", output_file="pause16.mp3")

text_to_speech("Xuất sắc! Bạn đã hoàn thành bài luyện tập hôm nay. Shadowing sẽ giúp bạn tăng khả năng phản xạ và phát âm tự nhiên hơn. Hãy tiếp tục luyện tập nhé!", voice="vi-VN-HoaiMyNeural", output_file="final_message.mp3")

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
input_files = ["intro", "interview_background_5sec",
               "part1_intro", "chunk1", "silent_5sec", "repeat1", "chunk1_repeat", "silent_5sec",
               "chunk2", "silent_5sec", "repeat2", "chunk2_repeat", "silent_5sec",
               "chunk3", "silent_5sec", "repeat3", "chunk3_repeat", "silent_5sec",
               "interview_background_5sec",
               "part2_intro", "phrase1", "silent_5sec", "repeat4", "phrase1_repeat", "silent_5sec",
               "phrase2", "silent_5sec", "repeat5", "phrase2_repeat", "silent_5sec",
               "interview_background_5sec",
               "part3_intro", "complete_slow", "silent_5sec", "repeat6", "complete_natural", "silent_5sec",
               "interview_background_5sec",
               "roleplay_intro", "receptionist", "silent_5sec",
               "interview_background_5sec",
               "wrapup_intro", "review_intro",
               "review1", "silent_5sec", "review2", "silent_5sec", "review3", "silent_5sec",
               "final_message", "interview_background_5sec"]

output_file = "complete_lesson.mp3"

merge_audio_files(input_files, output_file)