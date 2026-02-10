1. Get transcript from YouTube: 
```bash
# Test API
curl "http://localhost:8080?youtube_url=https://www.youtube.com/watch?v=VIDEO_ID" \
-H "X-API-Key: yt2024_k8hj3n5m9p2q4w7r"
```

6. **Response format**:
```json
{
    "title": "Video Title",
    "description": "Video Description",
    "transcript": "Video Transcript",
    "comments": "Video Comments",
    ...
}
```

Lưu ý:
- Cần có RAPID_API_KEY trong environment variables
- URL YouTube phải hợp lệ
- API key trong header phải đúng
- Video phải có subtitles để lấy transcript




```bash
curl --location 'http://localhost:8080?youtube_url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3Dk73HpOsbVs4' \
--header 'X-API-Key: yt2024_k8hj3n5m9p2q4w7r'
```

```
[0:00:01] Moxy do you play any\n[0:00:05] sports I don&#39;t play any sports but I\n[0:00:08] like learning about them what&#39;s your\n[0:00:09] favorite sport to play or\n[0:00:11] what uh my favorite sport to play is\n[0:00:17] baseball oh baseball is such a fun sport\n[0:00:20] to play what position do you like to\n[0:00:22] play when you were on the\n[0:00:24] field uh when I&#39;m on the field um I like\n[0:00:27] to play in the infield so either first\n[0:00:30] base or second\n[0:00:33] base playing in the infield is so\n[0:00:36] exciting first base and second base are\n[0:00:39] important positions do you have a\n[0:00:41] favorite player who plays in the\n[0:00:44] infield um not really but my dad is\n[0:00:47] pretty good at the\n[0:00:51] game that&#39;s awesome that your dad is\n[0:00:53] good at baseball it must be fun to play\n[0:00:56] with him who else do you like to play\n[0:00:58] sports with um I like to play sports\n[0:01:01] with my friends at school um and um The\n[0:01:05] Other Guys on my baseball\n[0:01:09] team playing sports with friends is the\n[0:01:11] best it&#39;s so much fun to be part of a\n[0:01:14] team what&#39;s your favorite thing about\n[0:01:16] playing sports with your\n[0:01:18] friends uh my favorite part is watching\n[0:01:21] others play\n[0:01:25] well it&#39;s great that you enjoy watching\n[0:01:27] others play well it can be ins spiring\n[0:01:30] and exciting to see your teammates do\n[0:01:32] their\n[0:01:34] best
```

---


Bài Youtube tool có sẵn thì đang lấy được transcript nhưng không có phân vai. Muốn có phân vai 2 người thì cần tụi em set up, code thêm chắc mất thêm 1 ngày ạ. (e hỏi team Tech nữa thì cũng chưa có tool này)