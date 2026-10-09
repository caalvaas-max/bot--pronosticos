"""Funciones auxiliares comunes."""
from __future__ import annotations
import re
from datetime import datetime
from typing import Optional

def limpiar_nombre_equipo(nombre: str) -> str:
    if not nombre:
        return ""
    nombre = re.sub(r"\s+", " ", nombre)
    return nombre.strip()

def formatear_fecha(fecha: Optional[datetime]) -> str:
    if fecha is None:
        return "Sin fecha"
    return fecha.strftime("%d/%m/%Y %H:%M")

def porcentaje(valor: float) -> str:
    return f"{valor * 100:.1f}%"

def redondear(valor: float, decimales: int = 2) -> float:
    return round(valor, decimales)

def calcular_probabilidad_implicita(cuota: float) -> float:
    if cuota <= 1.0:
        return 0.0
    return 1.0 / cuota

def calcular_valor_esperado(prob: float, cuota: float) -> float:
    return (prob * cuota) - 1.0

__all__ = [
    "limpiar_nombre_equipo",
    "formatear_fecha",
    "porcentaje",
    "redondear",
    "calcular_probabilidad_implicita",
    "calcular_valor_esperado",
]
