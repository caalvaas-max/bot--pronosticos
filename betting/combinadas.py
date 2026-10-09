"""Generador de combinadas de 2-3 mercados con cuota > 1.50."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

CUOTA_MINIMA = 1.50
MAX_PICKS = 3
PROB_MINIMA = 0.55

@dataclass
class Combinada:
    picks: list = field(default_factory=list)
    cuota_total: float = 1.0
    probabilidad_total: float = 1.0

class GeneradorCombinadas:
    def __init__(self, cuota_minima: float = CUOTA_MINIMA):
        self.cuota_minima = cuota_minima

    def generar(self, candidatos: list) -> Combinada:
        elegibles = [c for c in candidatos if c.get("probabilidad", 0) >= PROB_MINIMA]
        elegibles.sort(key=lambda x: x.get("probabilidad", 0), reverse=True)

        combinada = Combinada()
        for cand in elegibles:
            if len(combinada.picks) >= MAX_PICKS:
                break
            prob = cand.get("probabilidad", 0)
            cuota = cand.get("cuota", 1.0 / prob if prob > 0 else 1.0)
            if cuota <= 1.0:
                continue
            combinada.picks.append(cand)
            combinada.cuota_total *= cuota
            combinada.probabilidad_total *= prob
            if (len(combinada.picks) >= 2 and
                combinada.cuota_total >= self.cuota_minima):
                break

        if len(combinada.picks) < 2:
            return Combinada()
        return combinada

__all__ = ["GeneradorCombinadas", "Combinada", "CUOTA_MINIMA", "MAX_PICKS", "PROB_MINIMA"]
