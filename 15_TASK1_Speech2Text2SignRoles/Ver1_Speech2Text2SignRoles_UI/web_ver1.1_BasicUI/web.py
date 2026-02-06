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
        return jsonify({'success': False, 'msg': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
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

        # Tăng thời gian chờ lên 60 giây
        stt_response = requests.post(stt_url, headers=headers, files=files, timeout=60)
        stt_response.raise_for_status()
        stt_result = stt_response.json()
        if stt_result["success"]:
            transcription = stt_result['result']['text']
            return jsonify({'success': True, 'transcription': transcription})
        else:
            return jsonify({'success': False, 'msg': stt_result['msg']})
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'msg': str(e)})

@app.route('/assign_roles', methods=['POST'])
def assign_roles():
    transcription = request.json.get('transcription')
    if not transcription:
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
        
        openai_response = requests.post(openai_url, headers=openai_headers, data=json.dumps(openai_data))
        openai_response.raise_for_status()
        openai_result = openai_response.json()
        if 'choices' in openai_result and len(openai_result['choices']) > 0:
            assigned_roles = openai_result['choices'][0]['message']['content']
            return jsonify({'success': True, 'roles': assigned_roles})
        else:
            return jsonify({'success': False, 'msg': 'No response from OpenAI.'})
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'msg': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
