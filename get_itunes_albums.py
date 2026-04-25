import httpx
res = httpx.get("https://itunes.apple.com/us/rss/topalbums/limit=40/json")
data = res.json()
images = set()
for entry in data['feed']['entry']:
    imgs = entry['im:image']
    images.add(imgs[-1]['label'].replace('170x170', '600x600')) # Make it high-res
import json
with open("album_urls.json", "w") as f:
    json.dump(list(images), f)
print("Saved iTunes images!")
