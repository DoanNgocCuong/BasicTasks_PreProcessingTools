YOUTUBE TRANSCRIPT API - DEPLOYMENT GUIDE
----------------------------------------

1. Set environment variables:
export RAPID_API_KEY="your_rapid_api_key"

2. Deploy Cloud Function:
gcloud functions deploy process_youtube_url \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars RAPID_API_KEY=$RAPID_API_KEY

3. Test API:
curl -X GET \
  'https://YOUR_REGION-YOUR_PROJECT.cloudfunctions.net/process_youtube_url?youtube_url=https://www.youtube.com/watch?v=VIDEO_ID' \
  -H 'X-API-Key: yt2024_k8hj3n5m9p2q4w7r'

Notes:
- API Key required in X-API-Key header
- YouTube URL must be provided as query parameter
- Function will return JSON with video details and transcript