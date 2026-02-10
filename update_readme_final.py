import os

base_path = r'D:\GIT\BasicTasks_PreProcessingTools'

# Get all folders
all_items = os.listdir(base_path)
folders = [d for d in all_items if os.path.isdir(os.path.join(base_path, d)) and not d.startswith('.')]

# Filter and sort folders that have the NN_ prefix
indexed_folders = []
for f in folders:
    if f[0:2].isdigit() and f[2:3] == '_':
        indexed_folders.append(f)

indexed_folders.sort()

# Create README content
lines = [
    "# BasicTasks_PreProcessingTools",
    "",
    "## Project Map (Chronological & Priority)",
    "",
    "| # | Folder Name | Description |",
    "|---|-------------|-------------|",
]

for f in indexed_folders:
    num = f[0:2]
    name = f[3:]
    lines.append(f"| {num} | [{f}](./{f}) | |")

readme_content = "\n".join(lines)

with open(os.path.join(base_path, 'README.md'), 'w', encoding='utf-8') as readme_file:
    readme_file.write(readme_content)

print("README.md updated successfully.")
