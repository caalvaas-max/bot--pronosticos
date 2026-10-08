"""Sistema de rating Pi para equipos de futbol."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

K_FACTOR = 20.0
HOME_ADVANTAGE = 100.0

@dataclass
class RatingEquipo:
    nombre: str
    rating: float = 1500.0
    partidos: int = 0

class PiRatings:
    def __init__(self):
        self.equipos: dict[str, RatingEquipo] = {}

    def obtener(self, nombre: str) -> RatingEquipo:
        if nombre not in self.equipos:
            self.equipos[nombre] = RatingEquipo(nombre=nombre)
        return self.equipos[nombre]

    def probabilidad_local(self, local: str, visitante: str) -> float:
        r_local = self.obtener(local).rating + HOME_ADVANTAGE
        r_visitante = self.obtener(visitante).rating
        return 1.0 / (1.0 + 10 ** ((r_visitante - r_local) / 400.0))

    def actualizar(self, local: str, visitante: str, goles_local: int, goles_visitante: int):
        eq_local = self.obtener(local)
        eq_visitante = self.obtener(visitante)
        prob_local = self.probabilidad_local(local, visitante)

        if goles_local > goles_visitante:
            resultado = 1.0
        elif goles_local < goles_visitante:
            resultado = 0.0
        else:
            resultado = 0.5

        margen = abs(goles_local - goles_visitante)
        factor_margen = (margen + 1) ** 0.5

        cambio = K_FACTOR * factor_margen * (resultado - prob_local)

        eq_local.rating += cambio
        eq_visitante.rating -= cambio
        eq_local.partidos += 1
        eq_visitante.partidos += 1

__all__ = ["PiRatings", "RatingEquipo", "K_FACTOR", "HOME_ADVANTAGE"]
