"""Detecta apuestas con valor esperado positivo (EV+)."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

EV_MINIMO = 0.03

@dataclass
class ValueBet:
    mercado: str
    seleccion: str
    probabilidad: float
    cuota: float
    valor_esperado: float
    stake_sugerido: float = 0.0

class DetectorValue:
    def __init__(self, ev_minimo: float = EV_MINIMO):
        self.ev_minimo = ev_minimo

    def calcular_ev(self, prob: float, cuota: float) -> float:
        return (prob * cuota) - 1.0

    def detectar(self, probabilidades: dict, cuotas: dict) -> list:
        value_bets = []

        for mercado, data in probabilidades.items():
            if isinstance(data, dict):
                for seleccion, prob in data.items():
                    clave_cuota = f"{mercado}:{seleccion}"
                    cuota = cuotas.get(clave_cuota) or cuotas.get(mercado, {}).get(seleccion)
                    if not cuota or cuota <= 1.0:
                        continue
                    ev = self.calcular_ev(prob, cuota)
                    if ev >= self.ev_minimo:
                        value_bets.append(ValueBet(
                            mercado=mercado,
                            seleccion=seleccion,
                            probabilidad=prob,
                            cuota=cuota,
                            valor_esperado=ev,
                        ))
            elif isinstance(data, (int, float)):
                cuota = cuotas.get(mercado)
                if not cuota or cuota <= 1.0:
                    continue
                ev = self.calcular_ev(data, cuota)
                if ev >= self.ev_minimo:
                    value_bets.append(ValueBet(
                        mercado=mercado,
                        seleccion="principal",
                        probabilidad=data,
                        cuota=cuota,
                        valor_esperado=ev,
                    ))

        value_bets.sort(key=lambda v: v.valor_esperado, reverse=True)
        return value_bets

__all__ = ["DetectorValue", "ValueBet", "EV_MINIMO"]
