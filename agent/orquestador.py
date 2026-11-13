"""Orquestador Definitivo - Mejor opción por mercado."""
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

    def _elegir_mejor_opcion(self, prob_over: float, prob_under: float, linea: float) -> tuple[float, str]:
        if prob_over >= prob_under:
            return prob_over, f"Over {linea} ({prob_over*100:.1f}%)"
        else:
            return prob_under, f"Under {linea} ({prob_under*100:.1f}%)"

    def _calcular_mercados_goles(self, lambda_local: float, lambda_visitante: float, max_goles: int = 10) -> dict:
        prob_local = poisson.pmf(np.arange(max_goles + 1), lambda_local)
        prob_visitante = poisson.pmf(np.arange(max_goles + 1), lambda_visitante)
        matriz = np.outer(prob_local, prob_visitante)

        prob_1 = np.sum(np.tril(matriz, -1))
        prob_x = np.sum(np.diag(matriz))
        prob_2 = np.sum(np.triu(matriz, 1))

        total_goles = np.add.outer(np.arange(max_goles + 1), np.arange(max_goles + 1))
        
        opt_15 = self._elegir_mejor_opcion(np.sum(matriz[total_goles > 1.5]), 1 - np.sum(matriz[total_goles > 1.5]), 1.5)
        opt_25 = self._elegir_mejor_opcion(np.sum(matriz[total_goles > 2.5]), 1 - np.sum(matriz[total_goles > 2.5]), 2.5)
        opt_35 = self._elegir_mejor_opcion(np.sum(matriz[total_goles > 3.5]), 1 - np.sum(matriz[total_goles > 3.5]), 3.5)
        mejor_goles = max([opt_15, opt_25, opt_35], key=lambda x: x[0])

        p_btts = np.sum(matriz[1:, 1:])

        return {
            "1X2": {"1": prob_1, "X": prob_x, "2": prob_2},
            "Goles": mejor_goles[1],
            "BTTS": {"Sí": p_btts, "No": 1 - p_btts},
            "Doble Oportunidad": {"1X": prob_1 + prob_x, "12": prob_1 + prob_2, "X2": prob_x + prob_2},
        }

    def _calcular_mercados_corners(self, media_local: float, media_visitante: float) -> dict:
        media_total = media_local + media_visitante
        prob_total = nbinom.pmf(np.arange(25), media_total, 0.5)

        opt_85 = self._elegir_mejor_opcion(np.sum(prob_total[9:]), 1 - np.sum(prob_total[9:]), 8.5)
        opt_95 = self._elegir_mejor_opcion(np.sum(prob_total[10:]), 1 - np.sum(prob_total[10:]), 9.5)
        opt_105 = self._elegir_mejor_opcion(np.sum(prob_total[11:]), 1 - np.sum(prob_total[11:]), 10.5)
        mejor_corner = max([opt_85, opt_95, opt_105], key=lambda x: x[0])

        return {"Córners": mejor_corner[1]}

    def _calcular_mercados_tarjetas(self, media_local: float, media_visitante: float, media_arbitro: float) -> dict:
        media_total = (media_local + media_visitante + media_arbitro) / 3
        prob_tarjetas = poisson.pmf(np.arange(10), media_total)

        opt_25 = self._elegir_mejor_opcion(np.sum(prob_tarjetas[3:]), 1 - np.sum(prob_tarjetas[3:]), 2.5)
        opt_35 = self._elegir_mejor_opcion(np.sum(prob_tarjetas[4:]), 1 - np.sum(prob_tarjetas[4:]), 3.5)
        opt_45 = self._elegir_mejor_opcion(np.sum(prob_tarjetas[5:]), 1 - np.sum(prob_tarjetas[5:]), 4.5)
        mejor_tarjeta = max([opt_25, opt_35, opt_45], key=lambda x: x[0])

        return {"Tarjetas": mejor_tarjeta[1]}

    def _calcular_mercados_tiros(self, media_local: float, media_visitante: float) -> dict:
        media_total = media_local + media_visitante
        prob_tiros = poisson.pmf(np.arange(20), media_total)

        opt_85 = self._elegir_mejor_opcion(np.sum(prob_tiros[9:]), 1 - np.sum(prob_tiros[9:]), 8.5)
        opt_95 = self._elegir_mejor_opcion(np.sum(prob_tiros[10:]), 1 - np.sum(prob_tiros[10:]), 9.5)
        opt_105 = self._elegir_mejor_opcion(np.sum(prob_tiros[11:]), 1 - np.sum(prob_tiros[11:]), 10.5)
        mejor_tiro = max([opt_85, opt_95, opt_105], key=lambda x: x[0])

        return {"Tiros": mejor_tiro[1]}

    async def generar_pronostico(self, local: str, visitante: str) -> Optional[RespuestaPronostico]:
        data = await self._consultar_bzzoiro(local, visitante)
        if "error" in data: return None
        
        try:
            h = data.get("event", {}).get("home_team", local)
            a = data.get("event", {}).get("away_team", visitante)
            hora_str, _ = self._extraer_hora(data.get("event", {}))
            
            probs = {"1": 0.33, "X": 0.33, "2": 0.33}
            lambda_local = 1.4
            lambda_visitante = 1.1
            
            if "predictions" in data and isinstance(data["predictions"], dict):
                p = data["predictions"]
                probs = {"1": float(p.get("home_win", 0.33)), "X": float(p.get("draw", 0.33)), "2": float(p.get("away_win", 0.33))}
            
            mercados = {}
            mercados.update(self._calcular_mercados_goles(lambda_local, lambda_visitante))
            mercados.update(self._calcular_mercados_corners(5.0, 4.0))
            mercados.update(self._calcular_mercados_tarjetas(2.0, 2.0, 4.0))
            mercados.update(self._calcular_mercados_tiros(12.0, 10.0))
            
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
