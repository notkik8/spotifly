import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from aiogram.types import Update

from config import settings
from database import init_db, save_user
from spotify_api import spotify_client
from bot_handlers import bot, dp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEBHOOK_PATH = f"/bot/{settings.BOT_TOKEN}"
WEBHOOK_URL = f"{settings.BASE_URL}{WEBHOOK_PATH}"

_polling_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _polling_task
    # Startup Events
    await init_db()
    
    # Set webhook if BASE_URL is HTTPS
    if settings.BASE_URL.startswith("https"):
        await bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    else:
        logger.warning(f"BASE_URL {settings.BASE_URL} is HTTP. Telegram requires HTTPS for Webhooks.")
        logger.warning("Deleting webhook and starting polling mode in background...")
        await bot.delete_webhook()
        # Start polling in background
        _polling_task = asyncio.create_task(dp.start_polling(bot))

    yield
    
    # Shutdown Events
    try:
        if settings.BASE_URL.startswith("https"):
            await bot.delete_webhook()
        elif _polling_task:
            _polling_task.cancel()
            try:
                await _polling_task
            except asyncio.CancelledError:
                pass
    except Exception as e:
        logger.error(f"Failed to shutdown gracefully: {e}")
    await bot.session.close()

from pathlib import Path

app = FastAPI(lifespan=lifespan)

LANDING_PAGE_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Spotifly — Твоя музыка в Telegram</title>
    <meta name="description" content="Транслируй свою музыку из Spotify прямо в группы Telegram. Делись тем, что слушаешь!">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

        :root {
            --spotify-green: #1DB954;
            --spotify-brighter: #1ed760;
            --bg-dark: #0B0F19;
            --bg-gradient: linear-gradient(135deg, #0B0F19 0%, #170d24 100%);
        }

        body, html {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            font-family: 'Inter', sans-serif;
            background: var(--bg-gradient);
            color: white;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Moving Background Collage */
        .collage-container {
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            transform: rotate(-15deg);
            z-index: 0;
            pointer-events: none;
            opacity: 0.15;
            animation: scrollBackground 60s linear infinite;
        }

        @keyframes scrollBackground {
            0% { transform: rotate(-15deg) translateY(0); }
            100% { transform: rotate(-15deg) translateY(-20%); }
        }

        .album-cover {
            width: 200px;
            height: 200px;
            border-radius: 12px;
            background-size: cover;
            background-position: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            transition: opacity 0.5s ease;
        }

        /* Overlay to fade out the edges and make text readable */
        .overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at center, rgba(11, 15, 25, 0.4) 0%, rgba(11, 15, 25, 0.95) 80%);
            z-index: 1;
            pointer-events: none;
        }

        /* Main Content */
        .content {
            position: relative;
            z-index: 2;
            text-align: center;
            max-width: 600px;
            padding: 40px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-radius: 30px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.5), inset 0 0 0 1px rgba(255,255,255,0.05);
            animation: fadeInUp 1s ease forwards;
            opacity: 0;
            transform: translateY(30px);
        }

        @keyframes fadeInUp {
            to { opacity: 1; transform: translateY(0); }
        }

        .logo-wrap {
            margin-bottom: 20px;
        }

        h1 {
            font-size: 3.5rem;
            font-weight: 900;
            margin: 0 0 15px 0;
            background: linear-gradient(135deg, #fff 0%, #a5a5a5 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1px;
        }

        p {
            font-size: 1.2rem;
            color: #b3b3b3;
            margin: 0 0 35px 0;
            line-height: 1.5;
        }

        .btn {
            display: inline-block;
            background-color: var(--spotify-green);
            color: #000;
            text-decoration: none;
            padding: 18px 40px;
            border-radius: 50px;
            font-weight: 700;
            font-size: 1.1rem;
            letter-spacing: 0.5px;
            transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            box-shadow: 0 4px 15px rgba(29, 185, 84, 0.4);
        }

        .btn:hover {
            background-color: var(--spotify-brighter);
            transform: scale(1.05) translateY(-2px);
            box-shadow: 0 10px 25px rgba(29, 185, 84, 0.6);
        }

        .btn:active {
            transform: scale(0.98);
        }

        @media (max-width: 600px) {
            h1 { font-size: 2.5rem; }
            .content { padding: 30px 20px; margin: 20px; }
            .album-cover { width: 120px; height: 120px; }
        }
    </style>
</head>
<body>
    <div class="collage-container" id="collage"></div>
    <div class="overlay"></div>

    <div class="content">
        <div class="logo-wrap">
            <svg viewBox="0 0 24 24" width="64" height="64" fill="#1DB954">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.6 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.24 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.84.24 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.6.18-1.2.72-1.38 4.26-1.26 11.28-1.02 15.72 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
            </svg>
        </div>
        <h1>Spotifly</h1>
        <p>Узнавай, что слушают твои друзья. Транслируй свою активность из Spotify прямо в чаты Telegram в реальном времени.</p>
        <a href="https://t.me/ladsjambot" class="btn">Добавить в Telegram</a>
    </div>

    <script>
        const albums = [
            "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/56/ff/25/56ff259a-f9f9-54c3-3484-a45fa1c0348e/6180.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/a1/47/ba/a147ba91-31cd-ef4d-d785-040036d14598/12CMGIM34362.rgb.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/a1/ba/64/a1ba6484-f462-1b88-ddff-d4c014d5f265/196874018361.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/cc/8e/fb/cc8efb15-ad5e-69fc-ae92-dd921630c41d/199806333808.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/32/4f/fd/324ffda2-9e51-8f6a-0c2d-c6fd2b41ac55/074643811224.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/6b/2a/c8/6b2ac856-ac42-8278-b0cb-4ded012efd57/26BMR0007667.rgb.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music125/v4/f0/c7/c8/f0c7c8f4-4319-d357-ddaf-566ef8e2194e/081227979379.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/4c/b6/e5/4cb6e5b1-2db0-88c0-f025-b79cad3b8fab/196873832111.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music116/v4/9d/1b/c0/9d1bc061-4161-87bc-3cec-49e5951df334/197190214994.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/67/c6/c9/67c6c9b0-e879-7e4d-fcda-dc52f758ec43/888880457066.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/7a/b9/73/7ab9736c-3399-125f-5dcd-ae73c0408931/823000220731.png/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/38/8b/ce/388bcea4-f133-d51a-9023-e628744e52fd/437711.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/ef/f1/65/eff16551-2b83-202a-f923-a655a57c61b8/196872452563.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/54/f2/ef/54f2ef79-c668-8d6f-28cd-ae48c45009b7/196874193211.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/ed/46/bf/ed46bf4e-7cb9-965a-54f3-03059977fe6c/075679589293.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/54/e8/32/54e8324f-9ae0-f39c-687c-2ea6d2c77f44/199806246184.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/d5/5f/28/d55f28f4-610c-ee81-dc16-a01cda46bbc4/886443546264.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music221/v4/7e/33/73/7e337333-0802-d7b5-8848-d20fdbdf993c/075679584731.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music115/v4/d2/48/f4/d248f4ae-a7e4-a48e-1588-6617de3e8d76/mzi.izeorbmm.jpg/600x600bb.png",
            "https://is1-ssl.mzstatic.com/image/thumb/Music211/v4/76/28/e7/7628e7b8-0268-f529-6ca8-d5bffb1f2d9e/4099964214482.jpg/600x600bb.png"
        ];

        const collage = document.getElementById('collage');
        for (let i = 0; i < 45; i++) {
            const div = document.createElement('div');
            div.className = 'album-cover';
            const randomAlbum = albums[Math.floor(Math.random() * albums.length)];
            div.style.backgroundImage = `url(${randomAlbum})`;
            collage.appendChild(div);
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def read_root():
    return HTMLResponse(content=LANDING_PAGE_HTML, status_code=200)

@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    if not settings.BASE_URL.startswith("https"):
        return {"status": "polling mode active"}
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"status": "ok"}

@app.get("/callback")
async def spotify_callback(code: str = None, state: str = None, error: str = None):
    """
    Handles redirect from Spotify OAuth login
    `state` is passed from our start command and contains the user's telegram_id.
    """
    if error:
        return {"error": error}
    if not code or not state:
        return {"error": "Missing code or state"}

    try:
        telegram_id = int(state)
    except ValueError:
        return {"error": "Invalid state (telegram_id)"}

    # Exchange code for tokens
    token_data = await spotify_client.exchange_code_for_token(code)
    if not token_data:
        return {"error": "Failed to exchange authorization code"}

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    
    # Fetch user profile to get display name
    spotify_username = None
    if access_token:
        profile = await spotify_client.get_current_user_profile(access_token)
        if profile:
            spotify_username = profile.get("display_name") or profile.get("id")

    # Save to SQLite
    await save_user(telegram_id, refresh_token, spotify_username)
    
    # Notify user they've successfully connected
    try:
        await bot.send_message(
            chat_id=telegram_id, 
            text=f"✅ Successfully connected Spotify as {spotify_username}! "
                 f"You can now use the bot in group chats."
        )
    except Exception as e:
        logger.error(f"Failed to notify user {telegram_id}: {e}")

    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Авторизация успешна</title>
        <style>
            body { font-family: 'Helvetica Neue', Arial, sans-serif; background-color: #121212; color: white; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .container { text-align: center; background: #181818; padding: 40px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
            h1 { color: #1DB954; font-size: 32px; }
            p { color: #b3b3b3; font-size: 18px; margin-bottom: 24px; }
            .btn { background: #1DB954; color: white; text-decoration: none; padding: 14px 32px; border-radius: 50px; font-weight: bold; font-size: 16px; margin-top: 10px; display: inline-block; transition: transform 0.2s; }
            .btn:hover { transform: scale(1.05); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>✅ Успешно!</h1>
            <p>Ваш Spotify аккаунт успешно привязан.<br>Вы можете закрыть это окно и вернуться в Telegram.</p>
            <a href="https://t.me/" class="btn">Вернуться в Telegram</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    import uvicorn
    # Make sure to run with `uvicorn main:app` or `python main.py`
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
