"""Cliente para la API de Bzzoiro."""
from __future__ import annotations
import logging
import os
from typing import Optional
import httpx

logger = logging.getLogger(__name__)
BASE_URL = "https://sports.bzzoiro.com/api/v2"

class BzzoiroClient:
    def __init__(self, api_key: Optional[str] = None, timeout: float = 15.0):
        self.api_key = api_key or os.getenv("BZZOIRO_API_KEY", "")
        self.timeout = timeout
        self.headers = {"Authorization": f"Token {self.api_key}"}

    async def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r = await c.get(f"{BASE_URL}/{endpoint}", headers=self.headers, params=params or {})
                r.raise_for_status()
                return r.json()
        except Exception as e:
            logger.error(f"Error Bzzoiro {endpoint}: {e}")
            return {}

    async def partidos_hoy(self) -> list:
        data = await self._get("events/")
        return data.get("results", [])

    async def predicciones(self, evento_id: str) -> dict:
        return await self._get(f"predictions/{evento_id}/")

    async def cuotas(self, evento_id: str) -> dict:
        return await self._get(f"odds/{evento_id}/")

__all__ = ["BzzoiroClient"]
