"""Orquestador Definitivo con Guardado en Base de Datos."""
from __future__ import annotations
import logging
import os
import unicodedata
import datetime
import pytz
from dataclasses import dataclass, field
from typing import Optional
import httpx

from agent.validacion import validar_texto
from models.poisson_bivariante import PoissonBivariante
from models.goles import calcular_lambda
from models.pi_ratings import PiRatings
from models.ensemble import combinar_1x2
from auditoria.guardar import GuardadorPronosticos, DatosPronostico

logger = logging.getLogger(__name__)
BASE_URL = "https://sports.bzzoiro.com/api/v2"

def normalizar(texto: str) -> str:
    if not texto: return ""
    texto = texto.lower().strip()
    texto = texto.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    for prefijo in ['as ', 'fc ', 'real ', 'cd ', 'ca ', 'club ']:
        if texto.startswith(prefijo):
            texto = texto.replace(prefijo, '', 1)
    return texto.strip()

@dataclass
class RespuestaPronostico:
    local: str
    visitante: str
    hora: str
    probabilidades: dict
    mercados: dict = field(default_factory=dict)
    confianza: str = "media"

class Orquestador:
    def __init__(self, bankroll=1000.0):
        self.api_key = os.getenv("BZZOIRO_API_KEY", "")
        self.bankroll = bankroll

    async def obtener_partidos_disponibles(self, limite: int = 20) -> list:
        headers = {"Authorization": f"Token {self.api_key}", "User-Agent": "Mozilla/5.0"}
        ahora = datetime.datetime.now(pytz.timezone('America/Lima'))
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.get(f"{BASE_URL}/predictions/", headers=headers, params={"limit": limite})
                if r.status_code == 200:
                    data = r.json()
                    partidos = []
                    for item in data.get("results", []):
                        ev = item.get("event", {})
                        h = ev.get("home_team", "")
                        a = ev.get("away_team", "")
                        hora_str, dt_peru = self._extraer_hora(ev)

                        if dt_peru and dt_peru < ahora:
                            continue

                        if h and a:
                            liga_nombre = ev.get("league", {}).get("name", "Otra Liga") if isinstance(ev.get("league"), dict) else str(ev.get("league", "Otra Liga"))
                            genero = str(ev.get("gender", "M"))
                            partidos.append({
                                "texto": f"{h} vs {a}", 
                                "hora": hora_str, 
                                "liga": liga_nombre, 
                                "genero": genero
                            })
                    return partidos
        except Exception as e:
            logger.error(f"Error obteniendo partidos: {e}")
            return []

    async def _consultar_bzzoiro(self, local: str, visitante: str) -> dict:
        if not self.api_key: return {"error": "BZZOIRO_API_KEY vacía"}
        headers = {"Authorization": f"Token {self.api_key}", "User-Agent": "Mozilla/5.0"}
        loc_norm = normalizar(local)
        vis_norm = normalizar(visitante)
        try:
            async with httpx.AsyncClient(timeout=20.0) as c:
                for offset in range(0, 250, 50):
                    r = await c.get(f"{BASE_URL}/predictions/", headers=headers, params={"limit": 50, "offset": offset})
                    if r.status_code != 200: return {"error": f"API Status {r.status_code}"}
                    data = r.json()
                    results = data.get("results", [])
                    if not results: break
                    for item in results:
                        ev = item.get("event", {})
                        h_name = str(ev.get("home_team", ""))
                        a_name = str(ev.get("away_team", ""))
                        if normalizar(h_name) == loc_norm and normalizar(a_name) == vis_norm:
                            return item
        except Exception as e:
            return {"error": str(e)}
        return {"error": "Partido no encontrado"}

    def _extraer_hora(self, ev: dict) -> tuple:
        fecha_str = ev.get("date") or ev.get("start_time") or ev.get("kickoff")
        if not fecha_str: return "?", None
        try:
            fecha_str = str(fecha_str).replace('Z', '+00:00')
            dt = datetime.datetime.fromisoformat(fecha_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.UTC)
            dt_peru = dt.astimezone(pytz.timezone('America/Lima'))
            return dt_peru.strftime("%H:%M"), dt_peru
        except:
            return "?", None

    async def generar_pronostico(self, local: str, visitante: str) -> Optional[RespuestaPronostico]:
        data = await self._consultar_bzzoiro(local, visitante)
        if "error" in data: return None
        
        try:
            h = data.get("event", {}).get("home_team", local)
            a = data.get("event", {}).get("away_team", visitante)
            hora_str, _ = self._extraer_hora(data.get("event", {}))
            
            probs = {"1": 0.33, "X": 0.33, "2": 0.33}
            if "predictions" in data and isinstance(data["predictions"], dict):
                p = data["predictions"]
                probs = {"1": float(p.get("home_win", 0.33)), "X": float(p.get("draw", 0.33)), "2": float(p.get("away_win", 0.33))}
            
            return RespuestaPronostico(
                local=h,
                visitante=a,
                hora=hora_str,
                probabilidades=probs,
                confianza="alta"
            )
        except Exception as e:
            logger.error(f"Error generando pronostico: {e}")
            return None