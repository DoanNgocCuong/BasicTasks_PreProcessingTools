nohup python3 youtube_video_crawler.py > crawler_output.log 2>&1 &

# Chạy ở cổng tùy chỉnh (ví dụ: 8080)
nohup python3 -m http.server 30000 > webserver.log 2>&1 &

# Chạy ở cổng tùy chỉnh (ví dụ: 8080)
nohup python3 -m http.server 30001 > webserver.txt 2>&1 &

