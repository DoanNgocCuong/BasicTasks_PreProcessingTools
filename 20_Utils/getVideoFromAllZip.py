"""
This script finds all .zip files in the same folder and extracts all .mp4 video files from them.
The videos are saved in a folder called 'output' with safe file names.

How to use:
1. Put this script in the folder with your .zip files.
2. Run the script.
3. All .mp4 videos from the .zip files will be in the 'output' folder.
"""
import zipfile
import os
import re

def safe_filename(s):
    """
    Make the file name safe for your computer.
    It removes special characters and changes them to _ (underscore).
    Input: s (string) - the file name
    Output: safe file name (string)
    """
    # Loại bỏ các ký tự không hợp lệ cho tên file
    return re.sub(r'[\\/*?:"<>|]', '_', s)

def extract_mp4_from_zip(zip_path, output_dir):
    """
    Extract all .mp4 video files from a .zip file.
    The videos are saved in the output folder with safe names.
    Input:
        zip_path (string): path to the .zip file
        output_dir (string): folder to save videos
    Output: None (videos are saved to disk)
    """
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for file_info in zf.infolist():
            if not file_info.is_dir() and file_info.filename.lower().endswith('.mp4'):
                # Lấy đường dẫn gốc trong zip, đổi / thành _
                # Loại bỏ dấu / ở đầu (nếu có)
                rel_path = file_info.filename.lstrip('/')
                # Đổi / thành _
                flat_name = safe_filename(rel_path.replace('/', '_'))
                # Gắn thêm tên file zip để tránh trùng nếu cần
                zip_base = os.path.splitext(os.path.basename(zip_path))[0]
                out_name = f"{zip_base}_{flat_name}"
                out_path = os.path.join(output_dir, out_name)
                # Giải nén ra file mới
                with open(out_path, 'wb') as f:
                    f.write(zf.read(file_info.filename))
                print(f"Đã giải nén: {out_path}")

if __name__ == "__main__":
    """
    Main part of the script.
    Finds all .zip files in the folder and extracts .mp4 videos from them.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(current_dir, 'output')
    os.makedirs(output_dir, exist_ok=True)
    for fname in os.listdir(current_dir):
        if fname.lower().endswith('.zip'):
            zip_path = os.path.join(current_dir, fname)
            extract_mp4_from_zip(zip_path, output_dir)
