# How to Run YouTube Channel Videos API

## Prerequisites
1. Python 3.7 or higher
2. RapidAPI Key
3. Google Cloud Functions environment (for deployment)

## Local Setup

### 0. Create and Activate a Virtual Environment

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment

# Windows
.\venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 1. Install Required Packages
```bash
pip install functions-framework
pip install flask
pip install requests
```

### 2. Set Environment Variable
```bash
# Windows
set RAPID_API_KEY=your_api_key_here

# Linux/Mac
export RAPID_API_KEY=your_api_key_here
```

### 3. Run Locally
```bash
python -m functions_framework --target get_youtube_channel_videos --port 8080
```

## Testing

### 1. Using cURL

```bash
# Test with MrBeast's channel
curl -X GET "http://localhost:8080?url=https://www.youtube.com/@MrBeast"

# Test with PewDiePie's channel
curl -X GET "http://localhost:8080?url=https://www.youtube.com/user/PewDiePie"

# Test with standard channel ID
curl -X GET "http://localhost:8080?url=https://www.youtube.com/channel/UC-lHJZR3Gqxm24_Vd_AJ5Yw"
```

### 2. Using Browser
Open your browser and visit:
```
http://localhost:8080?url=https://www.youtube.com/@MrBeast
```

## Expected Output
```
https://www.youtube.com/watch?v=video1
https://www.youtube.com/watch?v=video2
https://www.youtube.com/watch?v=video3
...
```

## Error Codes
- 200: Success
- 400: Invalid input (missing or invalid URL)
- 404: No videos found
- 500: Server error

## Deployment to Google Cloud Functions

1. Create `requirements.txt`:
```
functions-framework==3.*
flask==2.*
requests==2.*
```

2. Deploy using gcloud:
```bash
gcloud functions deploy get_youtube_channel_videos \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars RAPID_API_KEY=your_api_key_here
```

3. Test deployed function:
```bash
curl -X GET "https://your-function-url?url=https://www.youtube.com/@MrBeast"
```

## Common Issues

1. **Missing API Key**
```
Error: RAPID_API_KEY environment variable not set
```
Solution: Set the RAPID_API_KEY environment variable

2. **Invalid Channel URL**
```
Error: Invalid channel URL or could not extract channel ID
```
Solution: Check if the URL is correct and accessible

3. **No Videos Found**
```
Error: No videos found in channel
```
Solution: Verify the channel exists and has public videos

## Rate Limits
- Check your RapidAPI subscription for specific limits
- Default tier typically allows 100 requests per day

## Support
For issues or questions, please create an issue in the repository.
