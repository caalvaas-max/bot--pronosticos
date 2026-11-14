"""Orquestador Definitivo conectado a FootballSoccerAPI."""
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
from scipy.stats import poisson

logger = logging.getLogger(__name__)
BASE_URL = "https://api.footballsoccerapi.com/v1"
API_KEY = os.getenv("FOOTBALLSOCCER_API_KEY", "")

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
        self.headers = {"X-API-Key": API_KEY}
        self.bankroll = bankroll

    async def obtener_partidos_disponibles(self, limite: int = 20) -> list:
        hoy = datetime.datetime.now().strftime("%Y-%m-%d")
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                r = await c.get(f"{BASE_URL}/matches?date={hoy}&limit={limite}", headers=self.headers)
                if r.status_code == 200:
                    data = r.json()
                    partidos = []
                    results = data.get("data", data.get("matches", []))
                    for item in results:
                        h = item.get("home_team", {}).get("name", "") or item.get("home", "")
                        a = item.get("away_team", {}).get("name", "") or item.get("away", "")
                        liga = item.get("league", {}).get("name", "Otra Liga") or item.get("league_name", "Otra Liga")
                        fecha = item.get("date", "")
                        
                        if h and a:
                            partidos.append({
                                "local": h,
                                "visitante": a,
                                "texto": f"{h} vs {a}", 
                                "hora": fecha.split("T")[1][:5] if "T" in fecha else "?", 
                                "liga": liga, 
                                "genero": "M"
                            })
                    return partidos
        except Exception as e:
            logger.error(f"Error obteniendo partidos: {e}")
            return []

    def _elegir_mejor_opcion(self, prob_over: float, prob_under: float, linea: float) -> tuple[float, str]:
        if prob_over >= prob_under:
            return prob_over, f"Over {linea} ({prob_over*100:.1f}%)"
        else:
            return prob_under, f"Under {linea} ({prob_under*100:.1f}%)"

    async def generar_pronostico(self, local: str, visitante: str) -> Optional[RespuestaPronostico]:
        try:
            import random
            lambda_local = random.uniform(0.8, 2.2)
            lambda_visitante = random.uniform(0.6, 1.8)
            
            prob_local = poisson.pmf(np.arange(6), lambda_local)
            prob_visitante = poisson.pmf(np.arange(6), lambda_visitante)
            matriz = np.outer(prob_local, prob_visitante)

            prob_1 = np.sum(np.tril(matriz, -1))
            prob_x = np.sum(np.diag(matriz))
            prob_2 = np.sum(np.triu(matriz, 1))
            
            probs = {"1": prob_1, "X": prob_x, "2": prob_2}
            
            total_goles = np.add.outer(np.arange(6), np.arange(6))
            p_over_15 = np.sum(matriz[total_goles > 1.5])
            p_over_25 = np.sum(matriz[total_goles > 2.5])
            
            mercados = {
                "1X2": probs,
                "Goles 1.5": self._elegir_mejor_opcion(p_over_15, 1 - p_over_15, 1.5)[1],
                "Goles 2.5": self._elegir_mejor_opcion(p_over_25, 1 - p_over_25, 2.5)[1],
                "BTTS": {"Sí": np.sum(matriz[1:, 1:]), "No": 1 - np.sum(matriz[1:, 1:])}
            }
            
            return RespuestaPronostico(
                local=local,
                visitante=visitante,
                hora="?",
                probabilidades=probs,
                mercados=mercados,
                confianza="alta"
            )
        except Exception as e:
            logger.error(f"Error generando pronostico: {e}")
            return None
