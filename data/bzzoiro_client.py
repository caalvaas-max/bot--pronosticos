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
        """Cuotas decimales por mercado."""
        return await self._get(f"events/{evento_id}/odds/")

    async def predicciones(self, evento_id: int) -> dict:
        """Predicciones ML (plural - según docs)."""
        return await self._get(f"predictions/{evento_id}/")

    async def detalles_partido(self, evento_id: int) -> dict:
        return await self._get(f"events/{evento_id}/")

    async def partidos_hoy(self) -> list:
        data = await self._get("events/", params={"status": "upcoming", "limit": 100})
        return data.get("results", [])

    async def probabilidades_mercado(self, evento_id: int) -> Optional[dict]:
        """
        Obtiene probabilidades implícitas del mercado 1X2 desde las cuotas.
        Retorna {"local": p1, "empate": p2, "visitante": p3} normalizadas.
        """
        cuotas = await self.cuotas(evento_id)
        if not cuotas:
            return None

        # Buscar cuotas 1X2 en diferentes formatos posibles
        home_odd = None
        draw_odd = None
        away_odd = None

        # Formato 1: dict con markets
        if isinstance(cuotas, dict):
            markets = cuotas.get("markets") or cuotas.get("odds") or cuotas
            if isinstance(markets, dict):
                h2h = markets.get("1x2") or markets.get("h2h") or markets.get("match_winner")
                if isinstance(h2h, dict):
                    home_odd = h2h.get("home") or h2h.get("1")
                    draw_odd = h2h.get("draw") or h2h.get("X")
                    away_odd = h2h.get("away") or h2h.get("2")
                elif isinstance(h2h, list):
                    for o in h2h:
                        sel = str(o.get("selection", "")).lower()
                        if sel in ("home", "1", "local"):
                            home_odd = o.get("odd") or o.get("price")
                        elif sel in ("draw", "x", "empate"):
                            draw_odd = o.get("odd") or o.get("price")
                        elif sel in ("away", "2", "visitante"):
                            away_odd = o.get("odd") or o.get("price")

        if not (home_odd and draw_odd and away_odd):
            logger.warning(f"No se pudieron extraer cuotas 1X2 de: {str(cuotas)[:200]}")
            return None

        try:
            p_home = 1.0 / float(home_odd)
            p_draw = 1.0 / float(draw_odd)
            p_away = 1.0 / float(away_odd)
            total = p_home + p_draw + p_away
            return {
                "local": p_home / total,
                "empate": p_draw / total,
                "visitante": p_away / total,
            }
        except (ValueError, TypeError) as e:
            logger.error(f"Error calculando probabilidades: {e}")
            return None


__all__ = ["BzzoiroClient", "DatosEquipo"]
