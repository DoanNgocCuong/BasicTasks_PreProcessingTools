Tôi sẽ hướng dẫn bạn cách chạy chương trình này:

### 1. Cài đặt các thư viện cần thiết

Đầu tiên, cài đặt tất cả các thư viện được liệt kê trong `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Tạo file .env

Tạo một file `.env` trong thư mục gốc của project và thêm API key của RapidAPI:

```plaintext
RAPID_API_KEY=your_rapidapi_key_here
```

Thay `your_rapidapi_key_here` bằng API key thật của bạn từ RapidAPI.

### 3. Chạy chương trình

Có thể chạy chương trình với các định dạng URL khác nhau:

```bash
# Sử dụng handle (@username)
python main_userNameChanelYoutube_getVideos.py --url "https://www.youtube.com/@mkbhd"

# Hoặc sử dụng channel ID
python main_userNameChanelYoutube_getVideos.py --url "https://www.youtube.com/channel/UCBJycsmduvYEL83R_U4JriQ"

# Hoặc sử dụng custom URL
python main_userNameChanelYoutube_getVideos.py --url "https://www.youtube.com/c/mkbhd"
```

### 4. Kết quả

Sau khi chạy thành công:

1. Chương trình sẽ in ra JSON chứa thông tin về các video đã tìm thấy
2. Tự động tạo một thư mục `output` (nếu chưa tồn tại)
3. Tạo file Excel trong thư mục `output` với tên format: `videos_[channel_id]_[timestamp].xlsx`

### 5. Cấu trúc thư mục

```
Crawl_Youtube_rapidapi/
├── api-chanelYoutube-get-video/
│   ├── main_userNameChanelYoutube_getVideos.py
│   ├── def_chanelID_get_videos.py
│   ├── def_xtracrt_chanelID_fromUsername.py
│   ├── utils_savelistVideos2Excel.py
│   ├── requirements.txt
│   ├── .env
│   └── output/
│       └── videos_[channel_id]_[timestamp].xlsx
```

### 6. Ví dụ cụ thể

```bash
# Ví dụ lấy video từ kênh Marques Brownlee
python main_userNameChanelYoutube_getVideos.py --url "https://www.youtube.com/@mkbhd"
```

Output sẽ hiển thị:
```
2024-XX-XX XX:XX:XX,XXX - INFO - Channel ID: UCBJycsmduvYEL83R_U4JriQ
2024-XX-XX XX:XX:XX,XXX - INFO - Tìm thấy XX video
2024-XX-XX XX:XX:XX,XXX - INFO - Đã lưu danh sách video vào file: output/videos_UCBJycsmduvYEL83R_U4JriQ_20240312_123456.xlsx
```

### 7. Lưu ý quan trọng

1. Đảm bảo có kết nối internet ổn định
2. API key phải còn hiệu lực và có đủ quota
3. URL kênh YouTube phải là kênh công khai
4. Nếu gặp lỗi, kiểm tra log để biết chi tiết

### 8. Xử lý lỗi thường gặp

1. **Lỗi "Invalid API key"**:
   - Kiểm tra lại API key trong file `.env`
   - Đảm bảo đã đăng ký dịch vụ trên RapidAPI

2. **Lỗi "Channel not found"**:
   - Kiểm tra URL kênh có chính xác không
   - Đảm bảo kênh không bị ẩn/xóa

3. **Lỗi "No videos found"**:
   - Kiểm tra kênh có video công khai không
   - Thử với kênh YouTube khác

4. **Lỗi thư viện**:
   - Chạy lại lệnh cài đặt thư viện
   ```bash
   pip install -r requirements.txt
   ```
