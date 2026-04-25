import asyncio
import io
import os
import math
import logging
import urllib.request
from dotenv import load_dotenv
from typing import List, Dict, Any
import httpx
from PIL import Image, ImageDraw, ImageFont


load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

font_regular_name = os.getenv("FONT_REGULAR", "Jumper.ttf")
font_bold_name = os.getenv("FONT_BOLD", "JumperB.ttf")
FONT_REGULAR_PATH = os.path.join(BASE_DIR, font_regular_name)
FONT_BOLD_PATH = os.path.join(BASE_DIR, font_bold_name)


logger = logging.getLogger(__name__)





async def fetch_image(client: httpx.AsyncClient, url: str) -> bytes | None:
    if not url:
        return None
    try:
        response = await client.get(url)
        response.raise_for_status()
        return response.content
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch image {url}: {e}")
        return None

def _create_collage_sync(users_data: List[Dict[str, Any]]) -> bytes:
    if not users_data:
        img = Image.new('RGB', (100, 100), color='black')
        buf = io.BytesIO()
        img.save(buf, format='JPEG')
        return buf.getvalue()

    n = len(users_data)
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)

    cell_size = 500
    width = cols * cell_size
    height = rows * cell_size

    collage = Image.new('RGB', (width, height), color='black')

    # Автоматически скачиваем красивые шрифты, если их нет
    font_bold_url = "https://raw.githubusercontent.com/cygnus-rom/external_inter-fonts/caf-ten/Inter-Bold.ttf"
    font_medium_url = "https://raw.githubusercontent.com/cygnus-rom/external_inter-fonts/caf-ten/Inter-Medium.ttf"
    
    def load_font(url, filename, size):
        filepath = os.path.join(BASE_DIR, filename)
        if not os.path.exists(filepath):
            try:
                urllib.request.urlretrieve(url, filepath)
            except Exception as e:
                logger.error(f"Failed to download font {filename}: {e}")
        try:
            return ImageFont.truetype(filepath, size)
        except IOError:
            return ImageFont.load_default()

    # Загружаем правильные шрифты Inter с поддержкой всех языков
    font_large = load_font(font_bold_url, "Inter-Bold.ttf", 42)
    font_medium = load_font(font_bold_url, "Inter-Bold.ttf", 28)
    font_small = load_font(font_medium_url, "Inter-Medium.ttf", 24)

    for idx, user_data in enumerate(users_data):
        row = idx // cols
        col = idx % cols
        x = col * cell_size
        y = row * cell_size

        image_bytes = user_data.get("image_bytes")
        if image_bytes:
            try:
                cover = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                cover = cover.resize((cell_size, cell_size), Image.Resampling.LANCZOS)
            except Exception:
                cover = Image.new('RGB', (cell_size, cell_size), color=(30, 30, 30))
        else:
            cover = Image.new('RGB', (cell_size, cell_size), color=(30, 30, 30))

        # Делаем высокий темный градиент для читаемости большого шрифта
        gradient = Image.new('RGBA', (cell_size, cell_size), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(gradient)
        gradient_height = int(cell_size * 0.5) # Градиент на 50% обложки
        for i in range(gradient_height):
            alpha = int(255 * (1 - (i / gradient_height)))
            # Немного сгущаем тьму внизу
            alpha = min(255, int(alpha * 1.2))
            draw.line([(0, cell_size - i), (cell_size, cell_size - i)], fill=(0, 0, 0, alpha))
            
        cover = cover.convert("RGBA")
        cover = Image.alpha_composite(cover, gradient)
        
        draw = ImageDraw.Draw(cover)
        
        username = f"{user_data.get('spotify_username', 'user')}"
        track_name = user_data.get('track_name', 'Unknown Track')
        artists = user_data.get('artists', 'Unknown Artist')

        # Drop shadow text helper (делаем тени мягче и дальше)
        def draw_text_with_shadow(draw_obj, pos, text, font, fill_color=(255, 255, 255)):
            x_pos, y_pos = pos
            draw_obj.text((x_pos+2, y_pos+3), text, font=font, fill=(0, 0, 0, 200))
            draw_obj.text((x_pos, y_pos), text, font=font, fill=fill_color)

        margin = 25
        text_y = cell_size - margin - 35 
        
        # Рисуем снизу вверх
        draw_text_with_shadow(draw, (margin, text_y), artists, font_small, fill_color=(200, 200, 200))
        text_y -= 48
        draw_text_with_shadow(draw, (margin, text_y), track_name, font_large, fill_color=(255, 255, 255))
        text_y -= 40
        draw_text_with_shadow(draw, (margin, text_y), username, font_medium, fill_color=(29, 185, 84)) 

        collage.paste(cover, (x, y))

    buf = io.BytesIO()
    collage.convert("RGB").save(buf, format='JPEG', quality=90)
    return buf.getvalue()

async def build_nowplaying_image(users_data: List[Dict[str, Any]]) -> bytes:
    """
    Expects users_data: [{'spotify_username': str, 'track_name': str, 'artists': str, 'image_url': str}, ...]
    Returns JPEG bytes of collage
    """
    if not users_data:
        raise ValueError("No users are currently playing anything.")

    # Fetch images asynchronously
    async with httpx.AsyncClient() as client:
        tasks = [fetch_image(client, user.get("image_url")) for user in users_data]
        images_bytes = await asyncio.gather(*tasks)

    for user_data, img_bytes in zip(users_data, images_bytes):
        user_data["image_bytes"] = img_bytes

    # Offload PIL processing to a separate thread to prevent blocking event loop
    result_bytes = await asyncio.to_thread(_create_collage_sync, users_data)
    
    return result_bytes
