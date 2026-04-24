import base64
import logging
from typing import Optional, Dict, Any
import httpx
from config import settings
from database import delete_user

logger = logging.getLogger(__name__)

class SpotifyClient:
    def __init__(self):
        self.client_id = settings.SPOTIFY_CLIENT_ID
        self.client_secret = settings.SPOTIFY_CLIENT_SECRET
        self.redirect_uri = settings.SPOTIFY_REDIRECT_URI
        self.token_url = "https://accounts.spotify.com/api/token"
        
    def get_auth_url(self, state: str) -> str:
        scopes = "user-read-currently-playing"
        return (f"https://accounts.spotify.com/authorize"
                f"?response_type=code"
                f"&client_id={self.client_id}"
                f"&scope={scopes}"
                f"&redirect_uri={self.redirect_uri}"
                f"&state={state}")

    async def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_base64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.token_url, data=data, headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Spotify token exchange failed: {e}")
                return None

    async def refresh_access_token(self, telegram_id: int, refresh_token: str) -> Optional[str]:
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_base64 = base64.b64encode(auth_str.encode("utf-8")).decode("utf-8")

        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.token_url, data=data, headers=headers)
                
                if response.status_code in (400, 401, 403):
                    data_json = response.json()
                    if data_json.get("error") == "invalid_grant":
                        logger.warning(f"Refresh token invalid for user {telegram_id}. Removing from DB.")
                        await delete_user(telegram_id)
                        return None

                response.raise_for_status()
                token_info = response.json()
                return token_info.get("access_token")
            except httpx.HTTPError as e:
                logger.error(f"Failed to refresh token for user {telegram_id}: {e}")
                return None

    async def get_currently_playing(self, telegram_id: int, refresh_token: str) -> Optional[Dict[str, Any]]:
        access_token = await self.refresh_access_token(telegram_id, refresh_token)
        if not access_token:
            return None

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            try:
                response = await client.get("https://api.spotify.com/v1/me/player/currently-playing", headers=headers)
                
                if response.status_code == 204: # No content (nothing is playing)
                    return None
                    
                response.raise_for_status()
                data = response.json()
                
                if not data or not data.get("is_playing"):
                    return None
                
                item = data.get("item")
                if not item:
                    return None

                track_name = item.get("name")
                artists = ", ".join([artist.get("name") for artist in item.get("artists", [])])
                album_images = item.get("album", {}).get("images", [])
                
                image_url = album_images[0].get("url") if album_images else None
                    
                return {
                    "track_name": track_name,
                    "artists": artists,
                    "image_url": image_url
                }
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch currently playing for user {telegram_id}: {e}")
                return None

    async def get_current_user_profile(self, access_token: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            try:
                response = await client.get("https://api.spotify.com/v1/me", headers=headers)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"Failed to fetch user profile: {e}")
                return None

spotify_client = SpotifyClient()
