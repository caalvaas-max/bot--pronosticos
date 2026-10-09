"""Calibrador automatico de probabilidades basado en historico."""
from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
CALIBRADOR_PATH = Path("calibrador.json")

class CalibradorAutomatico:
    def __init__(self):
        self.modelo = None
        self.entrenado = False
        self.cargar()

    def entrenar(self, probs: list, resultados: list) -> bool:
        try:
            from sklearn.isotonic import IsotonicRegression
            self.modelo = IsotonicRegression(out_of_bounds="clip")
            self.modelo.fit(probs, resultados)
            self.entrenado = True
            return True
        except Exception as e:
            logger.error(f"Error entrenando: {e}")
            return False

    def calibrar(self, prob: float) -> float:
        if not self.entrenado or self.modelo is None:
            return prob
        try:
            return float(self.modelo.predict([prob])[0])
        except Exception:
            return prob

    def guardar(self):
        if not self.entrenado or self.modelo is None:
            return
        try:
            data = {
                "x": self.modelo.X_thresholds_.tolist(),
                "y": self.modelo.y_thresholds_.tolist(),
                "fecha": datetime.now().isoformat(),
            }
            CALIBRADOR_PATH.write_text(json.dumps(data))
        except Exception as e:
            logger.error(f"Error guardando calibrador: {e}")

    def cargar(self):
        if not CALIBRADOR_PATH.exists():
            return
        try:
            from sklearn.isotonic import IsotonicRegression
            data = json.loads(CALIBRADOR_PATH.read_text())
            self.modelo = IsotonicRegression(out_of_bounds="clip")
            self.modelo.fit(data["x"], data["y"])
            self.entrenado = True
        except Exception as e:
            logger.error(f"Error cargando calibrador: {e}")

__all__ = ["CalibradorAutomatico"]
