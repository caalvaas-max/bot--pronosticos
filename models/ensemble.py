"""Combina predicciones de multiples modelos."""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

PESOS_DEFAULT = {"poisson": 0.45, "pi_ratings": 0.30, "mercado": 0.25}

def combinar_1x2(prob_poisson: dict, prob_pi: dict, prob_mercado: dict = None, pesos: dict = None) -> dict:
    if pesos is None:
        pesos = PESOS_DEFAULT

    if prob_mercado is None:
        total_activos = pesos["poisson"] + pesos["pi_ratings"]
        pesos = {
            "poisson": pesos["poisson"] / total_activos,
            "pi_ratings": pesos["pi_ratings"] / total_activos,
            "mercado": 0.0,
        }

    resultado = {"local": 0.0, "empate": 0.0, "visitante": 0.0}
    for clave in resultado:
        resultado[clave] = (
            pesos["poisson"] * prob_poisson.get(clave, 0.0)
            + pesos["pi_ratings"] * prob_pi.get(clave, 0.0)
            + pesos.get("mercado", 0.0) * (prob_mercado or {}).get(clave, 0.0)
        )

    total = sum(resultado.values())
    if total > 0:
        resultado = {k: v / total for k, v in resultado.items()}
    return resultado

__all__ = ["combinar_1x2", "PESOS_DEFAULT"]
