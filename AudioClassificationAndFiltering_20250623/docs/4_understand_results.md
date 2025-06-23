**Giải thích con số 0.4 (child_threshold = 0.4):**

Con số **0.4** là **ngưỡng xác suất (probability threshold)** để phân loại một audio là giọng trẻ em. Cụ thể:

**1. Ý nghĩa của child_threshold = 0.4:**
- Model trả về 3 xác suất cho mỗi audio: `[female_prob, male_prob, child_prob]`
- Nếu `child_prob > 0.4` (tức xác suất là trẻ em > 40%) → phân loại là **"child"**
- Nếu `child_prob ≤ 0.4` → xem xét thêm điều kiện tuổi hoặc phân loại là **"adult"**

**2. Tại sao chọn 0.4 thay vì 0.5 hoặc 0.7?**
- **0.4 (40%)** là ngưỡng **tương đối thấp**, giúp "bắt" được nhiều trường hợp trẻ em hơn
- Điều này phù hợp khi bạn muốn **ưu tiên Recall** (không bỏ sót trẻ em) hơn là Precision
- Nếu đặt ngưỡng cao (0.7), nhiều audio trẻ em có thể bị phân loại nhầm thành người lớn

**3. Logic phân loại trong code:**
```python
def classify_age_group(self, age_normalized, gender_probs):
    child_prob = gender_probs[2]  # Xác suất là trẻ em
    
    # Điều kiện 1: Nếu xác suất trẻ em > 0.4
    if child_prob > self.child_threshold:  # 0.4
        return "child", child_prob
    
    # Điều kiện 2: Hoặc nếu tuổi < 25 tuổi (age_threshold = 0.25)
    if age_normalized < self.age_threshold:  # 0.25
        return "child", age_normalized
    
    # Ngược lại là người lớn
    return "adult", 1 - child_prob
```

**4. Ví dụ cụ thể:**
- Audio A: `child_prob = 0.45` → Vì 0.45 > 0.4 → Phân loại: **CHILD**
- Audio B: `child_prob = 0.35, age = 20 tuổi` → Vì 0.35 < 0.4 nhưng 20 < 25 tuổi → Phân loại: **CHILD**
- Audio C: `child_prob = 0.30, age = 30 tuổi` → Cả hai điều kiện đều không thỏa → Phân loại: **ADULT**

**5. Điều chỉnh ngưỡng:**
- **Giảm xuống 0.3**: Bắt được nhiều trẻ em hơn, nhưng có thể nhầm lẫn người lớn
- **Tăng lên 0.6**: Chính xác hơn khi phân loại trẻ em, nhưng có thể bỏ sót nhiều trường hợp
- **Giữ 0.4**: Cân bằng tốt giữa việc phát hiện trẻ em và tránh nhầm lẫn

**Tóm lại:** Con số 0.4 là ngưỡng xác suất "vừa phải" để phân loại trẻ em, không quá cao (bỏ sót nhiều) cũng không quá thấp (nhầm lẫn nhiều).