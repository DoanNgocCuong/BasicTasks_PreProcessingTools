**Kiểm tra tính ngẫu nhiên (randomness) trong code hiện tại:**

Dưới đây là phân tích chi tiết từng thành phần trong pipeline của bạn để xác định xem có yếu tố random nào ảnh hưởng đến kết quả qua các lần chạy hay không:

---

**1. Model inference (model.eval()):**  
Bạn đã gọi `self.model.eval()` sau khi load model.  
- Điều này đảm bảo các layer như Dropout, BatchNorm (nếu có) hoạt động ở chế độ xác định (deterministic).  
- Với mô hình wav2vec2 inference (không training), các layer đều hoạt động cố định tại mỗi lần chạy.

**2. Xử lý audio (librosa, numpy):**
- Hàm `librosa.load` chỉ đọc file audio, không có random augmentation nào.
- Hàm resample và normalize cũng hoàn toàn xác định.
- Không có bước nào liên quan đến thêm nhiễu, thay đổi tốc độ, thay đổi pitch, hay cắt đoạn ngẫu nhiên.

**3. Trích xuất đặc trưng và tiền xử lý (Wav2Vec2Processor):**
- `Wav2Vec2Processor.from_pretrained` chỉ load processor/tokenizer, không có thành phần random.
- Khi gọi processor để chuẩn hóa input, không có augmentation hoặc random masking nào xảy ra trong inference.

**4. Duyệt file và lưu kết quả:**
- Bạn dùng `list(input_folder.glob('*.wav'))` để lấy danh sách file.  
  Nếu bạn muốn đảm bảo thứ tự tuyệt đối qua các lần chạy, có thể sort:
  ```python
  wav_files = sorted(list(input_folder.glob('*.wav')))
  ```
  Tuy nhiên, với cùng bộ input, kết quả sẽ không đổi dù thứ tự có thay đổi.

**5. Không có use-case của random seed:**
- Bạn không có bất kỳ lệnh set random seed nào, nhưng thực tế cũng không cần vì không có hàm random nào được sử dụng trong pipeline này cả.

**6. Không sử dụng multi-threading hoặc multiprocessing:**
- Toàn bộ pipeline chạy tuần tự, không chia file cho các thread khác nhau, nên không có trạng thái race condition hoặc random do thread.

---

**Kết luận:**  
> **Pipeline hiện tại của bạn là hoàn toàn DETERMINISTIC với cùng dữ liệu đầu vào, model, code và tham số. Không có bất kỳ nguồn ngẫu nhiên nào có thể làm kết quả khác nhau giữa các lần chạy.**

**Gợi ý kiểm tra lại nếu vẫn phát hiện sai khác:**
- Đảm bảo thư mục input không thay đổi giữa các lần chạy.
- Đảm bảo phiên bản model/processor không update hoặc overwrite bất ngờ.
- Kiểm tra lại xem có can thiệp nào từ bên ngoài (ví dụ lỗi đọc file, file bị ghi đè,...) không.
- Nếu bạn có ý định thêm augmentation hoặc phân tích batch lớn song song trong tương lai, hãy kiểm soát chặt random seed.

---

**Tóm lại:**  
**Code hiện tại của bạn không có random! Kết quả phải giống nhau 100% giữa các lần chạy với cùng input và tham số.**