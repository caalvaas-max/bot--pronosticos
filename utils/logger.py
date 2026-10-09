"""Configuracion centralizada de logs."""
from __future__ import annotations
import logging
import sys
from pathlib import Path

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "bot.log"

def configurar_logs(nivel: str = "INFO") -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)

    formato = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

    logger_root = logging.getLogger()
    logger_root.setLevel(getattr(logging, nivel.upper(), logging.INFO))

    if logger_root.handlers:
        logger_root.handlers.clear()

    consola = logging.StreamHandler(sys.stdout)
    consola.setFormatter(logging.Formatter(formato))
    logger_root.addHandler(consola)

    archivo = logging.FileHandler(LOG_FILE, encoding="utf-8")
    archivo.setFormatter(logging.Formatter(formato))
    logger_root.addHandler(archivo)

    return logger_root

def obtener_logger(nombre: str) -> logging.Logger:
    return logging.getLogger(nombre)

__all__ = ["configurar_logs", "obtener_logger", "LOG_FILE"]
