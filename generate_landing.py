import asyncio
from spotify_api import spotify_client

async def fetch_albums():
    # Use client_credentials to get token
    token = await spotify_client._get_client_credentials_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Global Top 50 playlist
    res = await spotify_client.client.get("https://api.spotify.com/v1/playlists/37i9dQZEVXbMDoHDwvn2tF/tracks?limit=30", headers=headers)
    
    if res.status_code == 200:
        data = res.json()
        images = []
        for item in data.get("items", []):
            track = item.get("track")
            if track and track.get("album"):
                imgs = track["album"].get("images", [])
                if imgs:
                    images.append(imgs[0]["url"])
        return list(set(images))
    return []

async def main():
    images = await fetch_albums()
    print("Found", len(images), "images")
    import json
    with open("album_urls.json", "w") as f:
        json.dump(images, f)

asyncio.run(main())
