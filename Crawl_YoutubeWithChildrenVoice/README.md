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

**Lưu ý**: Nhớ thay đổi `queries.txt` cho mỗi batch để có kết quả tìm kiếm đa dạng.
