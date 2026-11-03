"""Conexion a base de datos con pg8000 (sin compilacion)."""
from __future__ import annotations
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot.db")

# Si es una URL de PostgreSQL, forzamos el uso de pg8000
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+pg8000" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

class Base(DeclarativeBase):
    pass

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    try:
        Base.metadata.create_all(engine)
    except Exception as e:
        logger.error(f"Error creando tablas: {e}")

def get_session():
    return SessionLocal()

__all__ = ["engine", "SessionLocal", "Base", "init_db", "get_session"]
