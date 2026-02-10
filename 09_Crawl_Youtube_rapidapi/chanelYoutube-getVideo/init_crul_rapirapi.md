
```python
import http.client

conn = http.client.HTTPSConnection("youtube-media-downloader.p.rapidapi.com")

headers = {
    'x-rapidapi-key': "634ee30be2mshf179e8ef90e0c34p17c30ejsn3886f01275d3",
    'x-rapidapi-host': "youtube-media-downloader.p.rapidapi.com"
}

conn.request("GET", "/v2/channel/videos?channelId=UCeY0bbntWzzVIaj2z3QigXg&type=videos&sortBy=newest", headers=headers)

res = conn.getresponse()
data = res.read()

print(data.decode("utf-8"))
```