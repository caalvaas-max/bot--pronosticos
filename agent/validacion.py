"""Validacion de entradas del usuario."""
from __future__ import annotations
import re
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class ConsultaPartido:
    local: str
    visitante: str
    fecha: Optional[datetime] = None

class ValidacionError(Exception):
    pass

def validar_texto(texto: str) -> ConsultaPartido:
    if not texto or not texto.strip():
        raise ValidacionError("La consulta esta vacia")

    texto = texto.strip()
    patrones = [
        r"^(.+?)\s+(?:vs|VS|v\.|contra)\s+(.+?)$",
        r"^(.+?)\s+-\s+(.+?)$",
    ]

    for patron in patrones:
        m = re.match(patron, texto, re.IGNORECASE)
        if m:
            local = m.group(1).strip()
            visitante = m.group(2).strip()
            if len(local) < 2 or len(visitante) < 2:
                raise ValidacionError("Nombre de equipo muy corto")
            return ConsultaPartido(local=local, visitante=visitante)

    raise ValidacionError(
        "Formato invalido. Usa: 'Equipo Local vs Equipo Visitante'"
    )

def validar_fecha(fecha: Optional[datetime]) -> Optional[datetime]:
    if fecha is None:
        return None
    ahora = datetime.now()
    if fecha < ahora - timedelta(days=365):
        raise ValidacionError("Fecha muy antigua")
    if fecha > ahora + timedelta(days=365):
        raise ValidacionError("Fecha muy futura")
    return fecha

__all__ = ["validar_texto", "validar_fecha", "ConsultaPartido", "ValidacionError"]
