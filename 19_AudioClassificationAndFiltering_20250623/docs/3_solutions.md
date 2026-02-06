# Tập trung vào phân loại tuổi là xong 
```bash
# @DoanNgocCuong
"""
# QUan trọng nhất vẫn là model nhận diện trẻ em và người lớn. Code trêển khai cái này trước. Input là 1 folder trong đó có nhêều audio (dạng .wav)
=> Output mong muốn là: Folder output chứa
1. Folder trẻ em 
2. Folder người lớn 
3. File excel gồm tên file và label (trẻ em/người lớn)
4. File results.txt (đánh giá Precision, Recall)

Note: Dùng pathlib đi 
File code để ngang bằng vị trí với folder: input và folder output File code để ngang bằng vị trí với folder: input và folder output

---

Mỗi file audio .wav sẽ được đưa qua model wav2vec2 để dự đoán nhãn child/adult.
Nếu dự đoán là "child" với độ tự tin (confidence) lớn hơn 0.7 thì file sẽ được chép vào folder "child", ngược lại vào "adult".
Tất cả kết quả được ghi vào file Excel.
Nếu có file groundtruth, code sẽ tính Precision/Recall và ghi ra file results.txt.
"""
```