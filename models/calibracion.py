"""Calibracion de probabilidades con Isotonic Regression."""
from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class Calibrador:
    def __init__(self):
        self.modelo = None
        self.entrenado = False

    def entrenar(self, probs_predichas: list, resultados_reales: list):
        try:
            from sklearn.isotonic import IsotonicRegression
            self.modelo = IsotonicRegression(out_of_bounds="clip")
            self.modelo.fit(probs_predichas, resultados_reales)
            self.entrenado = True
        except ImportError:
            logger.warning("sklearn no instalado. Calibracion desactivada.")
        except Exception as e:
            logger.error(f"Error entrenando calibrador: {e}")

    def calibrar(self, prob: float) -> float:
        if not self.entrenado or self.modelo is None:
            return prob
        try:
            return float(self.modelo.predict([prob])[0])
        except Exception:
            return prob

    def brier_score(self, probs: list, resultados: list) -> float:
        if not probs:
            return 1.0
        return sum((p - r) ** 2 for p, r in zip(probs, resultados)) / len(probs)

__all__ = ["Calibrador"]
