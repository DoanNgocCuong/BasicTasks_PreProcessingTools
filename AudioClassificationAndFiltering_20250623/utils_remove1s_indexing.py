"""
# @DoanNgocCuong

Vào trong thư mục: input (thư mục này đang chứa các video .wav)
Rename tên file theo thứ tự 1_<filename>.wav, 2_<filename>.wav, ...
"""

import os
import shutil
import librosa

def filter_and_rename(input_dir="input"):
    recycle_dir = os.path.join(input_dir, "recycle")
    os.makedirs(recycle_dir, exist_ok=True)

    files = [f for f in os.listdir(input_dir) if f.endswith('.wav')]
    files.sort()
    valid_files = []
    for f in files:
        path = os.path.join(input_dir, f)
        try:
            duration = librosa.get_duration(filename=path)
            if duration <= 2.0:
                shutil.move(path, os.path.join(recycle_dir, f))
                print(f"Moved {f} to recycle (duration: {duration:.2f}s)")
            else:
                valid_files.append(f)
        except Exception as e:
            print(f"Error with {f}: {e}")

    for idx, filename in enumerate(valid_files, 1):
        src = os.path.join(input_dir, filename)
        dst = os.path.join(input_dir, f"{idx}_{filename}")
        os.rename(src, dst)
        print(f"Renamed {filename} -> {idx}_{filename}")

if __name__ == "__main__":
    filter_and_rename()