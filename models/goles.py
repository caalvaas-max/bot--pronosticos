"""Calculo de goles esperados por equipo."""
from __future__ import annotations
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

PROMEDIO_LIGA = 1.35

@dataclass
class GolesEsperados:
    lambda_local: float
    lambda_visitante: float

def calcular_lambda(
    goles_favor_local: float,
    goles_contra_local: float,
    goles_favor_visitante: float,
    goles_contra_visitante: float,
    factor_localia: float = 1.15,
) -> GolesEsperados:
    ataque_local = max(goles_favor_local / PROMEDIO_LIGA, 0.1)
    defensa_local = max(goles_contra_local / PROMEDIO_LIGA, 0.1)
    ataque_visitante = max(goles_favor_visitante / PROMEDIO_LIGA, 0.1)
    defensa_visitante = max(goles_contra_visitante / PROMEDIO_LIGA, 0.1)

    lambda_local = ataque_local * defensa_visitante * PROMEDIO_LIGA * factor_localia
    lambda_visitante = ataque_visitante * defensa_local * PROMEDIO_LIGA

    lambda_local = max(0.3, min(lambda_local, 4.0))
    lambda_visitante = max(0.3, min(lambda_visitante, 4.0))

    return GolesEsperados(lambda_local=lambda_local, lambda_visitante=lambda_visitante)

__all__ = ["calcular_lambda", "GolesEsperados", "PROMEDIO_LIGA"]
