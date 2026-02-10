import os
import re

base_path = r'D:\GIT\BasicTasks_PreProcessingTools'

# Folders to prioritize
priority_folders = {
    '1_Speech2Text': '01_Speech2Text',
    '2_Task3_ImageGeneration': '02_Task3_ImageGeneration',
    '3_Task8_HR-MindPal_Tool': '03_Task8_HR-MindPal_Tool',
    '4_UI_Text2Speech': '04_UI_Text2Speech'
}

# 1. Get all folders
all_items = os.listdir(base_path)
folders = [d for d in all_items if os.path.isdir(os.path.join(base_path, d)) and not d.startswith('.')]

# 2. Identify folders that start with a number prefix (e.g., 01_ or 1_)
shifts = []
for f in folders:
    if f in priority_folders:
        continue
    
    match = re.match(r'^(\d+)_(.*)$', f)
    if match:
        num = int(match.group(1))
        rest = match.group(2)
        new_num = num + 4
        new_name = f"{new_num:02d}_{rest}"
        shifts.append((f, new_name, num))

# 3. Sort shifts in descending order of current number to avoid collisions
shifts.sort(key=lambda x: x[2], reverse=True)

print("Starting Shift Renaming (+4)...")
for old, new, _ in shifts:
    old_full = os.path.join(base_path, old)
    new_full = os.path.join(base_path, new)
    print(f"Renaming: {old} -> {new}")
    os.rename(old_full, new_full)

print("\nStarting Priority Renaming...")
for old, new in priority_folders.items():
    old_full = os.path.join(base_path, old)
    new_full = os.path.join(base_path, new)
    if os.path.exists(old_full):
        print(f"Renaming: {old} -> {new}")
        os.rename(old_full, new_full)
    else:
        print(f"Warning: Priority folder {old} not found.")

print("\nAll folders renamed successfully.")
