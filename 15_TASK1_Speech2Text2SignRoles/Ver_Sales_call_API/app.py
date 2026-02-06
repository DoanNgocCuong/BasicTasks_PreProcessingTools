from flask import Flask, request, jsonify, render_template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, Call
import logging
import requests
import json
from process_audio import process_audio_file

# Cấu hình logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config.from_pyfile('config.py')

# Kết nối đến Database
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'success': False, 'msg': 'No audio file provided'})

    file = request.files['file']
    call = Call(file_name=file.filename)
    session.add(call)
    session.commit()

    result = process_audio_file(file)

    call.transcription = result.get('transcription', '')
    call.assigned_roles = result.get('roles', '')
    session.commit()

    return jsonify(result)

@app.route('/calls', methods=['GET'])
def get_calls():
    calls = session.query(Call).all()
    return jsonify([call.to_dict() for call in calls])

@app.route('/calls/<int:call_id>', methods=['GET'])
def get_call(call_id):
    call = session.query(Call).get(call_id)
    return jsonify(call.to_dict())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)