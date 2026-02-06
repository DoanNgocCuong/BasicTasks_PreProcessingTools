

Đây là các lệnh cURL để test API lấy videos từ channel YouTube:

```bash
# 1. Test với channel URL chuẩn (channel ID)
curl -X GET "http://localhost:8080?url=https://www.youtube.com/channel/UC-lHJZR3Gqxm24_Vd_AJ5Yw"

# 2. Test với custom URL (@username)
curl -X GET "http://localhost:8080?url=https://www.youtube.com/@MrBeast"

# 3. Test với URL dạng /c/
curl -X GET "http://localhost:8080?url=https://www.youtube.com/c/MrBeast"

# 4. Test với URL dạng user cũ
curl -X GET "http://localhost:8080?url=https://www.youtube.com/user/PewDiePie"
```

Để chạy được, cần thực hiện các bước:

1. Set API key:
```bash
# Windows CMD
set RAPID_API_KEY=your_api_key_here

# Windows PowerShell
$env:RAPID_API_KEY="your_api_key_here"

# Linux/Mac
export RAPID_API_KEY=your_api_key_here
```

2. Chạy server:
```bash
python -m functions_framework --target get_youtube_channel_videos --port 8080
```

3. Mở terminal mới và chạy các lệnh cURL ở trên

Lưu ý: Thay `your_api_key_here` bằng API key thật của bạn từ RapidAPI.
