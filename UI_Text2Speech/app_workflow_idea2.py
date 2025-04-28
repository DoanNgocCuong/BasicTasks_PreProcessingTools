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


# Scenario 1
text_to_speech("Good morning! What can I get for you today?", voice="en-AU-NatashaNeural", output_file="scenario1_barista.mp3")
text_to_speech("Chào buổi sáng! Tôi có thể giúp gì cho bạn hôm nay?", voice="vi-VN-HoaiMyNeural", output_file="scenario1_barista_vn.mp3")

text_to_speech("Hi, I'd like a large cappuccino, please.", voice="en-US-GuyNeural", output_file="scenario1_option1.mp3")
text_to_speech("Chào, cho tôi một ly cappuccino lớn nhé.", voice="vi-VN-HoaiMyNeural", output_file="scenario1_option1_vn.mp3")

text_to_speech("Sure thing! Would you like any flavor in that?", voice="en-AU-NatashaNeural", output_file="scenario1_barista2.mp3")
text_to_speech("Được thôi! Bạn có muốn thêm hương vị nào không?", voice="vi-VN-HoaiMyNeural", output_file="scenario1_barista2_vn.mp3")

text_to_speech("Yes, can I add vanilla?", voice="en-US-GuyNeural", output_file="scenario1_option2.mp3")
text_to_speech("Có, cho tôi thêm vị vanilla nhé?", voice="vi-VN-HoaiMyNeural", output_file="scenario1_option2_vn.mp3")

text_to_speech("Of course! That'll be $4.50. Are you paying with cash or card?", voice="en-AU-NatashaNeural", output_file="scenario1_barista3.mp3")
text_to_speech("Tất nhiên rồi! Giá là $4.50. Bạn thanh toán bằng tiền mặt hay thẻ?", voice="vi-VN-HoaiMyNeural", output_file="scenario1_barista3_vn.mp3")

text_to_speech("Card, please.", voice="en-US-GuyNeural", output_file="scenario1_option3.mp3")
text_to_speech("Bằng thẻ, cảm ơn.", voice="vi-VN-HoaiMyNeural", output_file="scenario1_option3_vn.mp3")

text_to_speech("Great, please tap your card here. Enjoy your coffee!", voice="en-AU-NatashaNeural", output_file="scenario1_barista4.mp3")
text_to_speech("Tuyệt, vui lòng chạm thẻ của bạn ở đây. Chúc bạn thưởng thức cà phê ngon miệng!", voice="vi-VN-HoaiMyNeural", output_file="scenario1_barista4_vn.mp3")

text_to_speech("Thanks! Have a nice day.", voice="en-US-GuyNeural", output_file="scenario1_option4.mp3")
text_to_speech("Cảm ơn! Chúc bạn một ngày tốt lành.", voice="vi-VN-HoaiMyNeural", output_file="scenario1_option4_vn.mp3")


from moviepy.editor import AudioFileClip, concatenate_audioclips
import os

def merge_audio_files(input_files, output_file):
    audio_clips = []
    
    try:
        for file in input_files:
            base_name = file.rsplit('.', 1)[0] if '.' in file else file
            
            if os.path.exists(base_name + '.mp3'):
                actual_file = base_name + '.mp3'
            elif os.path.exists(base_name + '.wav'):
                actual_file = base_name + '.wav'
            else:
                print(f"Error: Could not find file {base_name} with .mp3 or .wav extension")
                return
                
            clip = AudioFileClip(actual_file)
            audio_clips.append(clip)
        
        final_clip = concatenate_audioclips(audio_clips)
        final_clip.write_audiofile(output_file)
        
        for clip in audio_clips:
            clip.close()
        final_clip.close()
        
        print(f"Successfully created {output_file}!")
        
    except Exception as e:  
        print(f"Error: {str(e)}")

# Use the function
input_files = ["scenario1_barista", "scenario1_barista_vn", "scenario1_option1", "scenario1_option1_vn",
               "scenario1_barista2", "scenario1_barista2_vn", "scenario1_option2", "scenario1_option2_vn", 
               "scenario1_barista3", "scenario1_barista3_vn", "scenario1_option3", "scenario1_option3_vn",
               "scenario1_barista4", "scenario1_barista4_vn", "scenario1_option4", "scenario1_option4_vn"]
output_file = "scenario1_complete.mp3"

merge_audio_files(input_files, output_file)