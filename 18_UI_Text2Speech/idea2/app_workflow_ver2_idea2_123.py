import requests
from moviepy.editor import AudioFileClip, concatenate_audioclips
import os

# Get the directory of the current script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Create temp directory path
TEMP_DIR = os.path.join(SCRIPT_DIR, "temp")

# Create temp directory if it doesn't exist
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

def text_to_speech(input_text=None, file_path=None, voice="en-AU-NatashaNeural", speed=1, output_file="2_1.mp3"):
    url = "http://103.253.20.13:25010/api/text-to-speech"
    headers = {"Content-Type": "application/json"}
    
    # Create full path for output file in temp directory
    output_path = os.path.join(TEMP_DIR, output_file)
    
    if input_text:
        text = input_text
    elif file_path:
        with open(file_path, "r") as file:
            text = file.read()
    else:
        raise ValueError("Either input_text or file_path must be provided.")
    
    data = {"text": text, "voice": voice, "speed": speed}
    response = requests.post(url, headers=headers, json=data)
    with open(output_path, "wb") as file:
        file.write(response.content)
    print(f"Audio file saved as {output_path}")
    return output_file  # Return just filename for tracking

# Keep track of files created by text_to_speech
created_files = []

# Introduction
created_files.append(text_to_speech("Chào mừng bạn đến với bài học hôm nay! Bạn sẽ thực hành giao tiếp trong một nhà hàng khi gọi món ăn. Hãy lắng nghe từng tình huống, sau đó chọn câu trả lời phù hợp bằng tiếng Anh. Bài học này giúp bạn rèn luyện khả năng phản xạ nhanh và tự tin hơn khi ăn tại nhà hàng. Sẵn sàng chưa? Bắt đầu nào!", 
                                  voice="vi-VN-HoaiMyNeural", output_file="intro.mp3"))

# Scenario 1: Greeting the Waiter
created_files.append(text_to_speech("Scenario 1: Greeting the Waiter", 
                                  voice="en-GB-RyanNeural", output_file="scenario1_intro.mp3"))
created_files.append(text_to_speech("Bạn vừa bước vào nhà hàng và nhân viên phục vụ đến chào bạn. Nghe kỹ câu nói của họ và chọn câu trả lời phù hợp nhé.", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario1_narrator.mp3"))
created_files.append(text_to_speech("Good evening! Welcome to City Bistro. How many people will be dining with you tonight?", 
                                  voice="en-AU-NatashaNeural", output_file="scenario1_waiter.mp3"))
created_files.append(text_to_speech("Chào buổi tối! Chào mừng đến với City Bistro. Tối nay có mấy người dùng bữa ạ?", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario1_waiter_vn.mp3"))
created_files.append(text_to_speech("Hãy chọn các cách trả lời phù hợp trong cách trả lời sau:", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario1_prompt.mp3"))
created_files.append(text_to_speech("Answer 1: Just one, please. Table for one.", 
                                  voice="en-US-GuyNeural", output_file="scenario1_option1.mp3"))
created_files.append(text_to_speech("Chỉ một người thôi, làm ơn. Bàn cho một người.", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario1_option1_vn.mp3"))
created_files.append(text_to_speech("Answer 2: Two people, please.", 
                                  voice="en-AU-NatashaNeural", output_file="scenario1_option2.mp3"))
created_files.append(text_to_speech("Hai người, làm ơn.", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario1_option2_vn.mp3"))
created_files.append(text_to_speech("Answer 3: I’d like a large pizza.", 
                                  voice="en-US-GuyNeural", output_file="scenario1_option3.mp3"))
created_files.append(text_to_speech("Tôi muốn một chiếc pizza lớn.", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario1_option3_vn.mp3"))
created_files.append(text_to_speech("Bạn chọn cách trả lời nào?", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario1_selectQ.mp3"))
created_files.append(text_to_speech("Pause for user to repeat each phrase", 
                                  voice="vi-VN-HoaiMyNeural", output_file="pause.mp3"))
created_files.append(text_to_speech("Nếu bạn chọn câu trả lời số 1 'Just one, please. Table for one.' hoặc số 2 'Two people, please.', thì đây là lựa chọn đúng cho câu hỏi của nhân viên phục vụ. Câu trả lời số 3 không phù hợp vì không liên quan đến số lượng người.", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario1_feedback.mp3"))

# Scenario 2: Ordering a Drink
created_files.append(text_to_speech("Scenario 2: Ordering a Drink", 
                                  voice="en-GB-RyanNeural", output_file="scenario2_intro.mp3"))

created_files.append(text_to_speech("Người phục vụ đưa menu đồ uống cho bạn. Bạn muốn gọi một thức uống. Hãy chọn câu trả lời phù hợp nhé.", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario2_narrator.mp3"))
created_files.append(text_to_speech("What would you like to drink?", 
                                  voice="en-AU-NatashaNeural", output_file="scenario2_waiter.mp3"))
created_files.append(text_to_speech("Bạn muốn uống gì ạ?", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario2_waiter_vn.mp3"))

created_files.append(text_to_speech("Hãy chọn các cách trả lời phù hợp trong cách trả lời sau:", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario2_prompt.mp3"))
created_files.append(text_to_speech("Answer 1: Can I have a water, please?", 
                                  voice="en-US-GuyNeural", output_file="scenario2_option1.mp3"))
created_files.append(text_to_speech("Cho tôi xin một ly nước được không?", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario2_option1_vn.mp3"))
created_files.append(text_to_speech("Answer 2: Do you have any fresh juice?", 
                                  voice="en-AU-NatashaNeural", output_file="scenario2_option2.mp3"))
created_files.append(text_to_speech("Ở đây có nước ép tươi không?", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario2_option2_vn.mp3"))
created_files.append(text_to_speech("Answer 3: How long does it take to make pasta?", 
                                  voice="en-US-GuyNeural", output_file="scenario2_option3.mp3"))
created_files.append(text_to_speech("Làm pasta mất bao lâu?", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario2_option3_vn.mp3"))
created_files.append(text_to_speech("Bạn chọn cách trả lời nào?", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario2_selectQ.mp3"))
created_files.append(text_to_speech("Pause for user to repeat each phrase", 
                                  voice="vi-VN-HoaiMyNeural", output_file="pause.mp3"))
created_files.append(text_to_speech("Đáp án đúng sẽ là câu trả lời số 1: 'Can I have a water, please?' hoặc số 2: 'Do you have any fresh juice?', vì cả hai đều trả lời đúng câu hỏi của nhân viên phục vụ về đồ uống. Câu trả lời số 3 không phù hợp vì không liên quan đến việc gọi đồ uống.", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario2_feedback.mp3"))

# Scenario 3: Ordering Food
created_files.append(text_to_speech("Scenario 3: Ordering Food", 
                                  voice="en-GB-RyanNeural", output_file="scenario3_intro.mp3"))
created_files.append(text_to_speech("Người phục vụ hỏi bạn muốn gọi món gì. Hãy chọn câu trả lời phù hợp để gọi món ăn nhé.", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario3_narrator.mp3"))
created_files.append(text_to_speech("Are you ready to order your food?", 
                                  voice="en-AU-NatashaNeural", output_file="scenario3_waiter.mp3"))
created_files.append(text_to_speech("Bạn đã sẵn sàng gọi món ăn chưa?", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario3_waiter_vn.mp3"))
created_files.append(text_to_speech("Hãy chọn một trong các câu trả lời sau:", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario3_prompt.mp3"))
created_files.append(text_to_speech("Answer 1: Yes, I’ll have the grilled salmon with a side salad.", 
                                  voice="en-US-GuyNeural", output_file="scenario3_option1.mp3"))
created_files.append(text_to_speech("Vâng, tôi muốn gọi cá hồi nướng kèm salad.", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario3_option1_vn.mp3"))
created_files.append(text_to_speech("Answer 2: What are your restaurant hours?", 
                                  voice="en-AU-NatashaNeural", output_file="scenario3_option2.mp3"))
created_files.append(text_to_speech("Nhà hàng mở cửa vào giờ nào?", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario3_option2_vn.mp3"))
created_files.append(text_to_speech("Answer 3: Can you bring the bill, please?", 
                                  voice="en-US-GuyNeural", output_file="scenario3_option3.mp3"))
created_files.append(text_to_speech("Bạn có thể mang hóa đơn cho tôi không?", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario3_option3_vn.mp3"))
created_files.append(text_to_speech("Bạn chọn cách trả lời nào?", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario3_selectQ.mp3"))
created_files.append(text_to_speech("Pause for user to repeat each phrase", 
                                  voice="vi-VN-HoaiMyNeural", output_file="pause.mp3"))
created_files.append(text_to_speech("Câu trả lời đúng là số 1: 'Yes, I’ll have the grilled salmon with a side salad' vì nó liên quan đến việc gọi món ăn. Các lựa chọn khác như 'What are your restaurant hours?' hay 'Can you bring the bill, please?' không trả lời đúng câu hỏi của nhân viên phục vụ.", 
                                  voice="vi-VN-HoaiMyNeural", output_file="scenario3_feedback.mp3"))



def merge_audio_files(input_files, output_file):
    audio_clips = []
    # Create full path for output file in script directory (not in temp)
    output_path = os.path.join(SCRIPT_DIR, output_file)
    
    try:
        # Read each audio file
        for file in input_files:
            # Check if the file is a temp file (one we created) or a resource file
            if file in created_files:
                file_path = os.path.join(TEMP_DIR, file)
            else:
                file_path = os.path.join(SCRIPT_DIR, file)
                
            if os.path.exists(file_path):
                clip = AudioFileClip(file_path)
                audio_clips.append(clip)
            else:
                print(f"Warning: File {file_path} not found")
        
        # Merge clips
        final_clip = concatenate_audioclips(audio_clips)
        
        # Save file
        final_clip.write_audiofile(output_path)
        
        # Close clips to free memory
        for clip in audio_clips:
            clip.close()
        final_clip.close()
        
        print(f"Successfully created {output_file}!")
        print(f"Final file is located at: {output_path}")
        
        # # Only delete files that were created by text_to_speech from temp directory
        # for file in created_files:
        #     file_path = os.path.join(TEMP_DIR, file)
        #     if os.path.exists(file_path):
        #         os.remove(file_path)
        #         print(f"Deleted temp file: {file}")
        
        # Optionally remove temp directory if it's empty
        if not os.listdir(TEMP_DIR):
            os.rmdir(TEMP_DIR)
            print("Removed empty temp directory")
        
    except Exception as e:  
        print(f"Error: {str(e)}")

# List of all input files including existing background tracks
input_files = ["intro.mp3", 
               
               "interview_sceneTransition.mp3",
               "scenario1_narrator.mp3", "scenario1_waiter.mp3", "scenario1_waiter_vn.mp3", 
               "scenario1_prompt.mp3", "scenario1_option1.mp3", "scenario1_option1_vn.mp3", 
               "scenario1_option2.mp3", "scenario1_option2_vn.mp3", "scenario1_option3.mp3", 
               "scenario1_option3_vn.mp3", "scenario1_selectQ.mp3", "silent_3sec.mp3", "scenario1_feedback.mp3",
               
               "interview_sceneTransition.mp3",
               "scenario2_narrator.mp3", "scenario2_waiter.mp3", "scenario2_waiter_vn.mp3", 
               "scenario2_prompt.mp3", "scenario2_option1.mp3", "scenario2_option1_vn.mp3", 
               "scenario2_option2.mp3", "scenario2_option2_vn.mp3", "scenario2_option3.mp3", 
               "scenario2_option3_vn.mp3", "scenario2_selectQ.mp3", "silent_3sec.mp3", "scenario2_feedback.mp3",
               
               "interview_sceneTransition.mp3",
               "scenario3_narrator.mp3", "scenario3_waiter.mp3", "scenario3_waiter_vn.mp3", 
               "scenario3_prompt.mp3", "scenario3_option1.mp3", "scenario3_option1_vn.mp3", 
               "scenario3_option2.mp3", "scenario3_option2_vn.mp3", "scenario3_option3.mp3", 
               "scenario3_option3_vn.mp3", "scenario3_selectQ.mp3", "silent_3sec.mp3", "scenario3_feedback.mp3"]

output_file = "idea2_123.mp3"

merge_audio_files(input_files, output_file)
