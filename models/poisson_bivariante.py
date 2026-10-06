"""
Modelo Poisson Bivariante con corrección Dixon-Coles.

Este módulo implementa el modelo matemático principal para calcular
probabilidades de resultados en partidos de fútbol.

El modelo usa la distribución de Poisson para modelar los goles de cada
equipo, y aplica la corrección de Dixon-Coles para ajustar las
probabilidades de resultados con pocos goles (0-0, 1-0, 0-1, 1-1).

Referencia:
    Dixon, M. J., & Coles, S. G. (1997). Modelling Association Football
    Scores and Inefficiencies in the Football Betting Market.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.stats import poisson


# =============================================================================
# CONSTANTES
# =============================================================================

MAX_GOLES = 8  # Máximo de goles a considerar por equipo
RHO_DIXON_COLES = -0.10  # Factor de correlación (valor típico: -0.10 a -0.15)


# =============================================================================
# ESTRUCTURAS DE DATOS
# =============================================================================

@dataclass
class ParametrosPartido:
    """Parámetros de entrada para calcular el modelo."""
    lambda_local: float      # Goles esperados del equipo local
    lambda_visitante: float  # Goles esperados del equipo visitante
    rho: float = RHO_DIXON_COLES  # Factor Dixon-Coles

    def __post_init__(self):
        """Valida que los parámetros sean razonables."""
        if self.lambda_local <= 0:
            raise ValueError(f"lambda_local debe ser positivo, recibido: {self.lambda_local}")
        if self.lambda_visitante <= 0:
            raise ValueError(
                f"lambda_visitante debe ser positivo, recibido: {self.lambda_visitante}"
            )


@dataclass
class Probabilidades1X2:
    """Probabilidades del mercado 1X2."""
    local: float
    empate: float
    visitante: float

    def __post_init__(self):
        """Verifica que las probabilidades sumen ~1.0."""
        total = self.local + self.empate + self.visitante
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Las probabilidades deben sumar 1.0, suma actual: {total}")


# =============================================================================
# FUNCIONES AUXILIARES
# =============================================================================

def _factor_tau(
    x: int,
    y: int,
    lambda_local: float,
    lambda_visitante: float,
    rho: float,
) -> float:
    """
    Calcula el factor de corrección Dixon-Coles para resultados bajos.

    Este factor ajusta las probabilidades de 0-0, 1-0, 0-1, 1-1 que en el
    modelo Poisson simple están subestimadas.

    Args:
        x: Goles del equipo local.
        y: Goles del equipo visitante.
        lambda_local: Goles esperados del local.
        lambda_visitante: Goles esperados del visitante.
        rho: Factor de correlación Dixon-Coles.

    Returns:
        Factor de corrección tau.
    """
    if x == 0 and y == 0:
        return 1 - lambda_local * lambda_visitante * rho
    elif x == 0 and y == 1:
        return 1 + lambda_local * rho
    elif x == 1 and y == 0:
        return 1 + lambda_visitante * rho
    elif x == 1 and y == 1:
        return 1 - rho
    return 1.0


# =============================================================================
# MODELO PRINCIPAL
# =============================================================================

class PoissonBivariante:
    """
    Modelo Poisson Bivariante con corrección Dixon-Coles.

    Uso:
        modelo = PoissonBivariante()
        probs = modelo.calcular_probabilidades(1.65, 1.10)

    Atributos:
        max_goles: Número máximo de goles a considerar por equipo.
        rho: Factor de correlación Dixon-Coles por defecto.
    """

    def __init__(
        self,
        max_goles: int = MAX_GOLES,
        rho: float = RHO_DIXON_COLES,
    ):
        """
        Inicializa el modelo.

        Args:
            max_goles: Máximo de goles por equipo (default: 8).
            rho: Factor Dixon-Coles (default: -0.10).
        """
        self.max_goles = max_goles
        self.rho = rho

    def calcular_matriz(
        self,
        lambda_local: float,
        lambda_visitante: float,
        rho: Optional[float] = None,
    ) -> np.ndarray:
        """
        Calcula la matriz de probabilidades para todos los resultados.

        Args:
            lambda_local: Goles esperados del local.
            lambda_visitante: Goles esperados del visitante.
            rho: Factor Dixon-Coles (usa el de la instancia si es None).

        Returns:
            Matriz de tamaño (max_goles+1) x (max_goles+1) donde
            matriz[i, j] = P(local marca i goles Y visitante marca j goles).

        Raises:
            ValueError: Si los parámetros son inválidos.
        """
        if rho is None:
            rho = self.rho

        # Validar parámetros
        if lambda_local <= 0 or lambda_visitante <= 0:
            raise ValueError(
                f"Los lambdas deben ser positivos. "
                f"Recibidos: local={lambda_local}, visitante={lambda_visitante}"
            )

        n = self.max_goles + 1
        matriz = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                # Probabilidad Poisson simple
                p_local = poisson.pmf(i, lambda_local)
                p_visitante = poisson.pmf(j, lambda_visitante)

                # Aplicar corrección Dixon-Coles
                tau = _factor_tau(i, j, lambda_local, lambda_visitante, rho)

                # Asegurar que tau sea positivo (evitar valores negativos)
                tau = max(tau, 0.0)

                matriz[i, j] = p_local * p_visitante * tau

        # Normalizar la matriz para que sume 1.0
        suma = matriz.sum()
        if suma > 0:
            matriz = matriz / suma

        return matriz

    def calcular_1x2(
        self,
        lambda_local: float,
        lambda_visitante: float,
        rho: Optional[float] = None,
    ) -> Probabilidades1X2:
        """
        Calcula las probabilidades del mercado 1X2.

        Args:
            lambda_local: Goles esperados del local.
            lambda_visitante: Goles esperados del visitante.
            rho: Factor Dixon-Coles.

        Returns:
            Probabilidades1X2 con probabilidades de local, empate, visitante.
        """
        matriz = self.calcular_matriz(lambda_local, lambda_visitante, rho)

        # Sumar probabilidades según el resultado
        p_local = 0.0
        p_empate = 0.0
        p_visitante = 0.0

        for i in range(matriz.shape[0]):
            for j in range(matriz.shape[1]):
                if i > j:
                    p_local += matriz[i, j]
                elif i == j:
                    p_empate += matriz[i, j]
                else:
                    p_visitante += matriz[i, j]

        return Probabilidades1X2(
            local=float(p_local),
            empate=float(p_empate),
            visitante=float(p_visitante),
        )

    def calcular_over_under(
        self,
        lambda_local: float,
        lambda_visitante: float,
        linea: float = 2.5,
        rho: Optional[float] = None,
    ) -> tuple[float, float]:
        """
        Calcula las probabilidades de Over/Under para una línea de goles.

        Args:
            lambda_local: Goles esperados del local.
            lambda_visitante: Goles esperados del visitante.
            linea: Línea de goles (2.5 es la más común).
            rho: Factor Dixon-Coles.

        Returns:
            Tupla (prob_over, prob_under).
        """
        matriz = self.calcular_matriz(lambda_local, lambda_visitante, rho)

        p_over = 0.0
        for i in range(matriz.shape[0]):
            for j in range(matriz.shape[1]):
                if i + j > linea:
                    p_over += matriz[i, j]

        p_under = 1.0 - p_over
        return (float(p_over), float(p_under))

    def calcular_btts(
        self,
        lambda_local: float,
        lambda_visitante: float,
        rho: Optional[float] = None,
    ) -> tuple[float, float]:
        """
        Calcula las probabilidades de "Ambos Marcan" (BTTS).

        Args:
            lambda_local: Goles esperados del local.
            lambda_visitante: Goles esperados del visitante.
            rho: Factor Dixon-Coles.

        Returns:
            Tupla (prob_si, prob_no).
        """
        matriz = self.calcular_matriz(lambda_local, lambda_visitante, rho)

        # BTTS Sí = ambos equipos marcan al menos 1 gol
        p_si = 0.0
        for i in range(1, matriz.shape[0]):
            for j in range(1, matriz.shape[1]):
                p_si += matriz[i, j]

        p_no = 1.0 - p_si
        return (float(p_si), float(p_no))

    def calcular_score_exacto(
        self,
        lambda_local: float,
        lambda_visitante: float,
        goles_local: int,
        goles_visitante: int,
        rho: Optional[float] = None,
    ) -> float:
        """
        Calcula la probabilidad de un marcador exacto.

        Args:
            lambda_local: Goles esperados del local.
            lambda_visitante: Goles esperados del visitante.
            goles_local: Goles exactos del local.
            goles_visitante: Goles exactos del visitante.
            rho: Factor Dixon-Coles.

        Returns:
            Probabilidad del marcador exacto.
        """
        if goles_local > self.max_goles or goles_visitante > self.max_goles:
            return 0.0

        matriz = self.calcular_matriz(lambda_local, lambda_visitante, rho)
        return float(matriz[goles_local, goles_visitante])

    def calcular_todos_los_mercados(
        self,
        lambda_local: float,
        lambda_visitante: float,
        rho: Optional[float] = None,
    ) -> dict:
        """
        Calcula todos los mercados principales de una vez.

        Returns:
            Diccionario con todas las probabilidades organizadas por mercado.
        """
        p1x2 = self.calcular_1x2(lambda_local, lambda_visitante, rho)
        p_over25, p_under25 = self.calcular_over_under(
            lambda_local, lambda_visitante, 2.5, rho
        )
        p_over15, p_under15 = self.calcular_over_under(
            lambda_local, lambda_visitante, 1.5, rho
        )
        p_over35, p_under35 = self.calcular_over_under(
            lambda_local, lambda_visitante, 3.5, rho
        )
        p_btts_si, p_btts_no = self.calcular_btts(
            lambda_local, lambda_visitante, rho
        )

        return {
            "1x2": {
                "local": p1x2.local,
                "empate": p1x2.empate,
                "visitante": p1x2.visitante,
            },
            "over_under": {
                "over_1_5": p_over15,
                "under_1_5": p_under15,
                "over_2_5": p_over25,
                "under_2_5": p_under25,
                "over_3_5": p_over35,
                "under_3_5": p_under35,
            },
            "ambos_marcan": {
                "si": p_btts_si,
                "no": p_btts_no,
            },
        }


# =============================================================================
# FUNCIONES DE CONVENIENCIA
# =============================================================================

def calcular_probabilidades(
    lambda_local: float,
    lambda_visitante: float,
    rho: float = RHO_DIXON_COLES,
) -> dict:
    """
    Función de conveniencia para calcular todas las probabilidades.

    Args:
        lambda_local: Goles esperados del local.
        lambda_visitante: Goles esperados del visitante.
        rho: Factor Dixon-Coles.

    Returns:
        Diccionario con todas las probabilidades.
    """
    modelo = PoissonBivariante(rho=rho)
    return modelo.calcular_todos_los_mercados(lambda_local, lambda_visitante)


__all__ = [
    "PoissonBivariante",
    "ParametrosPartido",
    "Probabilidades1X2",
    "calcular_probabilidades",
    "MAX_GOLES",
    "RHO_DIXON_COLES",
]