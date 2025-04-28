# Tôi có 2 cột: ID Chunking và Chunking như trong file 3. 
# Tôi muốn merge 2 cột này lại với nhau, sao cho mỗi ID Chunking chỉ còn 1 Chunking tương ứng. 
# Ví dụ: 
# ID Chunking | Chunking |
# 1           | paragraph1        |
# 2           | paragraph2        |
# 3           | paragraph3        |
# 4           | paragraph 4        |
# 5           | paragraph5        |
# 6           | paragraph6        |

# Kết quả mong muốn:
# ID Chunking | Chunking |
# 1           | paragraph1        |
# 2           | paragraph2        |
# 3           | paragraph3        |
# 4           | paragraph4        |
# 5           | paragraph5        |
# 6           | paragraph6        |
# 1 cách random các hàng: với tham số: 2 hàng bất kỳ, 3 hàng bất kỳ, 4 hàng bất kỳ, 5 hàng bất kỳ, 6 hàng bất kỳ
# 1, 3        | paragraph1, paragraph3        |
# 2, 4        | paragraph2, paragraph4        |
# 5, 1        | paragraph5, paragraph1        | 
# 2, 6        | paragraph2, paragraph6        |
# 3, 4        | paragraph3, paragraph4        |
# ...
# 1, 2, 3, 4  | paragraph1, paragraph2, paragraph3, paragraph4        |
# 5, 6        | paragraph5, paragraph6        | 
# 1, 2, 3, 4, 5, 6 | paragraph1, paragraph2, paragraph3, paragraph4, paragraph5, paragraph6        |

# def merge_chunks(input_file, sheet_name, num_rows_merger, created_num_rows):
- for i in range(created_num_rows): Mỗi lần chọn ngẫu nhiên num_rows_merger từ các hàng data ban đầu để gộp vào 
- Trả ra 1 file mới

Chọn ngẫu nhiên, tuy nhiên:
- ID Chunking được short từ bé đến lớp 
- (kéo theo Chunking cũng sắp xếp như thế)


# Merge Chunks Script

## Description
This script reads an Excel file, randomly selects rows, merges specific columns, and saves the merged data to a new Excel file.

## Dependencies
- pandas
- random

## Usage
1. Ensure you have the required dependencies installed:
    ```bash
    pip install pandas
    ```

2. Update the `file_path` and `sheet_name` variables to point to your Excel file and the specific sheet you want to process.

3. Run the script:
    ```bash
    python random_merge_chunk.py
    ```

## Code