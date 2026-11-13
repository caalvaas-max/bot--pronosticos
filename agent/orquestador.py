"""Orquestador Definitivo con Selección Automática de Over/Under."""
from __future__ import annotations
import logging
import os
import unicodedata
import datetime
import pytz
from dataclasses import dataclass, field
from typing import Optional
import httpx
import numpy as np
from scipy.stats import poisson, nbinom

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
                            liga_nombre = ev.get("league_name", "Otra Liga")
                            genero = str(ev.get("gender", "M"))
                            partidos.append({
                                "local": h,
                                "visitante": a,
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
        fecha_str = ev.get("event_date")
        if not fecha_str: return "?", None
        try:
            fecha_str = str(fecha_str).replace('Z', '+00:00')
            dt = datetime.datetime.fromisoformat(fecha_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.UTC)
            dt_peru = dt.astimezone(pytz.timezone('America/Lima'))
            return dt_peru.strftime("%H:%M"), dt_peru
        except Exception as e:
            return "?", None

    def _elegir_mejor_opcion(self, prob_over: float, prob_under: float, linea: float) -> str:
        if prob_over >= prob_under:
            return f"Over {linea} ({prob_over*100:.1f}%)"
        else:
            return f"Under {linea} ({prob_under*100:.1f}%)"

    def _calcular_mercados_goles(self, lambda_local: float, lambda_visitante: float, max_goles: int = 10) -> dict:
        prob_local = poisson.pmf(np.arange(max_goles + 1), lambda_local)
        prob_visitante = poisson.pmf(np.arange(max_goles + 1), lambda_visitante)
        matriz = np.outer(prob_local, prob_visitante)

        prob_1 = np.sum(np.tril(matriz, -1))
        prob_x = np.sum(np.diag(matriz))
        prob_2 = np.sum(np.triu(matriz, 1))

        total_goles = np.add.outer(np.arange(max_goles + 1), np.arange(max_goles + 1))
        
        p_over_15 = np.sum(matriz[total_goles > 1.5])
        p_over_25 = np.sum(matriz[total_goles > 2.5])
        p_over_35 = np.sum(matriz[total_goles > 3.5])
        
        p_btts = np.sum(matriz[1:, 1:])

        return {
            "1X2": {"1": prob_1, "X": prob_x, "2": prob_2},
            "Goles 1.5": self._elegir_mejor_opcion(p_over_15, 1 - p_over_15, 1.5),
            "Goles 2.5": self._elegir_mejor_opcion(p_over_25, 1 - p_over_25, 2.5),
            "Goles 3.5": self._elegir_mejor_opcion(p_over_35, 1 - p_over_35, 3.5),
            "BTTS": {"Sí": p_btts, "No": 1 - p_btts},
            "Doble Oportunidad": {"1X": prob_1 + prob_x, "12": prob_1 + prob_2, "X2": prob_x + prob_2},
        }

    def _calcular_mercados_corners(self, media_local: float, media_visitante: float, max_corners: int = 20) -> dict:
        media_total = media_local + media_visitante
        r_total = media_total
        p_total = 0.5
        prob_total = nbinom.pmf(np.arange(max_corners * 2 + 1), r_total, p_total)

        p_over_85 = np.sum(prob_total[9:])
        p_over_95 = np.sum(prob_total[10:])
        p_over_105 = np.sum(prob_total[11:])

        return {
            "Córners 8.5": self._elegir_mejor_opcion(p_over_85, 1 - p_over_85, 8.5),
            "Córners 9.5": self._elegir_mejor_opcion(p_over_95, 1 - p_over_95, 9.5),
            "Córners 10.5": self._elegir_mejor_opcion(p_over_105, 1 - p_over_105, 10.5),
        }

    def _calcular_mercados_tarjetas(self, media_local: float, media_visitante: float, media_arbitro: float, max_tarjetas: int = 10) -> dict:
        media_total = (media_local + media_visitante + media_arbitro) / 3
        prob_tarjetas = poisson.pmf(np.arange(max_tarjetas + 1), media_total)

        p_over_25 = np.sum(prob_tarjetas[3:])
        p_over_35 = np.sum(prob_tarjetas[4:])
        p_over_45 = np.sum(prob_tarjetas[5:])

        return {
            "Tarjetas 2.5": self._elegir_mejor_opcion(p_over_25, 1 - p_over_25, 2.5),
            "Tarjetas 3.5": self._elegir_mejor_opcion(p_over_35, 1 - p_over_35, 3.5),
            "Tarjetas 4.5": self._elegir_mejor_opcion(p_over_45, 1 - p_over_45, 4.5),
        }

    def _calcular_mercados_tiros(self, media_local: float, media_visitante: float, max_tiros: int = 20) -> dict:
        media_total = media_local + media_visitante
        prob_tiros = poisson.pmf(np.arange(max_tiros + 1), media_total)

        p_over_85 = np.sum(prob_tiros[9:])
        p_over_95 = np.sum(prob_tiros[10:])
        p_over_105 = np.sum(prob_tiros[11:])

        return {
            "Tiros 8.5": self._elegir_mejor_opcion(p_over_85, 1 - p_over_85, 8.5),
            "Tiros 9.5": self._elegir_mejor_opcion(p_over_95, 1 - p_over_95, 9.5),
            "Tiros 10.5": self._elegir_mejor_opcion(p_over_105, 1 - p_over_105, 10.5),
        }

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
            
            lambda_local = 1.4
            lambda_visitante = 1.1
            if "expected_goals" in data:
                xg = data["expected_goals"]
                lambda_local = xg.get("home", lambda_local)
                lambda_visitante = xg.get("away", lambda_visitante)
            
            mercados = {}
            mercados.update(self._calcular_mercados_goles(lambda_local, lambda_visitante))
            mercados.update(self._calcular_mercados_corners(5.0, 4.0))
            mercados.update(self._calcular_mercados_tarjetas(2.0, 2.0, 4.0))
            mercados.update(self._calcular_mercados_tiros(12.0, 10.0))
            
            mercados["Goleadores"] = "NO RECOMENDADO"
            
            return RespuestaPronostico(
                local=h,
                visitante=a,
                hora=hora_str,
                probabilidades=probs,
                mercados=mercados,
                confianza="alta"
            )
        except Exception as e:
            logger.error(f"Error generando pronostico: {e}")
            return None
