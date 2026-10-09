"""Lee texto de imagenes de partidos usando OCR."""
from __future__ import annotations
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

@dataclass
class InfoPartido:
    local: str
    visitante: str
    liga: Optional[str] = None
    fecha: Optional[str] = None
    exito: bool = True
    error: Optional[str] = None

class LectorOCR:
    def __init__(self):
        self.reader = None

    def _inicializar(self):
        if self.reader is None:
            try:
                import easyocr
                self.reader = easyocr.Reader(["es", "en"], gpu=False)
            except ImportError:
                logger.warning("easyocr no instalado")
                self.reader = False

    def extraer_texto(self, ruta: str) -> str:
        self._inicializar()
        if not self.reader:
            return ""
        try:
            resultados = self.reader.readtext(ruta)
            return " ".join(r[1] for r in resultados)
        except Exception as e:
            logger.error(f"Error OCR: {e}")
            return ""

    def extraer_partido(self, ruta: str) -> InfoPartido:
        texto = self.extraer_texto(ruta)
        if not texto:
            return InfoPartido(local="", visitante="", exito=False, error="OCR fallo")

        patrones = [
            r"([A-Za-z\s]+?)\s+(?:vs|VS|v\.|contra)\s+([A-Za-z\s]+)",
            r"([A-Za-z\s]+?)\s+-\s+([A-Za-z\s]+)",
        ]

        for patron in patrones:
            m = re.search(patron, texto)
            if m:
                return InfoPartido(
                    local=m.group(1).strip(),
                    visitante=m.group(2).strip(),
                )

        return InfoPartido(local="", visitante="", exito=False, error="Formato no detectado")

__all__ = ["LectorOCR", "InfoPartido"]
