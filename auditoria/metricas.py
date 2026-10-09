"""Metricas de rendimiento: Brier Score, LogLoss, ROI."""
from __future__ import annotations
import logging
import math
from dataclasses import dataclass
from data.db import get_session
from auditoria.guardar import PronosticoDB

logger = logging.getLogger(__name__)

@dataclass
class Metricas:
    total: int
    aciertos: int
    fallos: int
    precision: float
    brier_score: float
    log_loss: float
    roi: float

class CalculadoraMetricas:
    def calcular(self) -> Metricas:
        with get_session() as s:
            pronosticos = s.query(PronosticoDB).filter(
                PronosticoDB.resultado.in_(["ACERTADO", "FALLADO"])
            ).all()

        if not pronosticos:
            return Metricas(0, 0, 0, 0.0, 1.0, 1.0, 0.0)

        total = len(pronosticos)
        aciertos = sum(1 for p in pronosticos if p.resultado == "ACERTADO")
        fallos = total - aciertos

        brier = sum(p.brier_score or 1.0 for p in pronosticos) / total

        logloss_vals = []
        for p in pronosticos:
            prob = max(min(p.probabilidad, 0.999), 0.001)
            y = 1.0 if p.resultado == "ACERTADO" else 0.0
            logloss_vals.append(-(y * math.log(prob) + (1 - y) * math.log(1 - prob)))
        logloss = sum(logloss_vals) / total

        ganancia = 0.0
        apostado = 0.0
        for p in pronosticos:
            if p.cuota and p.cuota > 0:
                apostado += 1.0
                if p.resultado == "ACERTADO":
                    ganancia += p.cuota - 1.0
                else:
                    ganancia -= 1.0
        roi = (ganancia / apostado * 100) if apostado > 0 else 0.0

        return Metricas(
            total=total,
            aciertos=aciertos,
            fallos=fallos,
            precision=aciertos / total,
            brier_score=brier,
            log_loss=logloss,
            roi=roi,
        )

__all__ = ["CalculadoraMetricas", "Metricas"]
