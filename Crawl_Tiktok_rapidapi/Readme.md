Tôi sẽ giải thích chức năng chính của từng file:

1. **File 1 - Lấy thông tin user TikTok:**
```python
# Chức năng: Thu thập thông tin cơ bản của user TikTok
- Lấy thông tin user từ Airtable (view "0_no_info")
- Gọi TikTok API để lấy thông tin chi tiết của user
- Cập nhật thông tin vào Airtable:
  + Thông tin cá nhân (id, nickname, secUid, avatar...)
  + Số liệu thống kê (followers, following, likes...)
```

2. **File 2 - Lấy danh sách video của user:**
```python
# Chức năng: Thu thập tất cả video của một user TikTok
- Lấy danh sách users từ Airtable (view "1_info") 
- Với mỗi user:
  + Gọi TikTok API để lấy toàn bộ video
  + Lưu thông tin video vào Airtable:
    * Thông tin video (id, description, createtime...)
    * Số liệu tương tác (views, likes, comments...)
- Kiểm tra trùng lặp để không lưu video đã có
```

3. **File 3 - Lấy comments của video:**
```python
# Chức năng: Thu thập comments của các video
- Lấy danh sách video từ Airtable (view "0_no_comment")
- Với mỗi video:
  + Gọi TikTok API để lấy toàn bộ comments
  + Format comments theo cấu trúc: [user_id][comment_text]
  + Chia nhỏ comments nếu quá dài
  + Lưu vào nhiều trường comments_1, comments_2... trong Airtable
```

4. **File 4 - Tải video và tạo transcript:**
```python
# Chức năng: Tải video và chuyển thành văn bản
- Lấy danh sách video từ Airtable (view "1_download")
- Với mỗi video:
  + Tải video về máy
  + Sử dụng Azure OpenAI Whisper để chuyển giọng nói thành văn bản
  + Format transcript với timestamp
  + Lưu transcript vào Airtable
```

5. **File 5 - Phân tích comments:**
```python
# Chức năng: Phân tích insights từ comments
- Lấy video từ Airtable (view "0_extract_2")
- Sử dụng GPT-4 để phân tích:
  + Persona của người comment
  + Phản ứng/cảm xúc
  + Pain points
  + Nhu cầu
  + Insights ẩn
- Lưu kết quả phân tích vào Airtable
```

6. **File 6 - Phân tích nội dung video:**
```python
# Chức năng: Phân tích nội dung và marketing của video
- Lấy video từ Airtable (view "0_extract")
- Sử dụng GPT-4 để phân tích:
  + Phân loại nội dung (học tiếng Anh/khác)
  + Mục đích video
  + Sản phẩm/giải pháp được quảng bá
  + Phân tích marketing (hook, message, audience...)
  + Đánh giá chuyên môn
- Lưu kết quả phân tích vào Airtable
```

Đây là một hệ thống hoàn chỉnh để:
1. Thu thập dữ liệu từ TikTok
2. Xử lý và chuyển đổi nội dung
3. Phân tích sâu bằng AI
4. Lưu trữ có cấu trúc trong Airtable
