import requests
import json
import logging

def process_audio_file(file):
    logging.info("Starting speech-to-text conversion.")
    stt_url = "http://42.96.42.156:6112/api/v1/asr/audio"
    stt_token = "su-ewiuwernmvf1ifmdsafajkdfaiwwe"
    headers = {"accept": "application/json"}
    files = {
        "token": (None, stt_token),
        "language": (None, "vi"),
        "file": (file.filename, file, 'audio/mpeg')
    }

    stt_response = requests.post(stt_url, headers=headers, files=files, timeout=60)
    stt_response.raise_for_status()
    stt_result = stt_response.json()
    logging.info("Speech-to-text conversion completed successfully.")

    if stt_result["success"]:
        transcription = stt_result['result']['text']
        logging.info("Transcription: %s", transcription)
    else:
        logging.error("Speech-to-text conversion failed: %s", stt_result['msg'])
        return {'success': False, 'msg': stt_result['msg']}
    
    logging.info("Starting role assignment using OpenAI API.")
    openai_url = "https://api.openai.com/v1/chat/completions"
    openai_headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer sk-proj-hrHNTMh5L6sxEs669JfqT3BlbkFJvyPqaiPjlIX4hYbHrcPT"
    }

    prompt = f"""
    Phân vai các đoạn hội thoại giữa 'Nhân viên bán hàng' và 'Khách hàng': 

    1. Loại bỏ các từ lỗi: "Ghiền Mì Gõ", "La La La School", "Cảm ơn mọi người. Hẹn gặp lại các bạn trong những video tiếp theo.", "Cảm ơn các bạn đã theo dõi và hẹn gặp lại."
    2. Tuyệt đối không thêm hoặc bớt thông tin nào.
    3. Theo dõi cách xưng hô: Nhân viên bán hàng thường xưng "em" sẽ gọi khách hàng là "anh/chị". 
    
    Vui lòng định dạng đầu ra như sau:
    Nhân viên bán hàng: [lời thoại]
    Khách hàng: [lời thoại]
    \n\n{transcription}
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

    openai_response = requests.post(openai_url, headers=openai_headers, data=json.dumps(openai_data))
    openai_response.raise_for_status()
    openai_result = openai_response.json()
    logging.info("Role assignment completed successfully.")

    if 'choices' in openai_result and len(openai_result['choices']) > 0:
        assigned_roles = openai_result['choices'][0]['message']['content']
        logging.info("Assigned roles: %s", assigned_roles)
        return {'success': True, 'transcription': transcription, 'roles': assigned_roles}
    else:
        logging.error("No response from OpenAI API.")
        return {'success': False, 'msg': 'No response from OpenAI.'}