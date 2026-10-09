"""Ajusta los pesos del ensemble segun rendimiento historico."""
from __future__ import annotations
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)
PESOS_PATH = Path("pesos_ensemble.json")
LEARNING_RATE = 0.02

PESOS_INICIALES = {"poisson": 0.45, "pi_ratings": 0.30, "mercado": 0.25}

class AjustadorPesos:
    def __init__(self):
        self.pesos = self.cargar()

    def cargar(self) -> dict:
        if not PESOS_PATH.exists():
            return dict(PESOS_INICIALES)
        try:
            data = json.loads(PESOS_PATH.read_text())
            if not all(k in data for k in PESOS_INICIALES):
                return dict(PESOS_INICIALES)
            return data
        except Exception:
            return dict(PESOS_INICIALES)

    def guardar(self):
        try:
            data = dict(self.pesos)
            data["fecha"] = datetime.now().isoformat()
            PESOS_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Error guardando pesos: {e}")

    def ajustar(self, brier_por_modelo: dict):
        for modelo, brier in brier_por_modelo.items():
            if modelo not in self.pesos:
                continue
            if brier > 0.25:
                delta = LEARNING_RATE * (brier - 0.20)
                self.pesos[modelo] = max(0.10, self.pesos[modelo] - delta)
            elif brier < 0.18:
                delta = LEARNING_RATE * (0.20 - brier)
                self.pesos[modelo] = min(0.70, self.pesos[modelo] + delta)

        total = sum(self.pesos.values())
        if total > 0:
            self.pesos = {k: v / total for k, v in self.pesos.items()}

        self.guardar()
        return dict(self.pesos)

__all__ = ["AjustadorPesos", "PESOS_INICIALES", "LEARNING_RATE"]
