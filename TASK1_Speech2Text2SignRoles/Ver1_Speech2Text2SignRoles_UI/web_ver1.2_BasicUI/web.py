from flask import Flask, render_template, request, jsonify
import requests
import json

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/speech_to_text', methods=['POST'])
def speech_to_text():
    if 'file' not in request.files:
        print('No file part')
        return jsonify({'success': False, 'msg': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        print('No selected file')
        return jsonify({'success': False, 'msg': 'No selected file'})
    
    try:
        stt_url = "http://42.96.42.156:6112/api/v1/asr/audio"
        stt_token = "su-ewiuwernmvf1ifmdsafajkdfaiwwe"
        headers = {"accept": "application/json"}
        files = {
            "token": (None, stt_token),
            "language": (None, "vi"),
            "file": (file.filename, file, 'audio/mpeg')
        }

        print('Sending request to speech-to-text API')
        stt_response = requests.post(stt_url, headers=headers, files=files, timeout=60)
        stt_response.raise_for_status()
        stt_result = stt_response.json()
        print('Received response from speech-to-text API:', stt_result)
        if stt_result["success"]:
            transcription = stt_result['result']['text']
            return jsonify({'success': True, 'transcription': transcription})
        else:
            return jsonify({'success': False, 'msg': stt_result['msg']})
    except requests.exceptions.RequestException as e:
        print('Request failed:', e)
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/assign_roles', methods=['POST'])
def assign_roles():
    transcription = request.json.get('transcription')
    if not transcription:
        print('No transcription provided')
        return jsonify({'success': False, 'msg': 'No transcription provided'})
    
    try:
        openai_url = "https://api.openai.com/v1/chat/completions"
        openai_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer sk-proj-hrHNTMh5L6sxEs669JfqT3BlbkFJvyPqaiPjlIX4hYbHrcPT"
        }
        openai_data = {
            "model": "gpt-4-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": f"Phân vai các đoạn hội thoại giữa 'Nhân viên bán hàng' và 'Khách hàng':\n\n{transcription}"
                }
            ]
        }

        print('Sending request to OpenAI API')
        openai_response = requests.post(openai_url, headers=openai_headers, data=json.dumps(openai_data))
        openai_response.raise_for_status()
        openai_result = openai_response.json()
        print('Received response from OpenAI API:', openai_result)
        if 'choices' in openai_result and len(openai_result['choices']) > 0:
            assigned_roles = openai_result['choices'][0]['message']['content']
            # Print the assigned roles to terminal
            print('Assigned roles:', assigned_roles)  # Dòng này được thêm vào
            return jsonify({'success': True, 'roles': assigned_roles})
        else:
            return jsonify({'success': False, 'msg': 'No response from OpenAI.'})
    except requests.exceptions.RequestException as e:
        print('Request failed:', e)
        return jsonify({'success': False, 'msg': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
