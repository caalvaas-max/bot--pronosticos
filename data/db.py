"""Conexion a base de datos con diagnostico."""
from __future__ import annotations
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("❌ CRÍTICO: La variable DATABASE_URL no está configurada en Railway.")
    DATABASE_URL = "sqlite:///bot.db"
else:
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # Ocultar la contraseña en los logs por seguridad
    try:
        if "@" in DATABASE_URL:
            parte_segura = DATABASE_URL.split('@')[0].split(':')[0]
            url_log = parte_segura + ":***@" + DATABASE_URL.split('@')[1]
        else:
            url_log = DATABASE_URL
    except:
        url_log = "URL_MAL_FORMADA"

    logger.info(f"🔗 CONECTANDO A DB: {url_log}")

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
