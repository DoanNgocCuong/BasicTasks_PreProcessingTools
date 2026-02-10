import pandas as pd
import re

# Đường dẫn tới tệp Excel
file_path = r'D:\OneDrive - Hanoi University of Science and Technology\ITE10-DS&AI-HUST\Learn&Task\Product_THECOACH\MiniTest_TheCoach\MiniTask2_Cleaning\(Input)_5000data_Thông tin khách hàng.xlsx'

# Đọc tệp Excel từ sheet đầu tiên
df = pd.read_excel(file_path)

# In ra tên các cột trong DataFrame để kiểm tra
print("Tên các cột trong tệp Excel:", df.columns)

# Các từ khóa cần kiểm tra và làm sạch
keywords = ['tdv', 'tđv', 'Tdv', 'lh', 'knm1', 'knm2', 'knm', 'mc2', 'c2', '(zl)', 'zl', 'kllđ', 'zalo', 'gls', 
            'tdv,', 'tđv,', 'Tdv,', 'lh,', 'knm1,', 'knm2,', 'knm,', 'mc2,', 'c2,', '(zl),', 'zl,', 'kllđ,', 'zalo,']
date_pattern = re.compile(r'\d{1,2}/\d{1,2}')  # Pattern để nhận diện ngày tháng
weekday_keywords = ['thứ 2', 'thứ 3', 'thứ 4', 'thứ 5', 'thứ 6', 'thứ 7', 'chủ nhật', 'ngày mai', 'ngày kia']

# Hàm để kiểm tra nếu chuỗi chứa ngày tháng
def contains_date(text):
    return bool(date_pattern.search(text))

# Hàm để tách các dòng chứa ngày tháng ra khỏi phần còn lại
def split_date_lines(text):
    lines = text.split('\n')
    date_lines = [line for line in lines if contains_date(line)]
    non_date_lines = [line for line in lines if not contains_date(line)]
    return date_lines, non_date_lines

# Hàm để sắp xếp các dòng theo thứ tự thời gian
def sort_date_lines(date_lines):
    return sorted(date_lines, key=lambda line: date_pattern.search(line).group())

# Hàm để làm sạch văn bản
def clean_text(text):
    if isinstance(text, str):
        # Tách các dòng chứa ngày tháng
        date_lines, non_date_lines = split_date_lines(text)
        # Sắp xếp các dòng chứa ngày tháng theo thứ tự thời gian
        sorted_date_lines = sort_date_lines(date_lines)
        # Kết hợp lại với phần dữ liệu chính
        combined_text = '\n'.join(sorted_date_lines + non_date_lines)
        
        # Lặp lại cho đến khi không còn từ khóa nào trong văn bản
        while any(keyword in combined_text for keyword in keywords) or date_pattern.search(combined_text) or any(kw in combined_text for kw in weekday_keywords):
            # Kiểm tra và làm sạch các từ khóa và dấu phẩy kèm theo
            for keyword in keywords:
                if keyword in combined_text:
                    # Loại bỏ từ khóa và dấu phẩy kèm theo nếu có, ngoại trừ "giao tiếp lh"
                    if keyword == 'lh' and 'giao tiếp lh' in combined_text:
                        continue
                    combined_text = re.sub(rf'[\s,]*{keyword}[\s,]*', ' ', combined_text).strip()
            # Kiểm tra và làm sạch các ngày tháng
            match_date = date_pattern.search(combined_text)
            if match_date:
                combined_text = combined_text.split(match_date.group(), 1)[-1].strip()

            # Kiểm tra và làm sạch các ngày trong tuần và từ khóa thời gian
            for keyword in weekday_keywords:
                if keyword in combined_text:
                    combined_text = combined_text.split(keyword, 1)[-1].strip()
        return combined_text
    return text

# Kiểm tra và làm sạch dữ liệu nếu cột 'Thông tin' tồn tại
if 'Thông tin' in df.columns:
    df_with_keywords = pd.DataFrame(columns=df.columns)
    df_without_keywords = pd.DataFrame(columns=df.columns)
    df_not_string = pd.DataFrame(columns=df.columns)
    
    count_with_keywords = 0
    count_without_keywords = 0
    count_not_string = 0
    
    for index, row in df.iterrows():
        if isinstance(row['Thông tin'], str):
            if any(keyword in row['Thông tin'] for keyword in keywords) or date_pattern.search(row['Thông tin']) or any(kw in row['Thông tin'] for kw in weekday_keywords):
                cleaned_text = clean_text(row['Thông tin'])
                row['D'] = cleaned_text
                df_with_keywords = pd.concat([df_with_keywords, pd.DataFrame([row])])
                count_with_keywords += 1
                if count_with_keywords % 25 == 0:
                    print(f"CheckPoint: {count_with_keywords} dòng có từ khóa, ngày tháng, giờ hoặc ngày trong tuần đã được xử lý thành công")
            else:
                row['D'] = row['Thông tin']
                df_without_keywords = pd.concat([df_without_keywords, pd.DataFrame([row])])
                count_without_keywords += 1
                if count_without_keywords % 25 == 0:
                    print(f"{count_without_keywords} dòng không có từ khóa, ngày tháng, giờ hoặc ngày trong tuần đã được xử lý thành công")
        else:
            df_not_string = pd.concat([df_not_string, pd.DataFrame([row])])
            count_not_string += 1
            if count_not_string % 25 == 0:
                print(f"{count_not_string} dòng không phải là chuỗi đã được xử lý thành công")
    
    # Tính tổng số dòng
    total_rows = count_with_keywords + count_without_keywords + count_not_string
    
    # Tính phần trăm các dòng có và không có từ khóa, ngày tháng, giờ hoặc ngày trong tuần
    percent_with_keywords = (count_with_keywords / total_rows) * 100
    percent_without_keywords = (count_without_keywords / total_rows) * 100
    percent_not_string = (count_not_string / total_rows) * 100
    
    # In phần trăm ra màn hình
    print("------------------------")
    print(f"Xử Lý Hoàn Tất. Tổng số dòng: {total_rows}")
    print(f"Phần trăm dòng có từ khóa, ngày tháng, giờ hoặc ngày trong tuần: {percent_with_keywords:.2f}%")
    print(f"Phần trăm dòng không có từ khóa, ngày tháng, giờ hoặc ngày trong tuần: {percent_without_keywords:.2f}%")
    print(f"Phần trăm dòng không phải là chuỗi: {percent_not_string:.2f}%")
else:
    print("Cột 'Thông tin' không tồn tại trong tệp Excel. Kiểm tra lại tên các cột.")

# Lưu DataFrame mới vào các tệp Excel riêng biệt
if 'Thông tin' in df.columns:
    output_file_path_with_keywords = 'cleaned_data_with_keywords.xlsx'
    output_file_path_without_keywords = 'cleaned_data_without_keywords.xlsx'
    output_file_path_not_string = 'cleaned_data_not_string.xlsx'
    
    df_with_keywords.to_excel(output_file_path_with_keywords, index=False)
    df_without_keywords.to_excel(output_file_path_without_keywords, index=False)
    df_not_string.to_excel(output_file_path_not_string, index=False)
    
    print(f"Dữ liệu đã được làm sạch và lưu vào {output_file_path_with_keywords}, {output_file_path_without_keywords} và {output_file_path_not_string}")
else:
    print("Không thể lưu tệp mới vì cột 'Thông tin' không tồn tại.")

# Đọc các file đã lưu và kết hợp chúng
file1 = 'cleaned_data_with_keywords.xlsx'
file2 = 'cleaned_data_without_keywords.xlsx'
file3 = 'cleaned_data_not_string.xlsx'

# Đọc các sheet từ từng file (giả sử mỗi file chỉ có 1 sheet)
df1 = pd.read_excel(file1)
df2 = pd.read_excel(file2)
df3 = pd.read_excel(file3)

# Ghép các dataframe lại với nhau
combined_df = pd.concat([df1, df2, df3], ignore_index=True)

# Lưu dataframe đã ghép vào file Excel mới
combined_df.to_excel('combined_file.xlsx', index=False)

print("Files have been combined successfully.")
