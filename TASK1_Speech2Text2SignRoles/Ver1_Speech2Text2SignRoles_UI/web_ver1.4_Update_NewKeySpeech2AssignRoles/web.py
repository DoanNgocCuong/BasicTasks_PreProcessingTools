from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_audio', methods=['POST'])
def process_audio():
    if 'file' not in request.files:
        return jsonify({'success': False, 'msg': 'No file part'})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'msg': 'No selected file'})
    
    try:
        url = "http://103.253.20.13:25024/role_assign"
        files = {
            "audio": (file.filename, file, 'audio/mpeg'),
            "secret_key": (None, "codedongian")
        }

        response = requests.post(url, files=files, timeout=60)
        response.raise_for_status()
        result = response.json()
        
        if result["success"]:
            return jsonify({'success': True, 'roles': result['result']})
        else:
            return jsonify({'success': False, 'msg': result['msg']})
    except requests.exceptions.RequestException as e:
        return jsonify({'success': False, 'msg': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)