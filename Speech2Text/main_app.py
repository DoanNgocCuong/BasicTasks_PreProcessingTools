import requests
import os
import json
import re

url = 'http://103.253.20.13:25029/role_assign'

def process_audio(audio_path, language):
    audio_filename = os.path.basename(audio_path)
    output_filename = os.path.splitext(audio_filename)[0] + '.txt'
    
    with open(audio_path, 'rb') as audio_file:
        files = {'audio': audio_file}
        data = {
            'secret_key': 'codedongian',
            'language': language
        }

        response = requests.post(url, files=files, data=data)

        if response.status_code == 200:
            output = response.json()
            with open(output_filename, 'w', encoding='utf-8') as output_file:
                json.dump(output, output_file, ensure_ascii=False, indent=2)
            print(f"Output saved to {output_filename}")
            return output
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return None

def extract_dicts(s):
    pattern = r"\{[^{}]*\}"
    matches = re.findall(pattern, s)
    result = []
    for match in matches:
        try:
            match = match.replace("'", '"')
            d = json.loads(match)
            result.append(d)
        except json.JSONDecodeError:
            print(f"Error decoding JSON: {match}")
    return result

def format_time(milliseconds):
    seconds = milliseconds // 1000
    minutes = seconds // 60
    hours = minutes // 60
    return f"{hours:02d}:{minutes%60:02d}:{seconds%60:02d}"

# Process English audio
output1 = process_audio(r'D:\OneDrive - Hanoi University of Science and Technology\ITE10-DS&AI-HUST\Learn&Task\PRODUCT_THECOACH\Đã đẩy lên GITHUB\BasicTasks_PreProcessingTools\Speech2Text\outptut\Mentor.m4a', 'en')

# Process English audio
output2 = process_audio(r'D:\OneDrive - Hanoi University of Science and Technology\ITE10-DS&AI-HUST\Learn&Task\PRODUCT_THECOACH\Đã đẩy lên GITHUB\BasicTasks_PreProcessingTools\Speech2Text\outptut\Mentee.m4a', 'en')

if output1 and output2:
    output1_data = extract_dicts(output1['output'])
    output2_data = extract_dicts(output2['output'])

    for item in output1_data:
        item['speaker'] = 'Mentor'

    for item in output2_data:
        item['speaker'] = 'Mentee'

    combined_output = sorted(output1_data + output2_data, key=lambda x: x['start_time'])

    formatted_output = []
    for item in combined_output:
        formatted_time = format_time(item['start_time'])
        formatted_output.append(f"[{formatted_time}] Speaker {item['speaker']}: {item['text']}")

    with open('output.txt', 'w', encoding='utf-8') as f:
        f.write("\n".join(formatted_output))

    print("Output has been saved to output.txt")
else:
    print("Error processing audio files. Please check the file paths and try again.")