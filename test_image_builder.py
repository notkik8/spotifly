import asyncio
from image_builder import build_nowplaying_image

async def run():
    users_data = [{
        'spotify_username': 'kik8', 
        'track_name': 'Привет', 
        'artists': 'Some Artist', 
        'image_url': 'https://i.scdn.co/image/ab67616d0000b273b55d26c59d1dc9a1fec0ae16'
    }]
    res = await build_nowplaying_image(users_data)
    with open("test_output.jpg", "wb") as f:
        f.write(res)
    print("Done! Image size:", len(res))

asyncio.run(run())
