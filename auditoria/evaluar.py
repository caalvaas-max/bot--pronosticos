"""Evalua pronosticos comparando con resultados reales."""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Optional
from data.db import get_session
from auditoria.guardar import PronosticoDB

logger = logging.getLogger(__name__)

class Evaluador:
    def __init__(self):
        pass

    def evaluar_partido(self, evento_id: str, goles_local: int, goles_visitante: int) -> int:
        with get_session() as s:
            pronosticos = s.query(PronosticoDB).filter(
                PronosticoDB.evento_id == evento_id,
                PronosticoDB.resultado == "PENDIENTE"
            ).all()

            for p in pronosticos:
                acertado = self._verificar(
                    p.mercado, p.seleccion, goles_local, goles_visitante
                )
                p.resultado = "ACERTADO" if acertado else "FALLADO"
                p.goles_local = goles_local
                p.goles_visitante = goles_visitante

                valor = 1.0 if acertado else 0.0
                p.brier_score = (p.probabilidad - valor) ** 2

            s.commit()
            return len(pronosticos)

    def _verificar(self, mercado: str, seleccion: str, gl: int, gv: int) -> bool:
        m = mercado.lower()
        s = seleccion.lower()

        if m == "1x2":
            if s == "local":
                return gl > gv
            elif s == "empate":
                return gl == gv
            elif s == "visitante":
                return gl < gv

        elif m in ("over_2_5", "over25"):
            return (gl + gv) > 2.5
        elif m in ("under_2_5", "under25"):
            return (gl + gv) < 2.5

        elif m in ("btts", "ambos_marcan"):
            ambos = gl > 0 and gv > 0
            return ambos if s == "si" else not ambos

        return False

__all__ = ["Evaluador"]
