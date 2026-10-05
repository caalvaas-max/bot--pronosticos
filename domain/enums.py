"""
Enums del dominio de pronósticos deportivos.

Este módulo define todos los tipos enumerados que representan conceptos
del negocio. Usar enums previene errores por strings mágicos y facilita
la validación con Pydantic.
"""
from enum import Enum


# =============================================================================
# RESULTADOS Y MERCADOS
# =============================================================================

class Resultado(str, Enum):
    """Resultado final de un partido."""
    LOCAL = "local"
    EMPATE = "empate"
    VISITANTE = "visitante"
    
    def __str__(self) -> str:
        return self.value


class Mercado(str, Enum):
    """Tipos de mercado de apuestas disponibles."""
    UNO_X_DOS = "1x2"
    DOBLE_OPORTUNIDAD = "doble_oportunidad"
    OVER_UNDER = "over_under"
    AMBOS_MARCAN = "ambos_marcan"
    CORNERS = "corners"
    TARJETAS = "tarjetas"
    SCORE_EXACTO = "score_exacto"
    HANDICAP = "handicap"
    GOLES_TOTALES = "goles_totales"
    GOLEADOR = "goleador"


class DireccionLinea(str, Enum):
    """Dirección de una línea over/under."""
    OVER = "over"
    UNDER = "under"


# =============================================================================
# ESTADOS DE EVENTOS Y PRONÓSTICOS
# =============================================================================

class EstadoEvento(str, Enum):
    """Estado temporal de un evento deportivo."""
    PROGRAMADO = "programado"
    EN_VIVO = "en_vivo"
    FINALIZADO = "finalizado"
    POSTPUESTO = "postpuesto"
    CANCELADO = "cancelado"


class EstadoPronostico(str, Enum):
    """Estado de seguimiento de un pronóstico emitido."""
    PENDIENTE = "pendiente"
    ACERTADO = "acertado"
    FALLADO = "fallado"
    NULO = "nulo"


class TipoApuesta(str, Enum):
    """Tipo de apuesta emitida por el bot."""
    INDIVIDUAL = "individual"
    COMBINADA = "combinada"


# =============================================================================
# NIVELES Y CONFIANZA
# =============================================================================

class Confianza(str, Enum):
    """Nivel de confianza en un pronóstico."""
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    
    @classmethod
    def desde_probabilidad(cls, prob: float) -> "Confianza":
        """Determina el nivel de confianza según la probabilidad del modelo."""
        if prob >= 0.70:
            return cls.ALTA
        elif prob >= 0.55:
            return cls.MEDIA
        return cls.BAJA


class NivelRiesgo(str, Enum):
    """Perfil de riesgo del usuario o de la apuesta."""
    CONSERVADOR = "conservador"
    MODERADO = "moderado"
    AGRESIVO = "agresivo"


# =============================================================================
# ENTORNO Y COMPETICIÓN
# =============================================================================

class Entorno(str, Enum):
    """Entorno de ejecución."""
    DESARROLLO = "desarrollo"
    PRODUCCION = "produccion"
    TESTING = "testing"


class TipoCompeticion(str, Enum):
    """Tipo de competición donde se juega el partido."""
    LIGA = "liga"
    COPA = "copa"
    AMISTOSO = "amistoso"
    ELIMINATORIA = "eliminatoria"
    SUPERCOPA = "supercopa"
    CONTINENTAL = "continental"


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "Resultado",
    "Mercado",
    "DireccionLinea",
    "EstadoEvento",
    "EstadoPronostico",
    "TipoApuesta",
    "Confianza",
    "NivelRiesgo",
    "Entorno",
    "TipoCompeticion",
]