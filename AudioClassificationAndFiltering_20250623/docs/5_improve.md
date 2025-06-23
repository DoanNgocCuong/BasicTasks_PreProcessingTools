```bash
Phát hiện và lọc audio trẻ em chất lượng tốt. Loại bỏ audio người lớn, nhiễu, và audio có background music.	
	
Định nghĩa chỉ số	
	
Precision_child = TP_child / (TP_child + FP_child) = TP_child / tổng các dự đoán child	
• TP_child: số audio trẻ em được giữ lại đúng	
• FP_child: số audio người lớn vô tình được giữ lại (phải = 0)	
	
Recall_child = TP_child / (TP_child + FN_child) = TP_child/tổng child thực tế	
• FN_child: số audio trẻ em bị loại hụt (chấp nhận)	
	
Mục tiêu: Precision_child = 1.0 (0% người lớn lọt qua) dù Recall_child có thể < 1.0.	
```

---

# Với ngưỡng:
📊 Model: audeering/wav2vec2-large-robust-24-ft-age-gender
🎯 Ngưỡng Child Probability: 0.4
🎯 Ngưỡng Age: 0.25 (25.0 tuổi)


thì kết quả cho thấy: 
- Precision_child = 36 đúng / tổng 37 dự đoán 