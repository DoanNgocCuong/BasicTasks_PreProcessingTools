from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
from datetime import datetime
import random
import string

app = FastAPI(title="Upload API")

UPLOAD_BASE_DIR = "uploaded_files"

@app.post("/start_upload")
async def start_upload():
    # Create a new folder with date_new_id
    date_str = datetime.now().strftime("%Y-%m-%d")
    random_id = ''.join(random.choices(string.digits, k=5))
    folder_name = f"{date_str}_new_{random_id}"
    folder_path = os.path.join(UPLOAD_BASE_DIR, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    return {"folder_id": folder_name}

@app.post("/upload/{folder_id}")
async def upload_file(folder_id: str, file: UploadFile = File(...)):
    folder_path = os.path.join(UPLOAD_BASE_DIR, folder_id)
    if not os.path.exists(folder_path):
        raise HTTPException(status_code=404, detail="Folder not found")
    
    if file.filename is None:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    file_path = os.path.join(folder_path, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"message": f"File {file.filename} uploaded successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)