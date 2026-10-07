"""Modulo de noticias y lesiones."""
from __future__ import annotations
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import httpx

logger = logging.getLogger(__name__)
API_FOOTBALL_BASE = "https://v3.football.api-sports.io"


@dataclass
class JugadorLesionado:
    nombre: str
    equipo: str
    tipo: str
    detalle: str
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None


@dataclass
class NoticiaEquipo:
    titulo: str
    fuente: str
    fecha: str
    resumen: str = ""
    url: str = ""


@dataclass
class InfoEquipo:
    nombre: str
    lesiones: list = field(default_factory=list)
    noticias: list = field(default_factory=list)
    forma_reciente: str = ""
    ultima_actualizacion: str = ""


class ClienteNoticias:
    """Cliente para API-Football."""

    def __init__(self, api_key: Optional[str] = None, timeout: float = 15.0):
        self.api_key = api_key or os.getenv("API_FOOTBALL_KEY", "")
        self.timeout = timeout

    def _headers(self) -> dict:
        return {"x-apisports-key": self.api_key}

    async def obtener_lesiones(self, equipo: str, temporada: int = 2025) -> list:
        if not self.api_key:
            logger.warning("API_FOOTBALL_KEY no configurada.")
            return []
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{API_FOOTBALL_BASE}/injuries",
                    headers=self._headers(),
                    params={"team": equipo, "season": temporada},
                )
                resp.raise_for_status()
                data = resp.json()
            lesiones = []
            for item in data.get("response", []):
                player = item.get("player", {})
                team = item.get("team", {})
                fixture = item.get("fixture", {})
                lesiones.append(JugadorLesionado(
                    nombre=player.get("name", "Desconocido"),
                    equipo=team.get("name", equipo),
                    tipo=item.get("type", "lesion"),
                    detalle=item.get("reason", "Sin detalle"),
                    fecha_inicio=fixture.get("date"),
                ))
            return lesiones
        except Exception as e:
            logger.error(f"Error obteniendo lesiones: {e}")
            return []

    async def obtener_info_equipo(self, equipo: str) -> InfoEquipo:
        lesiones = await self.obtener_lesiones(equipo)
        return InfoEquipo(
            nombre=equipo,
            lesiones=lesiones,
            ultima_actualizacion=datetime.now().isoformat(),
        )


__all__ = [
    "ClienteNoticias",
    "JugadorLesionado",
    "NoticiaEquipo",
    "InfoEquipo",
]
