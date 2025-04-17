Day: 15/9/2024
Task có 2 bước chính
1. Từ Input đã qua xử lý/ Input đã được chuẩn hoá => Các cột (Prompting) 
2. Từ các cột => Vẽ biểu đồ trên excel 

---
Future Work: 
- Nếu task lặp lại nhiều thì
+, step 1: em sẽ build thành UI. 
+, step 2: có thể là em sẽ đóng gói thành video (làm trên excel). 
1. Từ Input đã qua xử lý/ Input đã được chuẩn hoá => Các cột 
Link data: 
https://docs.google.com/spreadsheets/d/17t7EUyqqA5tZTc2NIe-1iZRVGHvgQZiC48zFPChTDig/edit?gid=2141830678#gid=2141830678
1. Xác định cơ bản các cột cần lấy: 

1. Phân loại nhóm ngành nghề: Công nghệ thông tin (IT), Kinh doanh/Bán hàng, Marketing/Truyền thông, Tài chính/Ngân hàng, Sản xuất và Chế tạo, Bất động sản, Giáo dục/Đào tạo, Hành chính/Nhân sự, Y tế và Chăm sóc sức khỏe, Logistics và Chuỗi cung ứng.

2. Chức Vụ (Nhân viên dưới 3 năm, chuyên viên trên 3 năm, quản lý trưởng phòng, giám đốc, khác)

3. Mục đích học (Học để giải quyết công việc hiện tại, học cho tương lai)

Trong quá trình làm có thể bổ sung thêm các nhóm ngành nghề khác, hoặc thêm các chức vụ Position khác để phân loại được hiệu quả hơn. 

2. Tạo Prompt: 
- Tool tinh chỉnh Prompt: https://prompthippo.net/profile  - Hiện tool đang bị lỗi
- (Hoặc vào chính trang Playground của GPT để tinh chỉnh prompt: https://platform.openai.com/playground/chat?models=gpt-4o )
Role: Data extraction and classification expert.  
Task: Extract and classify USER INPUT into:

1. Occupational Group: Students; IT; Business/Sales; Marketing/Communication; Finance/Banking; Production/Manufacturing; Real estate; Education/Training; Admin/HR; Health/Healthcare; Logistics/Supply Chain; Other.

2. Position: Employee (<3 years); Specialist (>3 years); Manager/Head (>5 years); Director; Other.  
   - If Occupational Group is ""Student"" then Position must be ""Other"".

3. Learning Purpose: Extract learning purpose based on these factors:
   - Is English used regularly in the current job? (yes/no)
   - Does English proficiency affect the current job? (yes/no)
   - Is there a specific goal for learning English? (yes/no)

4. Learning Purpose Group: 
   - If any of the responses to the learning purpose factors is ""no,"" classify as ""Study for the future.""
   - Otherwise, classify as ""Study for the current.""

Response: JSON format with 3 keys: Occupational Group, Position, and Learning Purpose Group

3. Chạy hàng loạt: https://colab.research.google.com/drive/1474bpychjeUPZytsdLtjRi0spBpp6dWP#scrollTo=zmwSfcQtzVBl
https://tableconvert.com/json-to-excel
-> Future: Đóng gói thành UI, tinh chỉnh Prompt và xem được kết quả trực tiếp trên UI
Từ các cột => Vẽ biểu đồ trên excel 
1. Nếu task lặp lại nhiều => Làm video hướng dẫn. 


### 4. **COUNTIF** - Đếm với điều kiện cụ thể
   - **Công thức**: `=COUNTIF(range, criteria)`
   - **Mục đích**: Đếm các ô thỏa mãn điều kiện nhất định.
   - **Ví dụ**: `=COUNTIF(F2:F4014, "Students")`

### 5. **COUNTIFS** - Đếm với nhiều điều kiện
   - **Công thức**: `=COUNTIFS(range1, criteria1, range2, criteria2, ...)`
  - Ví dụ: `=COUNTIFS(F2:F4014, "Students", G2:G4014, "Intern (0-1 year)")`

### 6. **DCOUNT** - Đếm số ô chứa giá trị số trong cơ sở dữ liệu
   - **Công thức**: `=DCOUNT(database, field, criteria)`
   - **Mục đích**: Đếm các ô có chứa giá trị số trong cơ sở dữ liệu thỏa mãn các tiêu chí cho trước.
   - **Ví dụ**: `=DCOUNT(A1:C10, "Age", E1:F2)` sẽ đếm số lượng giá trị số trong cột "Age" của bảng dữ liệu từ A1:C10 theo tiêu chí trong E1:F2.

-----------------------------------------
Copy nhanh công thức: 
Di chuột tới góc dưới bên phải của ô đã chọn. Khi con trỏ chuột biến thành hình dấu + (dấu cộng nhỏ), bạn có thể nhấn giữ chuột trái và kéo xuống các ô bên dưới để sao chép công thức cho các hàng còn lại.
---------------------------------------
Chèn biểu đồ dạng Heat Map
Để tạo bảng màu với các giá trị phần trăm, bạn có thể sử dụng Conditional Formatting để định dạng bảng dưới dạng Heat Map:

Chọn vùng dữ liệu từ bảng (không bao gồm tiêu đề).
Vào tab Home (Trang chủ), chọn Conditional Formatting (Định dạng có điều kiện).
Chọn Color Scales (Thang màu) để áp dụng dải màu tương ứng cho các giá trị phần trăm.
Bạn có thể chọn dải màu có sẵn, hoặc chọn More Rules để tùy chỉnh màu sắc theo ý muốn (ví dụ: màu cam cho giá trị cao, xanh lá cho giá trị trung bình, xám cho giá trị nhỏ hoặc N/A).

 Tùy chỉnh hiển thị phần trăm
Sau khi áp dụng định dạng màu, bạn cần chắc chắn rằng các ô đã được định dạng dưới dạng phần trăm:
Nhấn chuột phải vào các ô dữ liệu > chọn Format Cells > chọn Percentage để hiển thị phần trăm.
Điều chỉnh số thập phân nếu cần (ví dụ: hiển thị 2 số thập phân).
