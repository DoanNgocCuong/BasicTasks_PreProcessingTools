import json
import os
import requests
import concurrent.futures
import argparse
from typing import List, Dict, Any, Optional

from ..constants import DEFAULT_MAX_CONCURRENT_UPLOADS

SERVER_URL = "http://103.253.20.30:8081/"

# Authentication credentials
USERNAME = "admin"
PASSWORD = "secret"

def start_upload_session() -> str:
    response = requests.post(f"{SERVER_URL}/start_upload", auth=(USERNAME, PASSWORD))
    response.raise_for_status()
    return response.json()["folder_id"]

def upload_file(folder_id: str, file_path: str, filename: str, language: str = "unknown"):
    with open(file_path, "rb") as f:
        files = {"file": (filename, f)}
        data = {"language": language}
        response = requests.post(f"{SERVER_URL}/upload/{folder_id}", files=files, data=data, auth=(USERNAME, PASSWORD))
        response.raise_for_status()
    return filename

def main(manifest_path: str, folder_id: Optional[str] = None) -> tuple[Optional[str], int]:
    # Read manifest
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    
    records = manifest.get("records", [])
    
    # Filter targets: classified: true, containing_children_voice: true, uploaded: false, file_available: true
    targets = []
    for i, record in enumerate(records):
        if (record.get("classified") == True and 
            record.get("containing_children_voice") == True and 
            record.get("uploaded", False) == False and
            record.get("file_available", False) == True):
            targets.append((i, record))
    
    if not targets:
        print("No files to upload.")
        return folder_id, 0  # Return the folder_id even if no uploads
    
    # Start upload session or use provided folder_id
    if folder_id is None:
        folder_id = start_upload_session()
        print(f"Started new upload folder: {folder_id}")
    else:
        print(f"Using existing upload folder: {folder_id}")
    
    # Prepare uploads
    uploads = []
    for idx, record in targets:
        output_path = record.get("output_path")
        if not output_path:
            print(f"Skipping upload for record {idx}: missing output_path")
            continue
        # Assuming output_path is relative to the project root
        full_path = output_path.replace("\\", os.sep)
        filename = os.path.basename(full_path)
        language = record.get("language_folder", "unknown")
        uploads.append((folder_id, full_path, filename, language, idx))
    
    # Upload with multithreading
    successful_uploads = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=DEFAULT_MAX_CONCURRENT_UPLOADS) as executor:
        futures = [executor.submit(upload_file, fid, path, fname, lang) for fid, path, fname, lang, idx in uploads]
        for future in concurrent.futures.as_completed(futures):
            try:
                filename = future.result()
                # Find the corresponding upload info to get language and folder_id
                server_path = None
                upload_idx = None
                for fid, path, fname, lang, idx in uploads:
                    if fname == filename:
                        server_path = f"uploaded_files/{fid}/{lang}/{filename}"
                        upload_idx = idx
                        break
                print(f"✅ Uploaded to: {server_path}")
                if upload_idx is not None:
                    successful_uploads.append(upload_idx)
            except Exception as e:
                print(f"Failed to upload: {e}")
    
    # Update manifest
    targeted_indices = [idx for idx, _ in targets]
    for idx in targeted_indices:
        records[idx]["uploaded"] = False  # Mark as failed initially
    for idx in successful_uploads:
        records[idx]["uploaded"] = True   # Override to true for successful uploads
    
    # Write back
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    print(f"Updated manifest with {len(successful_uploads)} uploaded files.")
    return folder_id, len(successful_uploads)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload classified children voice audio files.")
    parser.add_argument("manifest_path", help="Path to the manifest.json file")
    parser.add_argument("--folder-id", help="Optional folder ID to reuse for uploads")
    args = parser.parse_args()
    main(args.manifest_path, args.folder_id)