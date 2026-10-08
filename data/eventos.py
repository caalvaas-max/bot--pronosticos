"""Gestion de eventos y partidos."""
from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class Evento:
    evento_id: str
    liga: str
    local: str
    visitante: str
    fecha_hora: datetime
    estado: str = "programado"
    resultado_local: Optional[int] = None
    resultado_visitante: Optional[int] = None

def crear_desde_bzzoiro(data: dict) -> Optional[Evento]:
    try:
        return Evento(
            evento_id=str(data.get("id", "")),
            liga=data.get("league_name", "Desconocida"),
            local=data.get("home_team", ""),
            visitante=data.get("away_team", ""),
            fecha_hora=datetime.fromisoformat(
                data.get("start_time", datetime.now().isoformat())
            ),
        )
    except Exception as e:
        logger.error(f"Error creando evento: {e}")
        return None

__all__ = ["Evento", "crear_desde_bzzoiro"]
