1. Chia thư mục ban đầu thành 2 folder: audio_long và audio_short
2. Chạy code với thư mục 'audio_long' qua model: ...
Điều kiện: 
- If child_prob > 0.4 => return child 
- If child_prob < 0.4 and age <=25 => return child 
- else return adult 

3. Chạy test trên bộ: 
- 100 audio random. 
Đo lường trên 2 metrics: 
+, Precision: Số dự đoán đúng / Tổng số dự đoán 
+, Recall: Số dự đoán đúng / Tổng số đúng thực tế. 

=> Precision_child = 35/36 > 95%
=> Recall_child = 35/55 ~ 70%


---

# How Run: 

```bash
# copy 100 segments to test_segments
mkdir -p input
ls segments | shuf | head -100 | xargs -I{} cp segments/{} input/

# run server
cd input
nohup python3 -m http.server 30002 > output.log 2>&1 &


# Run 
python AgeDetection.py
```