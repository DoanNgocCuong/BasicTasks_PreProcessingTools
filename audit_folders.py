import os
import subprocess

def get_git_creation_date(directory_path, folder_name):
    try:
        result = subprocess.run(
            ['git', 'log', '--reverse', '--format=%aI', '--', folder_name],
            cwd=directory_path,
            capture_output=True,
            text=True,
            check=True
        )
        dates = result.stdout.strip().split('\n')
        if dates and dates[0]:
            return dates[0]
    except:
        pass
    return "Unknown"

def audit_folders(base_path):
    subdirs = [d for d in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, d))]
    audit = []
    for d in subdirs:
        creation = get_git_creation_date(base_path, d)
        audit.append({'name': d, 'creation': creation})
    
    # Sort by creation date (if known)
    audit.sort(key=lambda x: x['creation'])
    
    for item in audit:
        print(f"{item['creation']} | {item['name']}")

if __name__ == "__main__":
    audit_folders(r'D:\GIT\BasicTasks_PreProcessingTools')
