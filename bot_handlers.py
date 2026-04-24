import asyncio
import logging
from aiogram import Router, F, Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.filters import Command

from config import settings
from database import add_user_to_group, get_group_members_with_tokens
from spotify_api import spotify_client
from image_builder import build_nowplaying_image

logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.type != "private":
        await message.answer("Please start me in private messages to connect your Spotify.")
        return

    # Pass telegram_id as state
    auth_url = spotify_client.get_auth_url(state=str(message.from_user.id))
    
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Connect Spotify", url=auth_url)]
    ])
    
    await message.answer(
        "Welcome! Click the button below to authorize this bot with your Spotify account \n"
        "so we can show your currently playing tracks to your friends.",
        reply_markup=markup
    )

@router.message(F.text.lower() == "nowplaying")
async def cmd_nowplaying(message: Message, bot: Bot):
    if message.chat.type == "private":
        await message.answer("The 'nowplaying' command is designed for group chats.")
        return

    group_id = message.chat.id
    
    # Send a typing action
    await bot.send_chat_action(chat_id=group_id, action="upload_photo")

    members = await get_group_members_with_tokens(group_id)
    if not members:
        await message.reply("No one in this group has connected their Spotify yet!")
        return

    async def fetch_user_data(member):
        telegram_id = member["telegram_id"]
        refresh_token = member["spotify_refresh_token"]
        spotify_username = member["spotify_username"] or f"user_{telegram_id}"
        
        playing_data = await spotify_client.get_currently_playing(telegram_id, refresh_token)
        if playing_data:
            playing_data["spotify_username"] = spotify_username
            return playing_data
        return None

    tasks = [fetch_user_data(member) for member in members]
    results = await asyncio.gather(*tasks)
    
    active_users = [r for r in results if r is not None]

    if not active_users:
        await message.reply("Nobody is listening to Spotify right now.")
        return

    try:
        image_bytes = await build_nowplaying_image(active_users)
        photo = BufferedInputFile(image_bytes, filename="nowplaying.jpg")
        await message.reply_photo(photo=photo, caption="🎵 Now playing in this chat:")
    except ValueError as e:
        await message.reply(str(e))
    except Exception as e:
        logger.error(f"Failed to build or send image: {e}")
        await message.reply("Oops, an error occurred while generating the image.")

@router.message()
async def passive_tracker(message: Message):
    # Passively track all messages in group chats to accumulate users
    if message.chat.type in ("group", "supergroup"):
        group_id = message.chat.id
        telegram_id = message.from_user.id
        
        # This will silently ignore if the user is not in our database
        await add_user_to_group(group_id, telegram_id)
