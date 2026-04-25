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
    <title>LADSJAM</title>
    <meta name="description" content="Транслируй свою музыку из Spotify прямо в группы Telegram.">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Manrope:wght@400;700;800&display=swap');

        :root {
            --swag-accent: #FFD700; /* Drip Gold */
            --bg-dark: #000000;
            --text-main: #FFFFFF;
        }

        body, html {
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            font-family: 'Manrope', sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Moving Background Collage */
        .collage-container {
            position: absolute;
            top: -25%;
            left: -25%;
            width: 150%;
            height: 150%;
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            transform: rotate(-10deg);
            z-index: 0;
            pointer-events: none;
            opacity: 0.25;
            animation: scrollBackground 90s linear infinite;
        }

        @keyframes scrollBackground {
            0% { transform: rotate(-10deg) translateX(0) translateY(0); }
            100% { transform: rotate(-10deg) translateX(-15%) translateY(-15%); }
        }

        .album-cover {
            width: 100px;
            height: 100px;
            border-radius: 4px;
            background-size: cover;
            background-position: center;
            filter: grayscale(80%) contrast(120%);
            border: 2px solid rgba(255, 215, 0, 0.1);
            transition: all 0.5s ease;
        }

        /* Dark edge overlay for the street vibe */
        .overlay {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at center, rgba(0, 0, 0, 0.1) 0%, rgba(0, 0, 0, 0.95) 80%);
            z-index: 1;
            pointer-events: none;
        }

        /* Main brutalist content box */
        .content {
            position: relative;
            z-index: 2;
            text-align: center;
            max-width: 650px;
            padding: 50px 30px;
            background: rgba(10, 10, 10, 0.9);
            border: 4px solid var(--text-main);
            border-radius: 0px;
            box-shadow: 12px 12px 0px var(--swag-accent);
            animation: slamDown 0.6s cubic-bezier(0.25, 1, 0.5, 1) forwards;
            opacity: 0;
            transform: translateY(-50px) scale(1.05);
        }

        @keyframes slamDown {
            to { opacity: 1; transform: translateY(0) scale(1); }
        }

        .logo-icon {
            margin-bottom: 5px;
        }

        h1 {
            font-family: 'Bebas Neue', sans-serif;
            font-size: 6rem;
            line-height: 0.9;
            margin: 0;
            color: var(--text-main);
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 4px 4px 0px var(--swag-accent);
        }

        p {
            font-size: 1.25rem;
            font-weight: 700;
            color: #b3b3b3;
            margin: 20px 0 40px 0;
            line-height: 1.4;
            max-width: 80%;
            margin-left: auto;
            margin-right: auto;
        }

        .highlight {
            color: var(--swag-accent);
        }

        .btn {
            display: inline-block;
            background-color: var(--text-main);
            color: var(--bg-dark);
            text-decoration: none;
            padding: 16px 45px;
            font-weight: 800;
            font-size: 1.3rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            border: 3px solid var(--text-main);
            border-radius: 0px;
            transition: all 0.2s ease-out;
            box-shadow: 6px 6px 0px var(--swag-accent);
        }

        .btn:hover {
            background-color: var(--swag-accent);
            border-color: var(--swag-accent);
            color: var(--bg-dark);
            box-shadow: 2px 2px 0px var(--text-main);
            transform: translate(4px, 4px);
        }

        .btn:active {
            transform: translate(6px, 6px);
            box-shadow: 0px 0px 0px var(--text-main);
        }

        @media (max-width: 600px) {
            h1 { font-size: 4rem; text-shadow: 3px 3px 0px var(--swag-accent); }
            .content { padding: 40px 20px; margin: 20px; box-shadow: 8px 8px 0px var(--swag-accent); }
            .btn { padding: 14px 30px; font-size: 1.1rem; }
        }
    </style>
</head>
<body>
    <div class="collage-container" id="collage"></div>
    <div class="overlay"></div>

    <div class="content">
        <div class="logo-icon">
            <svg viewBox="0 0 24 24" width="64" height="64" fill="#FFD700">
                <path d="M12 2C12 2 8 8 8 12C8 14.2091 9.79086 16 12 16C14.2091 16 16 14.2091 16 12C16 8 12 2 12 2ZM12 22C6.47715 22 2 17.5228 2 12C2 9.0705 3.2618 6.43831 5.25367 4.60333C4.46016 6.36877 4 8.27091 4 10C4 14.4183 7.58172 18 12 18C16.4183 18 20 14.4183 20 10C20 8.27091 19.5398 6.36877 18.7463 4.60333C20.7382 6.43831 22 9.0705 22 12C22 17.5228 17.5228 22 12 22Z"/>
            </svg>
        </div>
        <h1>LADSJAM</h1>
        <p>Твой <span class="highlight">Spotify</span>. Твои правила. Залетай в Telegram и показывай генгу, какую музыку ты крутишь.</p>
        <a href="https://t.me/ladsjambot" class="btn">Ворваться в тусовку</a>
    </div>

    <script>
        const albums = [
            "https://coverartarchive.org/release-group/17a9ea15-ea83-4aeb-8f45-7d8b5eb522d4/front",
            "https://coverartarchive.org/release-group/28298e2c-4d70-3eed-a0f5-a3280c662b3d/front",
            "https://coverartarchive.org/release-group/610fb60f-900a-3c42-ac7d-f6b6aa8035f9/front",
            "https://coverartarchive.org/release-group/ad444843-7160-33d7-b0c9-fc99f2c14a99/front",
            "https://coverartarchive.org/release/ed3e7564-e4a5-4885-9cb9-abaa4c44258c/front",
            "https://coverartarchive.org/release/dbcc52f3-9a94-4ca4-b92b-b05f6d5cb0c8/front",
            "https://coverartarchive.org/release/61eee7a2-43cc-41b5-b7bc-cef045fa074a/front",
            "https://coverartarchive.org/release-group/11ae8c9c-27c1-3308-9761-edb87c8f54ea/front",
            "https://coverartarchive.org/release/ab455983-1a71-4797-bf53-61306ebde2ca/front",
            "https://coverartarchive.org/release/4e9cd9d7-4c26-4d0b-b404-3a7543122225/front",
            "https://coverartarchive.org/release/c034efca-b753-442e-9182-9577731527af/front",
            "https://coverartarchive.org/release-group/5995738d-4b6f-4db6-847b-310a9dc67085/front",
            "https://coverartarchive.org/release-group/0f1b9e07-b38b-4bba-9794-55e0924d7177/front",
            "https://coverartarchive.org/release-group/c65de046-7a48-4269-b4e5-4db0ed328f47/front",
            "https://coverartarchive.org/release/cd653261-861d-49ab-90b8-cef707eb5f89/front",
            "https://coverartarchive.org/release-group/499c19c8-0dab-4824-884b-6191d145e95b/front",
            "https://coverartarchive.org/release-group/5d6e21e1-deb5-428e-bb42-c2a567f3619b/front",
            "https://coverartarchive.org/release/2d45efbe-a339-4002-a9a6-6ece0f33b4bf/front",
            "https://coverartarchive.org/release-group/d36a5a6c-e275-37cd-b518-2d2da71c358b/front",
            "https://coverartarchive.org/release/cb7b2647-8b66-4f24-a349-4a5b389a6f60/front"
        ];

        const collage = document.getElementById('collage');
        for (let i = 0; i < 150; i++) {
            const div = document.createElement('div');
            div.className = 'album-cover';
            const randomAlbum = albums[Math.floor(Math.random() * albums.length)];
            div.style.backgroundImage = `url(${randomAlbum}-250)`;
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
