
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


        prompt = f"""
        Phân vai các đoạn hội thoại giữa 'Nhân viên bán hàng' và 'Khách hàng': 

        1. Loại bỏ các từ lỗi: "Ghiền Mì Gõ", "La La La School", "Cảm ơn mọi người. Hẹn gặp lại các bạn trong những video tiếp theo.", "Cảm ơn các bạn đã theo dõi và hẹn gặp lại."
        2. Tuyệt đối không thêm hoặc bớt thông tin nào.
        3. Theo dõi cách xưng hô: Nhân viên bán hàng thường xưng "em" sẽ gọi khách hàng là "anh/chị". 
        
        
        Vui lòng định dạng đầu ra như sau:
        Nhân viên bán hàng: [lời thoại]
        Khách hàng: [lời thoại]
        \n\n{transcription}

        Example : 
        --------
        --------
        Assign roles: 
        Nhân viên bán hàng:
        Dạ em chào anh, em là Trường từ BNAP The Coach. Em có hẹn với anh liên hệ lại sau. Em thấy mình có bấm quan tâm về chương trình học 1-1 của bên em đúng không anh?

        Khách hàng:
        Ừ đúng rồi.

        Nhân viên bán hàng:
        Vâng, em chắc là anh cũng đã từng tham khảo qua trên app đúng không ạ? Với chương trình gia sư 1-1 của bên em, em sẽ giúp anh tập trung nhiều hơn vào luyện nói và mở rộng kỹ năng giao tiếp bằng tiếng Anh. Em biết anh đang quan tâm chương trình học tiếng Anh này để hỗ trợ công việc, hay anh chỉ muốn luyện tập thêm thôi ạ?

        Khách hàng:
        Alo à!

        Nhân viên bán hàng:
        Dạ, anh có thể nói rõ hơn không ạ? Em xin lỗi vì nãy giờ không nghe rõ. Anh đang quan tâm chương trình học tiếng Anh để hỗ trợ công việc hay chỉ đơn giản là luyện tập thêm thôi ạ?

        Khách hàng:
        Tôi muốn cải thiện kỹ năng nói của mình.

        Nhân viên bán hàng:
        Dạ vâng, thế thì em muốn hỏi thêm là về phát âm, anh đã có sẵn nền tảng nào chưa hay mình muốn bắt đầu từ đầu luôn ạ?

        Khách hàng:
        Tôi muốn bắt đầu từ đầu để nắm vững nền tảng.

        Nhân viên bán hàng:
        Dạ, với mục tiêu hiện tại của mình như vậy, anh có đặt ra thời gian cụ thể nào để cải thiện không ạ? Hay anh muốn cải thiện sớm nhất có thể?

        Khách hàng:
        Sớm nhất có thể.

        Nhân viên bán hàng:
        Dạ vâng, bởi vì chương trình học của bên em sẽ giúp anh cá nhân hóa lộ trình học tập, tập trung vào giao tiếp thực tế và mình sẽ thấy hiệu quả ngay sau 2 buổi học. Thay vì học theo phương pháp truyền thống, các mentor sẽ giao tiếp trực tiếp với anh trong một môi trường linh hoạt và dễ dàng. Anh có thấy phù hợp không ạ?

        Khách hàng:
        Có.

        Nhân viên bán hàng:
        Dạ vâng, em sẽ gửi thông tin chi tiết về chương trình gia sư 1-1 qua Zalo nhé. Có gì anh cứ nhắn em qua Zalo để được hỗ trợ thêm. Cảm ơn anh và hẹn gặp lại.

        Khách hàng:
        Cảm ơn.

        Nhân viên bán hàng:
        Dạ vâng, tạm biệt anh.

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
            # Print the assigned roles to terminal
            print('Assigned roles:', assigned_roles)

            return jsonify({'success': True, 'roles': assigned_roles})
        else:
            return jsonify({'success': False, 'msg': 'No response from OpenAI.'})
    except requests.exceptions.RequestException as e:
        print('Request failed:', e)
        return jsonify({'success': False, 'msg': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)