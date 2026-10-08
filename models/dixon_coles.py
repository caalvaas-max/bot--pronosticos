"""Correccion Dixon-Coles para el modelo Poisson."""
from __future__ import annotations
import logging

logger = logging.getLogger(__name__)

RHO_DEFAULT = -0.10

def factor_tau(x: int, y: int, lmbda: float, mu: float, rho: float = RHO_DEFAULT) -> float:
    if x == 0 and y == 0:
        return 1.0 - lmbda * mu * rho
    elif x == 0 and y == 1:
        return 1.0 + lmbda * rho
    elif x == 1 and y == 0:
        return 1.0 + mu * rho
    elif x == 1 and y == 1:
        return 1.0 - rho
    return 1.0

def aplicar_correccion(matriz, lmbda: float, mu: float, rho: float = RHO_DEFAULT):
    for i in range(min(2, matriz.shape[0])):
        for j in range(min(2, matriz.shape[1])):
            tau = factor_tau(i, j, lmbda, mu, rho)
            tau = max(tau, 0.001)
            matriz[i, j] *= tau
    total = matriz.sum()
    if total > 0:
        matriz = matriz / total
    return matriz

__all__ = ["factor_tau", "aplicar_correccion", "RHO_DEFAULT"]
