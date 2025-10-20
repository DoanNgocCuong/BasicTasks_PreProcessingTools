# Crawler Video YouTube Có Giọng Trẻ Em

Hệ thống này là một crawler tự động để tìm kiếm, tải xuống và phân tích video YouTube có giọng trẻ em.

## Quy Trình Cơ Bản

1. **Phase 0**: Dọn dẹp manifest
2. **Phase 1**: Tìm kiếm video từ YouTube
3. **Phase 2**: Tải xuống audio
4. **Phase 3**: Phân tích giọng nói (phát hiện giọng trẻ em)
5. **Phase 4**: Lọc và tổ chức file
6. **Phase 5**: Upload lên server

## Cách Chạy

### Chạy Toàn Bộ Hệ Thống

```bash
python -m src.main [OPTIONS]
# hoặc
python src/main.py [OPTIONS]
```

### Chạy Từng Phase Riêng Lẻ

- `python -m src.cleaner.run_clean_phase`
- `python -m src.crawler.run_discovery_phase`
- `python -m src.downloader.run_download_phase`
- `python -m src.analyzer.run_analysis_phase`
- `python -m src.filterer.run_filtering_phase`
- `python -m src.uploader.run_upload_phase`

## Tùy Chỉnh

Để tái sử dụng crawler cho mục đích khác (ví dụ: tìm video về động vật, âm nhạc, v.v.), chỉ cần thay đổi file `analysis_phases.py` để phân tích nội dung theo ý muốn.

## Cấu Hình .env

File `.env` chứa các biến cấu hình cho hệ thống. Dưới đây là giải thích chi tiết về từng trường:

### YouTube API Configuration

- `YOUTUBE_API_KEY_1`, `YOUTUBE_API_KEY_2`, `YOUTUBE_API_KEY_3`: Các khóa API YouTube Data v3. Hệ thống sẽ sử dụng các khóa này để truy vấn YouTube. Nếu một khóa hết quota, hệ thống sẽ tự động chuyển sang khóa tiếp theo.
- `POLL_INTERVAL_SECONDS`: Khoảng thời gian chờ giữa các lần gọi API YouTube (giây). Giá trị mặc định 300 giây giúp tránh bị rate limit.

### Audio Processing Configuration

- `MAX_AUDIO_DURATION_SECONDS`: Thời lượng tối đa của mỗi đoạn audio được xử lý (giây). Audio dài hơn sẽ được chia thành các chunk nhỏ hơn để phân tích.
- `AUDIO_QUALITY`: Chất lượng audio tải xuống (high/medium/low). Hiện tại chưa được sử dụng trong code chính.

### Model Configuration

- `WHISPER_MODEL_SIZE`: Kích thước mô hình Whisper cho nhận dạng ngôn ngữ. Hiện tại chưa được sử dụng trong code chính.
- `WAV2VEC2_MODEL`: Mô hình wav2vec2 sử dụng để phát hiện giọng nói trẻ em và phân loại tuổi. Mặc định là "audeering/wav2vec2-large-robust-24-ft-age-gender".

### Processing Configuration

- `MAX_WORKERS`: Số worker tối đa cho xử lý đa luồng. Hiện tại chưa được sử dụng trực tiếp.
- `CHILD_THRESHOLD`: Ngưỡng xác suất để phân loại giọng nói là trẻ em (0.0-1.0). Giá trị cao hơn làm cho việc phát hiện trẻ em nghiêm ngặt hơn.
- `AGE_THRESHOLD`: Ngưỡng độ tin cậy cho việc phát hiện ngôn ngữ (0.0-1.0). Ảnh hưởng đến độ chính xác của việc phân loại ngôn ngữ.

### Debug Configuration

- `DEBUG_MODE`: Bật chế độ debug (true/false). Khi bật, hệ thống sẽ ghi log chi tiết hơn.
- `LOG_LEVEL`: Mức độ log (INFO/DEBUG/WARNING/ERROR). Kiểm soát lượng thông tin được ghi vào log.

### File Paths

- `OUTPUT_DIR`: Thư mục đầu ra chính (tùy chọn). Nếu không chỉ định, sử dụng giá trị mặc định.
- `TEMP_AUDIO_DIR`: Thư mục tạm thời cho audio (tùy chọn). Nếu không chỉ định, sử dụng giá trị mặc định.

**Lưu ý**: Để thay đổi cấu hình, chỉnh sửa file `.env` và khởi động lại hệ thống.

**Lưu ý**:

- Nhớ thay đổi `queries.txt` cho mỗi batch để có kết quả tìm kiếm đa dạng.
- Trước khi chạy bất kỳ phase nào, hãy chạy `python sort_queries.py` để sắp xếp queries từ ngắn đến dài và loại bỏ trùng lặp. Điều này giúp bắt đầu với queries rộng hơn trước, tăng khả năng tìm thấy nhiều kết quả hơn.
- Trước khi chạy các phase, cần khởi động API server bằng cách chạy `python src/uploader/start_server.py`.
- Để thay đổi URL API, chỉnh sửa biến `SERVER_URL` trong file `src/uploader/client.py`.
- Để biết đường dẫn chính xác của các file đã upload trên server, kiểm tra output console trong phase upload. Mỗi file sẽ hiển thị đường dẫn dạng `uploaded_files/{folder_id}/{language}/{filename}`, và `folder_id` được hiển thị khi bắt đầu session upload.
