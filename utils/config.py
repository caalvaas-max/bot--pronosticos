"""Configuracion centralizada del bot."""
from __future__ import annotations
import os
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class Config:
    telegram_token: str = ""
    bzzoiro_api_key: str = ""
    database_url: str = "sqlite:///bot.db"
    log_level: str = "INFO"
    debug: bool = False
    bankroll_inicial: float = 1000.0
    kelly_fraccion: float = 0.25
    ev_minimo: float = 0.03
    max_goles: int = 8
    rho_dixon_coles: float = -0.10

def cargar_config() -> Config:
    return Config(
        telegram_token=os.getenv("TELEGRAM_TOKEN", ""),
        bzzoiro_api_key=os.getenv("BZZOIRO_API_KEY", ""),
        database_url=os.getenv("DATABASE_URL", "sqlite:///bot.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        debug=os.getenv("DEBUG", "false").lower() == "true",
    )

__all__ = ["Config", "cargar_config"]
