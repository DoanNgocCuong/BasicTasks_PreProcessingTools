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

# Customer order
text_to_speech("I'd like a large cappuccino, please.", voice="en-AU-NatashaNeural", output_file="5_1.mp3")

# Customer asking about flavor
text_to_speech("Can I add vanilla?", voice="en-AU-NatashaNeural", output_file="5_2.mp3")

# Customer asking about payment
text_to_speech("Are you paying with cash or card?", voice="en-AU-NatashaNeural", output_file="5_3.mp3")
