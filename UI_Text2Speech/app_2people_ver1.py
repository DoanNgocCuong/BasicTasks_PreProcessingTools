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

# Conversation
text_to_speech("Good morning! What can I get for you today?", output_file="2_1.mp3")  # Nhân viên pha chế
text_to_speech("Hi, I'd like a large cappuccino, please.", voice="en-US-GuyNeural", output_file="2_2.mp3")  # Khách hàng
text_to_speech("Sure thing! Would you like any flavor in that?", output_file="2_3.mp3")  # Nhân viên pha chế
text_to_speech("Yes, can I add vanilla?", voice="en-US-GuyNeural", output_file="2_4.mp3")  # Khách hàng
text_to_speech("Of course! That'll be $4.50. Are you paying with cash or card?", output_file="2_5.mp3")  # Nhân viên pha chế
text_to_speech("Card, please.", voice="en-US-GuyNeural", output_file="2_6.mp3")  # Khách hàng
text_to_speech("Great, please tap your card here. Enjoy your coffee!", output_file="2_7.mp3")  # Nhân viên pha chế
text_to_speech("Thanks! Have a nice day.", voice="en-US-GuyNeural", output_file="2_8.mp3")  # Khách hàng