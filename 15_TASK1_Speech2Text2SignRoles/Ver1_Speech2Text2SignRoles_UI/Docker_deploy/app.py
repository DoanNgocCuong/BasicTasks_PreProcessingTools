from flask import Flask, render_template, request, jsonify
import requests
import json
import os

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
        stt_token = os.getenv('STT_TOKEN')
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
        openai_token = os.getenv('OPENAI_API_KEY')
        openai_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai_token}"
        }

        prompt = f"""
        - Đọc kỹ toàn bộ nội dung để hiểu rõ cuộc hội thoại. Việc này sẽ giúp phân vai chính xác hơn.
        - Phân vai các đoạn hội thoại giữa 'Nhân viên bán hàng' và 'Khách hàng'.
        - Chú ý đặc biệt đến cách xưng hô (anh, chị, em, ...) để duy trì đúng việc phân vai xuyên suốt cuộc hội thoại.
        - Đảm bảo sử dụng nhất quán cách xưng hô cho mỗi vai trong toàn bộ cuộc đối thoại.

        Ngoài ra:
        - Sửa các lỗi chính tả trong lời thoại nếu có.
        - Tuyệt đối không thêm hoặc bớt thông tin nào.

        Đoạn hội thoại:
        {transcription}

        Vui lòng định dạng đầu ra như sau:
        Nhân viên bán hàng: [lời thoại]
        Khách hàng: [lời thoại]

        Lưu ý: Duy trì cách xưng hô nhất quán cho mỗi vai trong toàn bộ cuộc đối thoại.
        """

        openai_data = {
            "model": "gpt-4-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
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
            print('Assigned roles:', assigned_roles)
            return jsonify({'success': True, 'roles': assigned_roles})
        else:
            return jsonify({'success': False, 'msg': 'No response from OpenAI.'})
    except requests.exceptions.RequestException as e:
        print('Request failed:', e)
        return jsonify({'success': False, 'msg': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)