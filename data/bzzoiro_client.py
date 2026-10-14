"""Cliente completo para la API de Bzzoiro."""
from __future__ import annotations
import logging
import os
from dataclasses import dataclass, field
from typing import Optional
import httpx

logger = logging.getLogger(__name__)
BASE_URL = "https://sports.bzzoiro.com/api/v2"


@dataclass
class DatosEquipo:
    equipo_id: int
    nombre: str
    goles_promedio: float = 1.3
    goles_recibidos: float = 1.3
    forma: list = field(default_factory=list)
    xg_promedio: float = 1.3
    xg_recibido: float = 1.3


class BzzoiroClient:
    def __init__(self, api_key: Optional[str] = None, timeout: float = 15.0):
        self.api_key = api_key or os.getenv("BZZOIRO_API_KEY", "")
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Accept": "application/json",
        }

    async def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        if not self.api_key:
            logger.warning("BZZOIRO_API_KEY no configurada")
            return {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as c:
                r = await c.get(
                    f"{BASE_URL}/{endpoint}",
                    headers=self.headers,
                    params=params or {},
                )
                r.raise_for_status()
                return r.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} en {endpoint}")
            return {}
        except Exception as e:
            logger.error(f"Error Bzzoiro {endpoint}: {e}")
            return {}

    async def buscar_partido(self, equipo_local: str, equipo_visitante: str):
        data = await self._get("events/", params={"team_name": equipo_local, "limit": 50})
        partidos = data.get("results", [])
        for p in partidos:
            home = p.get("home_team", "").lower()
            away = p.get("away_team", "").lower()
            if (equipo_local.lower() in home and equipo_visitante.lower() in away):
                return p
        return None

    async def stats_partido(self, evento_id: int) -> dict:
        return await self._get(f"events/{evento_id}/stats/")

    async def h2h_partido(self, evento_id: int) -> dict:
        return await self._get(f"events/{evento_id}/h2h/")

    async def alineaciones(self, evento_id: int) -> dict:
        return await self._get(f"events/{evento_id}/lineups/")

    async def cuotas(self, evento_id: int) -> dict:
        return await self._get(f"events/{evento_id}/odds/")

    async def predicciones(self, evento_id: int) -> dict:
        return await self._get(f"events/{evento_id}/prediction/")

    async def detalles_partido(self, evento_id: int) -> dict:
        return await self._get(f"events/{evento_id}/")

    async def partidos_hoy(self) -> list:
        data = await self._get("events/", params={"status": "upcoming", "limit": 100})
        return data.get("results", [])


__all__ = ["BzzoiroClient", "DatosEquipo"]
