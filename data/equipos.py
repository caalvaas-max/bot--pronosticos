"""Informacion de equipos de futbol."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class Equipo:
    nombre: str
    pais: Optional[str] = None
    liga: Optional[str] = None
    estadio: Optional[str] = None
    altitud_m: Optional[float] = None
    escudo_url: Optional[str] = None

@dataclass
class EstadisticasEquipo:
    equipo: str
    partidos_jugados: int = 0
    goles_favor: int = 0
    goles_contra: int = 0
    corners_promedio: float = 0.0
    tarjetas_promedio: float = 0.0
    forma_reciente: list = field(default_factory=list)

    @property
    def goles_promedio(self) -> float:
        if self.partidos_jugados == 0:
            return 0.0
        return self.goles_favor / self.partidos_jugados

    @property
    def goles_recibidos_promedio(self) -> float:
        if self.partidos_jugados == 0:
            return 0.0
        return self.goles_contra / self.partidos_jugados

__all__ = ["Equipo", "EstadisticasEquipo"]
