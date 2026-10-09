"""Gestion de bankroll con Kelly Criterion fraccional."""
from __future__ import annotations
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

FRACCION_KELLY = 0.25
STAKE_MAXIMO = 0.05

@dataclass
class ApuestaSugerida:
    stake: float
    fraccion_bankroll: float
    kelly_completo: float
    kelly_fraccionado: float

class GestorBankroll:
    def __init__(self, bankroll: float, fraccion: float = FRACCION_KELLY):
        self.bankroll = bankroll
        self.fraccion = fraccion

    def calcular_stake(self, prob: float, cuota: float) -> ApuestaSugerida:
        if cuota <= 1.0 or prob <= 0.0 or prob >= 1.0:
            return ApuestaSugerida(0.0, 0.0, 0.0, 0.0)

        b = cuota - 1.0
        q = 1.0 - prob
        kelly_completo = (prob * b - q) / b

        if kelly_completo <= 0:
            return ApuestaSugerida(0.0, 0.0, kelly_completo, 0.0)

        kelly_fraccionado = kelly_completo * self.fraccion
        fraccion_final = min(kelly_fraccionado, STAKE_MAXIMO)
        stake = self.bankroll * fraccion_final

        return ApuestaSugerida(
            stake=stake,
            fraccion_bankroll=fraccion_final,
            kelly_completo=kelly_completo,
            kelly_fraccionado=kelly_fraccionado,
        )

    def actualizar_bankroll(self, ganancia: float):
        self.bankroll += ganancia

__all__ = ["GestorBankroll", "ApuestaSugerida", "FRACCION_KELLY", "STAKE_MAXIMO"]
