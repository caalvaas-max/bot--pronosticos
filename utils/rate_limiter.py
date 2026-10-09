"""Control de rate limiting para APIs externas."""
from __future__ import annotations
import logging
from datetime import date, datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class LimiteAPI:
    nombre: str
    max_por_dia: int
    max_por_minuto: int = 60
    usados_hoy: int = 0
    fecha_actual: date = field(default_factory=date.today)
    ultima_peticion: datetime = field(default_factory=datetime.now)

class RateLimiter:
    def __init__(self):
        self.limites: dict[str, LimiteAPI] = {}

    def registrar(self, nombre: str, max_por_dia: int, max_por_minuto: int = 60):
        self.limites[nombre] = LimiteAPI(
            nombre=nombre,
            max_por_dia=max_por_dia,
            max_por_minuto=max_por_minuto,
        )

    def _actualizar_fecha(self, lim: LimiteAPI):
        hoy = date.today()
        if lim.fecha_actual != hoy:
            lim.usados_hoy = 0
            lim.fecha_actual = hoy

    def puede_consultar(self, nombre: str) -> bool:
        lim = self.limites.get(nombre)
        if not lim:
            return True
        self._actualizar_fecha(lim)
        return lim.usados_hoy < lim.max_por_dia

    def registrar_uso(self, nombre: str):
        lim = self.limites.get(nombre)
        if not lim:
            return
        self._actualizar_fecha(lim)
        lim.usados_hoy += 1
        lim.ultima_peticion = datetime.now()

    def restantes(self, nombre: str) -> int:
        lim = self.limites.get(nombre)
        if not lim:
            return -1
        self._actualizar_fecha(lim)
        return max(0, lim.max_por_dia - lim.usados_hoy)

__all__ = ["RateLimiter", "LimiteAPI"]
