"""
Módulo de clima para partidos de fútbol.

Usa Open-Meteo API (gratuita, sin API key) para obtener:
- Clima actual en la ubicación del estadio.
- Pronóstico para la fecha del partido.
- Datos históricos de clima en partidos anteriores.

La altitud y el clima afectan el rendimiento físico de los jugadores,
especialmente en ligas con estadios en zonas de altura.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"


@dataclass
class DatosClima:
    """Datos climáticos de una ubicación."""
    latitud: float
    longitud: float
    altitud_m: float
    temperatura_c: Optional[float] = None
    humedad_pct: Optional[float] = None
    viento_kmh: Optional[float] = None
    precipitacion_mm: Optional[float] = None
    condicion: str = "desconocida"


class ClienteClima:
    """
    Cliente para obtener datos climáticos de Open-Meteo.

    Uso:
        cliente = ClienteClima()
        clima = await cliente.obtener_clima_actual(-12.05, -77.03)
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def obtener_clima_actual(
        self, latitud: float, longitud: float
    ) -> Optional[DatosClima]:
        """Obtiene el clima actual en coordenadas dadas."""
        params = {
            "latitude": latitud,
            "longitude": longitud,
            "current": (
                "temperature_2m,relative_humidity_2m,"
                "wind_speed_10m,precipitation"
            ),
            "timezone": "auto",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(OPEN_METEO_URL, params=params)
                resp.raise_for_status()
                data = resp.json()

            current = data.get("current", {})
            elevation = data.get("elevation", 0)

            return DatosClima(
                latitud=latitud,
                longitud=longitud,
                altitud_m=elevation,
                temperatura_c=current.get("temperature_2m"),
                humedad_pct=current.get("relative_humidity_2m"),
                viento_kmh=current.get("wind_speed_10m"),
                precipitacion_mm=current.get("precipitation"),
                condicion=self._clasificar_condicion(
                    current.get("precipitation", 0),
                    current.get("wind_speed_10m", 0),
                ),
            )
        except Exception as e:
            logger.error(f"Error obteniendo clima: {e}")
            return None

    async def obtener_clima_historico(
        self,
        latitud: float,
        longitud: float,
        fecha: str,
    ) -> Optional[DatosClima]:
        """Obtiene clima histórico para una fecha (YYYY-MM-DD)."""
        params = {
            "latitude": latitud,
            "longitude": longitud,
            "start_date": fecha,
            "end_date": fecha,
            "daily": "temperature_2m_mean,precipitation_sum,wind_speed_10m_max",
            "timezone": "auto",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(OPEN_METEO_ARCHIVE, params=params)
                resp.raise_for_status()
                data = resp.json()

            daily = data.get("daily", {})
            elevation = data.get("elevation", 0)

            return DatosClima(
                latitud=latitud,
                longitud=longitud,
                altitud_m=elevation,
                temperatura_c=(daily.get("temperature_2m_mean") or [None])[0],
                viento_kmh=(daily.get("wind_speed_10m_max") or [None])[0],
                precipitacion_mm=(daily.get("precipitation_sum") or [None])[0],
            )
        except Exception as e:
            logger.error(f"Error obteniendo clima histórico: {e}")
            return None

    @staticmethod
    def _clasificar_condicion(precipitacion: float, viento: float) -> str:
        """Clasifica la condición climática."""
        if precipitacion > 5:
            return "lluvia_fuerte"
        elif precipitacion > 0.5:
            return "lluvia_ligera"
        elif viento > 40:
            return "viento_fuerte"
        elif viento > 20:
            return "viento_moderado"
        return "despejado"


__all__ = ["ClienteClima", "DatosClima"]