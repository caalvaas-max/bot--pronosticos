"""Sistema de cache con SQLite para APIs."""
from __future__ import annotations
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Optional
from sqlalchemy import String, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from data.db import Base, get_session, init_db

logger = logging.getLogger(__name__)

class CacheEntry(Base):
    __tablename__ = "cache"
    clave: Mapped[str] = mapped_column(String(200), primary_key=True)
    valor: Mapped[str] = mapped_column(Text)
    actualizado: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class Cache:
    def __init__(self, horas: int = 24):
        self.horas = horas
        init_db()

    def get(self, clave: str) -> Optional[Any]:
        with get_session() as s:
            e = s.get(CacheEntry, clave)
            if not e:
                return None
            if datetime.now() - e.actualizado > timedelta(hours=self.horas):
                return None
            return json.loads(e.valor)

    def set(self, clave: str, valor: Any):
        with get_session() as s:
            e = s.get(CacheEntry, clave)
            if e:
                e.valor = json.dumps(valor, default=str)
                e.actualizado = datetime.now()
            else:
                s.add(CacheEntry(clave=clave, valor=json.dumps(valor, default=str)))
            s.commit()

__all__ = ["Cache", "CacheEntry"]
