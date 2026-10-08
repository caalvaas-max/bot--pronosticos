"""Conexion a base de datos con SQLAlchemy."""
from __future__ import annotations
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DB_PATH = Path("bot.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

class Base(DeclarativeBase):
    pass

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(engine)

def get_session():
    return SessionLocal()

__all__ = ["engine", "SessionLocal", "Base", "init_db", "get_session"]
