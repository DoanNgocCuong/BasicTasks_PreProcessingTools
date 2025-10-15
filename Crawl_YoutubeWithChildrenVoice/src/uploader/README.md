# Upload API

This is a self-contained API for uploading classified children voice audio files.

## Components

- `server.py`: FastAPI server that receives file uploads and organizes them in dated folders.
- `client.py`: Client script that reads the manifest, filters files to upload, and uploads them using multithreading.
- `start_server.py`: Convenience script to start the server.
- `start_client.py`: Convenience script to start the client with manifest path.
- `upload_phases.py`: Integration module for the crawler workflow.

## Usage

1. Start the server:

   ```
   python src/uploader/start_server.py
   ```

2. Run the client with the path to manifest.json:
   ```
   python src/uploader/start_client.py output/final_audio/manifest.json
   ```

The client will:

- Read the manifest.json
- Find records where `classified: true`, `children_voice: true`, and `uploaded: false`
- Start an upload session to get a unique folder ID
- Upload the files in parallel using multithreading
- Update the manifest to set `uploaded: true` for successfully uploaded files

## Requirements

The manifest.json should have records with the following fields:

- `classified`: boolean
- `children_voice`: boolean
- `uploaded`: boolean
- `output_path`: string path to the audio file

Files are uploaded to `uploaded_files/{folder_id}/` on the server side.
