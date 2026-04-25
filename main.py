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

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

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
