import http.client
import json
import os
from dotenv import load_dotenv

load_dotenv()

def fetch_tiktok_videos(username, api_key, max_videos=5):
    """
    Fetch a list of TikTok videos for a given username.
    """
    try:
        # Kiểm tra API key
        if not api_key:
            print("API key is missing")
            return []

        conn = http.client.HTTPSConnection("tiktok-api23.p.rapidapi.com")
        headers = {
            'x-rapidapi-key': api_key,
            'x-rapidapi-host': "tiktok-api23.p.rapidapi.com"
        }

        # Step 1: Lấy thông tin user
        print(f"\nGetting videos for user: {username}")
        conn.request("GET", f"/api/user/info?uniqueId={username}", headers=headers)
        res = conn.getresponse()
        user_data = json.loads(res.read().decode("utf-8"))
        
        # Lấy secUid từ response
        sec_uid = user_data.get("userInfo", {}).get("user", {}).get("secUid")
        if not sec_uid:
            print("Could not find secUid")
            return []

        # Step 2: Lấy danh sách video
        conn.request("GET", f"/api/user/posts?secUid={sec_uid}&count={max_videos}&cursor=0", headers=headers)
        res = conn.getresponse()
        data = json.loads(res.read().decode("utf-8"))

        # Xử lý danh sách video từ itemList
        videos = []
        for item in data.get("data", {}).get("itemList", []):
            video_info = {
                "id": item.get("id"),
                "description": item.get("desc"),
                "create_time": item.get("createTime"),
                "duration": item.get("video", {}).get("duration"),
                "play_count": item.get("stats", {}).get("playCount"),
                "like_count": item.get("stats", {}).get("diggCount"),
                "comment_count": item.get("stats", {}).get("commentCount"),
                "share_count": item.get("stats", {}).get("shareCount"),
                "download_url": item.get("video", {}).get("downloadAddr"),
                "play_url": item.get("video", {}).get("playAddr"),
                "cover_url": item.get("video", {}).get("cover"),
                "url": f"https://www.tiktok.com/@{username}/video/{item.get('id')}"
            }
            videos.append(video_info)

        return videos

    except Exception as e:
        print(f"Error: {str(e)}")
        return []

if __name__ == "__main__":
    username = "moxierobot"
    api_key = os.getenv("TIKTOK_API_KEY")
    max_videos = 20

    if not api_key:
        print("Error: TIKTOK_API_KEY environment variable not set")
        exit(1)

    videos = fetch_tiktok_videos(username, api_key, max_videos=max_videos)
    
    if not videos:
        print("\nNo videos found")
    else:
        print(f"\nFound {len(videos)} videos:")
        for video in videos:
            print("\n" + "="*50)
            print(f"Video ID: {video['id']}")
            print(f"Description: {video['description']}")
            print(f"Created: {video['create_time']}")
            print(f"Duration: {video['duration']}s")
            print(f"Stats:")
            print(f"- Views: {video['play_count']}")
            print(f"- Likes: {video['like_count']}")
            print(f"- Comments: {video['comment_count']}")
            print(f"- Shares: {video['share_count']}")
            print(f"URL: {video['url']}")
