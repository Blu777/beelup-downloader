import aiohttp
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from .models import (
    BootstrapData, Player, PlayerStats, GeneralStats
)
from .client import ChalaCupAPIError

class AsyncChalaCupClient:
    """
    Cliente oficial asíncrono para interactuar con la API REST de Chala Cup Club.
    Ideal para bots de Discord, Telegram o microservicios concurrentes.
    """
    DEFAULT_BASE_URL = "https://chala-cup-club.vercel.app"
    TOKEN_FILE = ".chala_token"

    def __init__(self, base_url: str = DEFAULT_BASE_URL, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._session: Optional[aiohttp.ClientSession] = None
        if not self.token and os.path.exists(self.TOKEN_FILE):
            try:
                with open(self.TOKEN_FILE, "r") as f:
                    self.token = f.read().strip()
            except Exception:
                pass

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {
                "User-Agent": "AsyncChalaCupAPI-PythonClient/0.1.0",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            if self.token:
                headers["X-Chala-Token"] = self.token
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def close(self):
        """Cierra la sesión HTTP asíncrona."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        session = await self._get_session()
        url = f"{self.base_url}/club/api/{endpoint.lstrip('/')}"
        
        if self.token and "headers" not in kwargs:
            kwargs["headers"] = {"X-Chala-Token": self.token}

        async with session.request(method, url, **kwargs) as response:
            if response.status == 204:
                return None
            
            try:
                data = await response.json()
            except Exception:
                text = await response.text()
                data = {"message": text}

            if not response.ok:
                detail = data.get("detail", data.get("message", "Error desconocido de API"))
                if isinstance(detail, list):
                    detail = " / ".join([item.get("msg", str(item)) if isinstance(item, dict) else str(item) for item in detail])
                raise ChalaCupAPIError(f"[{response.status}] {detail}")
            
            return data

    async def get_bootstrap(self) -> BootstrapData:
        """Obtiene el estado completo en tiempo real del torneo."""
        raw = await self._request("GET", "/bootstrap")
        return BootstrapData.from_dict(raw)

    async def login(self, email: str, password: str, persist_token: bool = True) -> str:
        res = await self._request("POST", "/auth/login", json={"email": email, "password": password})
        self.token = res.get("token", "")
        if persist_token and self.token:
            try:
                with open(self.TOKEN_FILE, "w") as f:
                    f.write(self.token)
            except Exception:
                pass
        return self.token

    async def signup_for_match(self, match_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"/matches/{match_id}/signup")

    async def withdraw_from_match(self, match_id: str) -> Dict[str, Any]:
        return await self._request("POST", f"/matches/{match_id}/withdraw")

    async def vote_player_stats(self, target_user_id: str, stats: PlayerStats) -> Dict[str, Any]:
        return await self._request("POST", f"/players/{target_user_id}/vote", json=stats.to_dict())
