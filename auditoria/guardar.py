"""Guarda pronosticos con contexto completo para auditoria."""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from data.db import Base, get_session, init_db

logger = logging.getLogger(__name__)

class PronosticoDB(Base):
    __tablename__ = "pronosticos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evento_id: Mapped[str] = mapped_column(String(50), index=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    liga: Mapped[str] = mapped_column(String(100))
    local: Mapped[str] = mapped_column(String(100))
    visitante: Mapped[str] = mapped_column(String(100))
    mercado: Mapped[str] = mapped_column(String(50))
    seleccion: Mapped[str] = mapped_column(String(50))
    probabilidad: Mapped[float] = mapped_column(Float)
    cuota: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confianza: Mapped[str] = mapped_column(String(20))
    datos_contexto: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resultado: Mapped[str] = mapped_column(String(20), default="PENDIENTE")
    goles_local: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goles_visitante: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    brier_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

@dataclass
class DatosPronostico:
    evento_id: str
    liga: str
    local: str
    visitante: str
    mercado: str
    seleccion: str
    probabilidad: float
    cuota: Optional[float] = None
    confianza: str = "media"
    contexto: dict = None

class GuardadorPronosticos:
    def __init__(self):
        init_db()

    def guardar(self, datos: DatosPronostico) -> int:
        with get_session() as s:
            p = PronosticoDB(
                evento_id=datos.evento_id,
                liga=datos.liga,
                local=datos.local,
                visitante=datos.visitante,
                mercado=datos.mercado,
                seleccion=datos.seleccion,
                probabilidad=datos.probabilidad,
                cuota=datos.cuota,
                confianza=datos.confianza,
                datos_contexto=json.dumps(datos.contexto or {}, default=str),
            )
            s.add(p)
            s.commit()
            return p.id

    def pendientes(self) -> list:
        with get_session() as s:
            return s.query(PronosticoDB).filter(PronosticoDB.resultado == "PENDIENTE").all()

__all__ = ["GuardadorPronosticos", "DatosPronostico", "PronosticoDB"]
