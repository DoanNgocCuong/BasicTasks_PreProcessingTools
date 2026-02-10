from flask import Flask, request, jsonify
import os
import subprocess
import re
import json

app = Flask(__name__)
UPLOAD_FOLDER = './input'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
PORT = 25024
SECRET_KEY = "codedongian"

@app.route('/role_assign', methods=['POST'])
def role_assign():
    secret_key = request.form.get('secret_key')
    if secret_key != SECRET_KEY:
        return jsonify({'error': 'Invalid secret key'}), 403

    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio = request.files['audio']
    if audio.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    language = request.form.get('language', 'vi')  
    
    file_path = os.path.join(UPLOAD_FOLDER, audio.filename)
    audio.save(file_path)
    
    try:
        result = subprocess.run(
            ['python', 'diarize_parallel_1p.py', '--no-stem', '--whisper-model', 'large-v3', '--device', 'cuda', '--language', language, '-a', file_path],
            capture_output=True,
            text=True,
            encoding='utf-8'  # Ensure the output is decoded as UTF-8
        )
        
        if result.returncode != 0:
            return jsonify({'error': 'Processing failed', 'details': result.stderr}), 500
        
        # Extract JSON portion from result.stdout
        json_match = re.search(r"\[\{'speaker': .*?\}\]", result.stdout)
        if json_match:
        # Replace " with ' in the matched output
            processed_output = json_match.group(0).replace('"', "'")
            return jsonify({'output': processed_output}), 200
        else:
            return jsonify({'error': 'No valid output found'}), 500  
      
        # Convert the matched portion to valid JSON
        json_output = json.loads(json_match.group(0).replace("'", '"'))
        
        return jsonify(json_output)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(port=PORT)
