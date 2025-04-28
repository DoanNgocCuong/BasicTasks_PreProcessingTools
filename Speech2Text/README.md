### Chuyển từ run trên server về local

Để chạy code này trên local thay vì trên server, chúng ta cần thực hiện một số thay đổi nhỏ. Dưới đây là các chỉnh sửa cần thiết:

```python:role_assign_local.py
# ... existing code ...

@app.route('/role_assign', methods=['POST'])
def role_assign():
    # Xóa kiểm tra secret key vì đang chạy local
    # if secret_key != SECRET_KEY:
    #     return jsonify({'error': 'Invalid secret key'}), 403

    # ... existing code ...

    try:
        result = subprocess.run(
            ['python', 'diarize_parallel_1p.py', '--no-stem', '--whisper-model', 'large-v3', '--device', 'cuda', '--language', language, '-a', file_path],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        # ... existing code ...

if __name__ == '__main__':
    app.run(port=PORT, debug=True)
```

Giải thích các thay đổi:

1. Đã xóa phần kiểm tra secret key vì khi chạy local, chúng ta không cần kiểm tra này nữa.

2. Thêm tham số `debug=True` vào `app.run()`. Điều này sẽ kích hoạt chế độ debug, giúp bạn dễ dàng phát hiện và sửa lỗi khi chạy ứng dụng locally.

Những thay đổi này sẽ cho phép bạn chạy ứng dụng Flask trên máy local của mình. Để chạy ứng dụng, bạn chỉ cần thực hiện lệnh sau trong terminal:

```
python role_assign_local.py
```

Sau đó, bạn có thể truy cập ứng dụng tại `http://localhost:25024/role_assign` và gửi các yêu cầu POST đến endpoint này.

Lưu ý rằng bạn vẫn cần đảm bảo rằng tất cả các dependencies cần thiết (như Flask) đã được cài đặt và file `diarize_parallel_1p.py` cũng như thư mục `input` tồn tại trong cùng thư mục với file `role_assign_local.py`.

Lưu ý ko run được trên web mà sẽ test qua POSTMAN 
```
Method Not Allowed
The method is not allowed for the requested URL.
```


-----------------------------

API

```bash
curl --location 'http://103.253.20.13:25029/role_assign' \
--form 'audio=@"/path/to/file"' \
--form 'secret_key="codedongian"' \
--form 'language="en"'
```

```
output: {
    "output": "[{'speaker': 'Speaker 0', 'start_time': 220, 'end_time': 2160, 'text': 'Chapter 2 What is the purpose of life? '}, {'speaker': 'Speaker 0', 'start_time': 3140, 'end_time': 7180, 'text': 'Translator, Luan Nguyen Please keep listening, everyone. '}, {'speaker': 'Speaker 0', 'start_time': 8260, 'end_time': 11320, 'text': 'Some of you have been to this retreat before, while others are new to it. '}, {'speaker': 'Speaker 0', 'start_time': 12360, 'end_time': 17160, 'text': 'When you listen to the lecture, try to keep your mouth closed naturally and pay attention to what's being said. '}, {'speaker': 'Speaker 0', 'start_time': 18180, 'end_time': 23160, 'text': 'In Buddhism, there are two important terms that describe the journey of a practitioner, wisdom and unwisdom. '}, {'speaker': 'Speaker 0', 'start_time': 24280, 'end_time': 25260, 'text': 'So, what do they mean? '}, {'speaker': 'Speaker 0', 'start_time': 26340, 'end_time': 28860, 'text': 'Wisdom is about truly understanding things as they are. '}, {'speaker': 'Speaker 0', 'start_time': 29860, 'end_time': 32040, 'text': 'It's also known as right view or enlightenment. '}, {'speaker': 'Speaker 0', 'start_time': 33100, 'end_time': 37200, 'text': 'On the other hand, unwisdom means having an incorrect understanding of things and phenomena. '}, {'speaker': 'Speaker 0', 'start_time': 38340, 'end_time': 41440, 'text': 'This is also called wrong view, false thinking, or delusion. '}, {'speaker': 'Speaker 0', 'start_time': 42520, 'end_time': 49800, 'text': 'When you observe or examine any phenomenon, there are two types of knowledge to consider, the wisdom taught by the Buddha and the unwisdom of ordinary people. '}, {'speaker': 'Speaker 0', 'start_time': 50840, 'end_time': 54760, 'text': 'The goal of Buddhist practice is to overcome unwisdom and cultivate wisdom instead. '}, {'speaker': 'Speaker 0', 'start_time': 55840, 'end_time': 56780, 'text': 'Why is this the case? '}, {'speaker': 'Speaker 0', 'start_time': 57840, 'end_time': 60680, 'text': 'Well, it's because the way we live is determined by what we know. '}, {'speaker': 'Speaker 0', 'start_time': 61800, 'end_time': 62900, 'text': 'Let me give you an example. '}, {'speaker': 'Speaker 0', 'start_time': 63120, 'end_time': 66720, 'text': 'Imagine a two-year-old child who sees a red-hot coal burning in the fireplace. '}, {'speaker': 'Speaker 0', 'start_time': 67760, 'end_time': 73760, 'text': 'Even though the child may recognize the object as a coal, they don't fully understand the danger of touching it with their bare hands. '}, {'speaker': 'Speaker 0', 'start_time': 74840, 'end_time': 79040, 'text': 'So, if there's no one around to stop them, they might grab the coal and burn their hands badly. '}, {'speaker': 'Speaker 0', 'start_time': 80080, 'end_time': 85780, 'text': 'But for adults, who have a better understanding of the danger of a burning coal, they wouldn't touch it with their bare hands or feet. '}, {'speaker': 'Speaker 0', 'start_time': 86780, 'end_time': 90680, 'text': 'By living according to this knowledge, they can avoid suffering from burns or injuries. '}, {'speaker': 'Speaker 0', 'start_time': 91740, 'end_time': 93360, 'text': 'Our knowledge determines how we live. '}, {'speaker': 'Speaker 0', 'start_time': 94380, 'end_time': 103120, 'text': 'Children with limited knowledge might touch a burning coal and suffer, while adults with a deeper understanding of risks will avoid touching it with bare hands, preventing unnecessary pain. '}, {'speaker': 'Speaker 0', 'start_time': 104160, 'end_time': 113540, 'text': 'In the same way, if someone's understanding of daily life is based on delusion, confusion, or wrong views, it's like being a child who doesn't understand the danger of touching a burning coal. '}, {'speaker': 'Speaker 0', 'start_time': 114680, 'end_time': 118820, 'text': 'This leads to conflicts with reality and their life becomes filled with sorrow and suffering. '}, {'speaker': 'Speaker 0', 'start_time': 119840, 'end_time': 127040, 'text': 'If a person has wisdom, right view, and insight, and understands the truth about things and phenomena, their life won't be in conflict with reality. '}, {'speaker': 'Speaker 0', 'start_time': 128160, 'end_time': 129960, 'text': 'They won't experience grief or sorrow. '}, {'speaker': 'Speaker 0', 'start_time': 131039, 'end_time': 140560, 'text': 'As I mentioned earlier regarding wisdom and unwisdom, anyone can feel the crunchy texture when chewing on a sesame cracker, whether they are an ahat, a wise person, or an ordinary individual. '}, {'speaker': 'Speaker 0', 'start_time': 141680, 'end_time': 144920, 'text': 'However, there are two types of knowledge that arise from this experience. '}, {'speaker': 'Speaker 0', 'start_time': 146040, 'end_time': 155080, 'text': 'One is the knowledge of unwisdom, which assumes that the brittle texture of the sesame crackers is the actual material nature of it, and that crispness is an inherent quality of the sesame crackers. '}, {'speaker': 'Speaker 0', 'start_time': 156180, 'end_time': 160100, 'text': 'This type of knowledge is considered unwisdom, delusion, and illusion in Buddhism. '}, {'speaker': 'Speaker 0', 'start_time': 161140, 'end_time': 166860, 'text': 'The second understanding is that brittleness is a sensation created in one's mind rather than being a property of matter. '}, {'speaker': 'Speaker 0', 'start_time': 167900, 'end_time': 173500, 'text': 'It arises from the teeth coming into contact with the sesame crackers and is impermanent, onerous and non-possessive. '}, {'speaker': 'Speaker 0', 'start_time': 174580, 'end_time': 175600, 'text': 'This knowledge is wisdom. '}, {'speaker': 'Speaker 0', 'start_time': 176720, 'end_time': 183040, 'text': 'Therefore, not only should one examine the brittleness of phenomena, but all phenomena should be examined through these two types of knowledge. '}, {'speaker': 'Speaker 0', 'start_time': 184140, 'end_time': 185440, 'text': 'Why should we strive for wisdom? '}, {'speaker': 'Speaker 0', 'start_time': 186460, 'end_time': 193720, 'text': 'to attain it, live by it, to end confusion, gain insight, live in harmony with reality, and free ourselves from suffering. '}]"
}

```


README `app.py`
=> With 2 audio => ra Transcription đã phân vai. 