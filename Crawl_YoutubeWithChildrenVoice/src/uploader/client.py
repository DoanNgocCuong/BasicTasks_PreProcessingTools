import json
import os
import requests
import concurrent.futures
import argparse
from typing import List, Dict, Any

SERVER_URL = "http://localhost:8000"

def start_upload_session() -> str:
    response = requests.post(f"{SERVER_URL}/start_upload")
    response.raise_for_status()
    return response.json()["folder_id"]

def upload_file(folder_id: str, file_path: str, filename: str):
    with open(file_path, "rb") as f:
        files = {"file": (filename, f)}
        response = requests.post(f"{SERVER_URL}/upload/{folder_id}", files=files)
        response.raise_for_status()
    return filename

def main(manifest_path: str):
    # Read manifest
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    records = manifest.get("records", [])
    
    # Filter targets: classified: true, children_voice: true, uploaded: false
    targets = []
    for i, record in enumerate(records):
        if (record.get("classified") == True and 
            record.get("children_voice") == True and 
            record.get("uploaded") == False):
            targets.append((i, record))
    
    if not targets:
        print("No files to upload.")
        return
    
    # Start upload session
    folder_id = start_upload_session()
    print(f"Upload folder: {folder_id}")
    
    # Prepare uploads
    uploads = []
    for idx, record in targets:
        output_path = record["output_path"]
        # Assuming output_path is relative to the project root
        full_path = output_path.replace("\\", os.sep)
        filename = os.path.basename(full_path)
        uploads.append((folder_id, full_path, filename, idx))
    
    # Upload with multithreading
    successful_uploads = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(upload_file, fid, path, fname) for fid, path, fname, idx in uploads]
        for future in concurrent.futures.as_completed(futures):
            try:
                filename = future.result()
                print(f"Uploaded {filename}")
                # Find the idx
                for fid, path, fname, idx in uploads:
                    if fname == filename:
                        successful_uploads.append(idx)
                        break
            except Exception as e:
                print(f"Failed to upload: {e}")
    
    # Update manifest
    for idx in successful_uploads:
        records[idx]["uploaded"] = True
    
    # Write back
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"Updated manifest with {len(successful_uploads)} uploaded files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload classified children voice audio files.")
    parser.add_argument("manifest_path", help="Path to the manifest.json file")
    args = parser.parse_args()
    main(args.manifest_path)