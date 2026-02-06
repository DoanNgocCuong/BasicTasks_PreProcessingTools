

# ```cmd 
# curl -L -X POST "http://103.253.20.13:25010/api/text-to-speech" -H "Content-Type: application/json" -d "{\"text\": \"hello. Its me.Can you tell me?\",\"voice\": \"en-AU-WilliamNeural\",\"speed\": 1}" --output "1.mp3"
# ```

import requests
import json

def text_to_speech(input_text=None, file_path=None, voice="en-AU-NatashaNeural", speed=1, output_file="1.mp3"):
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
    response = requests.post(url, headers=headers, json=data)  # Changed from data=json.dumps(data) to json=data
    with open(output_file, "wb") as file:
        file.write(response.content)
    print(f"Audio file saved as {output_file}")

# Example usage
# text_to_speech("hello. Its me.Can you tell me?")
# text_to_speech(file_path="MucDichCuocSong.txt")

text_to_speech("""
Good morning! What can I get for you today
""", output_file="2_1.mp3")



# ```cmd 
# curl -L -X POST "http://103.253.20.13:25010/api/text-to-speech" -H "Content-Type: application/json" -d "{\"text\": \"hello. Its me.Can you tell me?\",\"voice\": \"en-AU-WilliamNeural\",\"speed\": 1}" --output "1.mp3"
# ```

import requests
import json

def text_to_speech(input_text=None, file_path=None, voice="en-GB-RyanNeural", speed=1, output_file="1.mp3"):
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
    response = requests.post(url, headers=headers, json=data)  # Changed from data=json.dumps(data) to json=data
    with open(output_file, "wb") as file:
        file.write(response.content)
    print(f"Audio file saved as {output_file}")

# Example usage
# text_to_speech("hello. Its me.Can you tell me?")
# text_to_speech(file_path="MucDichCuocSong.txt")

text_to_speech("""
Hi, I’d like a large cappuccino, please
""", output_file="2_2.mp3")