import aiosqlite
import logging
from config import settings

logger = logging.getLogger(__name__)

async def init_db():
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                spotify_refresh_token TEXT NOT NULL,
                spotify_username TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS group_members (
                group_id INTEGER,
                telegram_id INTEGER,
                PRIMARY KEY (group_id, telegram_id),
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id) ON DELETE CASCADE
            )
        ''')
        await db.commit()
        logger.info("Database initialized.")

async def save_user(telegram_id: int, refresh_token: str, spotify_username: str = None):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute('''
            INSERT INTO users (telegram_id, spotify_refresh_token, spotify_username)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                spotify_refresh_token=excluded.spotify_refresh_token,
                spotify_username=excluded.spotify_username
        ''', (telegram_id, refresh_token, spotify_username))
        await db.commit()

async def add_user_to_group(group_id: int, telegram_id: int):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        # Check if user exists in the `users` table
        async with db.execute('SELECT 1 FROM users WHERE telegram_id = ?', (telegram_id,)) as cursor:
            if not await cursor.fetchone():
                return False
        
        await db.execute('''
            INSERT OR IGNORE INTO group_members (group_id, telegram_id)
            VALUES (?, ?)
        ''', (group_id, telegram_id))
        await db.commit()
        return True

async def get_group_members_with_tokens(group_id: int):
    """
    Returns a list of dictionaries with user data for a specific group.
    Format: [{'telegram_id': int, 'spotify_refresh_token': str, 'spotify_username': str}]
    """
    async with aiosqlite.connect(settings.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute('''
            SELECT u.telegram_id, u.spotify_refresh_token, u.spotify_username
            FROM group_members gm
            JOIN users u ON gm.telegram_id = u.telegram_id
            WHERE gm.group_id = ?
        ''', (group_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

async def delete_user(telegram_id: int):
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute('DELETE FROM users WHERE telegram_id = ?', (telegram_id,))
        await db.execute('DELETE FROM group_members WHERE telegram_id = ?', (telegram_id,))
        await db.commit()
