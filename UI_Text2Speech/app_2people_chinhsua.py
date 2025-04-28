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
text_to_speech("Chào mừng bạn đến với bài học hôm nay! Bạn sẽ thực hành giao tiếp trong một nhà hàng khi gọi món ăn. Hãy lắng nghe từng tình huống, sau đó chọn câu trả lời phù hợp bằng tiếng Anh. Bài học này giúp bạn rèn luyện khả năng phản xạ nhanh và tự tin hơn khi ăn tại nhà hàng. Sẵn sàng chưa? Bắt đầu nào!", voice="vi-VN-HoaiMyNeural", output_file="intro.mp3")

# Scenario 1
text_to_speech("Bạn bước vào nhà hàng và người phục vụ đến chào đón bạn. Nghe kỹ câu nói của họ và chọn phản hồi phù hợp.", voice="vi-VN-HoaiMyNeural", output_file="scenario1_intro.mp3")
text_to_speech("Good evening! Welcome to City Bistro. How many people will be dining with you tonight?", voice="en-AU-NatashaNeural", output_file="scenario1_waiter.mp3")
text_to_speech("Just one, please. Table for one.", voice="en-US-GuyNeural", output_file="scenario1_option1.mp3")
text_to_speech("Two people, please.", voice="en-AU-NatashaNeural", output_file="scenario1_option2.mp3")
text_to_speech("I'd like a large pizza.", voice="en-US-GuyNeural", output_file="scenario1_option3.mp3")
text_to_speech("Nếu bạn chọn câu trả lời 1 hoặc 2, đó là lựa chọn phù hợp cho câu hỏi của nhân viên phục vụ. Câu trả lời số 3 không đúng vì nó trả lời không liên quan đến số lượng người.", voice="vi-VN-HoaiMyNeural", output_file="scenario1_feedback.mp3")

# Scenario 2
text_to_speech("Người phục vụ đưa menu đồ uống cho bạn. Bạn muốn gọi một thức uống. Hãy chọn câu trả lời phù hợp.", voice="vi-VN-HoaiMyNeural", output_file="scenario2_intro.mp3")
text_to_speech("What would you like to drink?", voice="en-AU-NatashaNeural", output_file="scenario2_waiter.mp3")
text_to_speech("Can I have a water, please?", voice="en-US-GuyNeural", output_file="scenario2_option1.mp3")
text_to_speech("Do you have any fresh juice?", voice="en-AU-NatashaNeural", output_file="scenario2_option2.mp3")
text_to_speech("How long does it take to make pasta?", voice="en-US-GuyNeural", output_file="scenario2_option3.mp3")
text_to_speech("Đáp án đúng sẽ là câu trả lời 1 hoặc 2, vì cả hai đều trả lời đúng câu hỏi của nhân viên phục vụ. Đáp án 3 không phù hợp, vì câu hỏi không liên quan đến đồ uống.", voice="vi-VN-HoaiMyNeural", output_file="scenario2_feedback.mp3")

# Scenario 3
text_to_speech("Người phục vụ hỏi bạn muốn gọi món gì. Hãy chọn câu trả lời phù hợp để gọi món ăn.", voice="vi-VN-HoaiMyNeural", output_file="scenario3_intro.mp3")
text_to_speech("Are you ready to order your food?", voice="en-AU-NatashaNeural", output_file="scenario3_waiter.mp3")
text_to_speech("Yes, I'll have the grilled salmon with a side salad.", voice="en-US-GuyNeural", output_file="scenario3_option1.mp3")
text_to_speech("What are your restaurant hours?", voice="en-AU-NatashaNeural", output_file="scenario3_option2.mp3")
text_to_speech("Can you bring the bill, please?", voice="en-US-GuyNeural", output_file="scenario3_option3.mp3")
text_to_speech("Câu trả lời đúng là số 1 vì nó liên quan đến việc gọi món. Các lựa chọn khác không trả lời đúng câu hỏi của nhân viên phục vụ.", voice="vi-VN-HoaiMyNeural", output_file="scenario3_feedback.mp3")

# Scenario 4
text_to_speech("Bạn muốn hỏi thêm thông tin về món ăn. Người phục vụ đến gần và bạn có cơ hội để đặt câu hỏi.", voice="vi-VN-HoaiMyNeural", output_file="scenario4_intro.mp3")
text_to_speech("Our special today is the pasta primavera. Would you like to know more about it?", voice="en-AU-NatashaNeural", output_file="scenario4_waiter.mp3")
text_to_speech("Yes, what ingredients are in the pasta primavera?", voice="en-US-GuyNeural", output_file="scenario4_option1.mp3")
text_to_speech("No, just bring me water.", voice="en-AU-NatashaNeural", output_file="scenario4_option2.mp3")
text_to_speech("Is there an extra charge for takeout?", voice="en-US-GuyNeural", output_file="scenario4_option3.mp3")
text_to_speech("Câu trả lời phù hợp là số 1 vì nó trả lời đúng vào việc muốn biết thêm về món ăn đặc biệt. Các lựa chọn khác không đúng ngữ cảnh.", voice="vi-VN-HoaiMyNeural", output_file="scenario4_feedback.mp3")

# Scenario 5
text_to_speech("Cuối cùng, bạn đã ăn xong và muốn thanh toán. Người phục vụ đang ở gần đó. Hãy chọn câu trả lời để yêu cầu hóa đơn.", voice="vi-VN-HoaiMyNeural", output_file="scenario5_intro.mp3")
text_to_speech("Is there anything else I can get for you?", voice="en-AU-NatashaNeural", output_file="scenario5_waiter.mp3")
text_to_speech("No, just the check, please.", voice="en-US-GuyNeural", output_file="scenario5_option1.mp3")
text_to_speech("Can I order dessert?", voice="en-AU-NatashaNeural", output_file="scenario5_option2.mp3")
text_to_speech("Do you have a menu?", voice="en-US-GuyNeural", output_file="scenario5_option3.mp3")
text_to_speech("Câu trả lời đúng là số 1 vì bạn đã hoàn thành bữa ăn và muốn thanh toán. Câu trả lời số 2 và số 3 sẽ không phù hợp vì chúng đề cập đến việc gọi thêm món hoặc hỏi về thực đơn.", voice="vi-VN-HoaiMyNeural", output_file="scenario5_feedback.mp3")

# Wrap-up
text_to_speech("Tốt lắm! Bạn đã thực hành chọn phản hồi phù hợp trong từng tình huống tại nhà hàng. Hãy cùng ôn lại các câu trả lời mà bạn đã học hôm nay.", voice="vi-VN-HoaiMyNeural", output_file="wrapup_intro.mp3")
text_to_speech("Table for one, please.", voice="en-AU-NatashaNeural", output_file="review1.mp3")
text_to_speech("Can I have a water, please?", voice="en-US-GuyNeural", output_file="review2.mp3")
text_to_speech("I'll have the grilled salmon with a side salad.", voice="en-AU-NatashaNeural", output_file="review3.mp3")
text_to_speech("What ingredients are in the pasta primavera?", voice="en-US-GuyNeural", output_file="review4.mp3")
text_to_speech("Just the check, please.", voice="en-AU-NatashaNeural", output_file="review5.mp3")
text_to_speech("Xuất sắc! Những câu trả lời này sẽ giúp bạn tự tin hơn trong các tình huống thực tế khi đi ăn nhà hàng. Hãy tiếp tục ôn luyện để phản xạ tốt hơn nhé!", voice="vi-VN-HoaiMyNeural", output_file="final_message.mp3")
