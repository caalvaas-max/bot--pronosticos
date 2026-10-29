"""Orquestador Definitivo: Hándicap exacto, marcador dinámico y escáner de hora."""
from __future__ import annotations
import logging
import os
import unicodedata
from dataclasses import dataclass, field
from typing import Optional
import httpx

from agent.validacion import validar_texto
from models.poisson_bivariante import PoissonBivariante
from models.goles import calcular_lambda
from models.pi_ratings import PiRatings
from models.ensemble import combinar_1x2

logger = logging.getLogger(__name__)
BASE_URL = "https://sports.bzzoiro.com/api/v2"

def normalizar(texto: str) -> str:
    if not texto: return ""
    texto = texto.lower().strip()
    texto = texto.replace('ø', 'o').replace('å', 'a').replace('æ', 'ae')
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    for prefijo in ['as ', 'fc ', 'cf ', 'real ', 'cd ', 'ca ', 'club ']:
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
    marcador_top: str = ""
    marcador_prob: float = 0.0
    fuente: str = "APROX"

class Orquestador:
    def __init__(self, bankroll: float = 1000.0):
        self.poisson = PoissonBivariante()
        self.pi_ratings = PiRatings()
        self.api_key = os.getenv("BZZOIRO_API_KEY", "")

    def _extraer_hora(self, ev: dict) -> str:
        # Escáner de hora: busca cualquier cosa que parezca una hora (HH:MM)
        for key, val in ev.items():
            if isinstance(val, str) and "T" in val and len(val) >= 16:
                # Busca formato 2026-10-28T20:00:00Z
                try: return val[11:16]
                except: pass
            elif isinstance(val, str) and ":" in val and len(val) <= 5:
                # Busca formato 20:00
                return val
            elif isinstance(val, int) and val > 1600000000:
                # Busca formato timestamp UNIX
                import datetime
                try: return datetime.datetime.fromtimestamp(val).strftime("%H:%M")
                except: pass
        return ""

    async def obtener_partidos_disponibles(self, limite: int = 8) -> list:
        if not self.api_key: return []
        headers = {"Authorization": f"Token {self.api_key}", "User-Agent": "Mozilla/5.0"}
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
                        hora = self._extraer_hora(ev)
                        if h and a:
                            partidos.append({"texto": f"{h} vs {a}", "hora": hora})
                    return partidos
        except Exception as e:
            logger.error(f"Error obteniendo partidos: {e}")
        return []

    async def _consultar_bzzoiro(self, local: str, visitante: str) -> dict:
        if not self.api_key: return {"error": "BZZOIRO_API_KEY vacia"}
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
                        if (loc_norm in normalizar(h_name) or normalizar(h_name) in loc_norm) and \
                           (vis_norm in normalizar(a_name) or normalizar(a_name) in vis_norm):
                            return {"success": True, "data": item}
                return {"error": "No se encontró el partido."}
        except Exception as e:
            return {"error": f"Falla: {str(e)[:30]}"}

    async def procesar(self, texto: str, guardar: bool = True) -> RespuestaPronostico:
        consulta = validar_texto(texto)
        res = await self._consultar_bzzoiro(consulta.local, consulta.visitante)
        
        fuente = "APROX"
        probs_final = {}
        mercados_bzz = {}
        mejor_marcador = ""
        mejor_prob = 0.0
        hora_partido = ""

        if "success" in res:
            fuente = "BZZOIRO"
            ev_data = res["data"].get("event", {})
            hora_partido = self._extraer_hora(ev_data)
            mkts = res["data"].get("markets", {})
            
            # 1X2
            mr = mkts.get("match_result", {})
            if mr:
                probs_final = {
                    "local": float(mr.get("prob_home", 0)) / 100.0,
                    "empate": float(mr.get("prob_draw", 0)) / 100.0,
                    "visitante": float(mr.get("prob_away", 0)) / 100.0
                }
            
            # Goles y BTTS
            ou = mkts.get("over_under", {})
            if ou:
                mercados_bzz["over_15"] = float(ou.get("prob_over_15", 0)) / 100.0
                mercados_bzz["over_25"] = float(ou.get("prob_over_25", 0)) / 100.0
                mercados_bzz["over_35"] = float(ou.get("prob_over_35", 0)) / 100.0
            
            btts = mkts.get("btts", {})
            if btts:
                prob_yes = float(btts.get("prob_yes", 0)) / 100.0
                mercados_bzz["btts_si"] = prob_yes
                mercados_bzz["btts_no"] = 1.0 - prob_yes
            
            # Escáner de Marcador Top (Buscando llaves con "prob" o formato "1-1")
            score_mkt = mkts.get("score", {})
            for k, v in score_mkt.items():
                if k == "most_likely":
                    if isinstance(v, str) and "-" in v:
                        mejor_marcador = v
                        # Buscar su probabilidad en otra llave si existe
                        mejor_prob = float(score_mkt.get(f"prob_{v.replace('-','_')}", 0)) / 100.0
                elif "-" in str(k):
                    # Si la llave es "1-1"
                    if float(v) > mejor_prob * 100:
                        mejor_marcador = k
                        mejor_prob = float(v) / 100.0
            
            if not mejor_marcador and "most_likely" in score_mkt:
                 mejor_marcador = str(score_mkt["most_likely"])

        else:
            fuente = f"ERROR: {res.get('error', 'Desconocido')[:40]}"

        if not probs_final:
            probs_final = {"local": 0.33, "empate": 0.33, "visitante": 0.34}

        # --- HÁNDICAP EXACTO MATEMÁTICAMENTE ---
        # El hándicap Loc -0.5 significa exactamente lo mismo que gana el local.
        hcp_local_m05 = probs_final.get("local", 0)
        # El hándicap Vis +0.5 significa que gana la visita o empatan.
        hcp_visita_p05 = probs_final.get("empate", 0) + probs_final.get("visitante", 0)
        
        # Para Loc -1.5 (ganar por 2 goles o más), usamos la matriz completa (8x8) sin truncar
        lambda_local = 1.4 * (probs_final.get("local", 0.33) / 0.33)
        lambda_visitante = 1.1 * (probs_final.get("visitante", 0.33) / 0.33)
        matriz = self.poisson.calcular_matriz(lambda_local, lambda_visitante)
        hcp_local_m15 = sum(matriz[i, j] for i in range(matriz.shape[0]) for j in range(matriz.shape[1]) if i - j >= 2)

        doble_1x = probs_final.get("local", 0) + probs_final.get("empate", 0)
        doble_12 = probs_final.get("local", 0) + probs_final.get("visitante", 0)
        doble_x2 = probs_final.get("empate", 0) + probs_final.get("visitante", 0)

        mercados = {
            "over_15": mercados_bzz.get("over_15", 0.75),
            "over_25": mercados_bzz.get("over_25", 0.50),
            "over_35": mercados_bzz.get("over_35", 0.30),
            "btts_si": mercados_bzz.get("btts_si", 0.50),
            "btts_no": mercados_bzz.get("btts_no", 0.50),
            "doble_1x": doble_1x,
            "doble_12": doble_12,
            "doble_x2": doble_x2,
            "hcp_local_m05": hcp_local_m05,
            "hcp_local_m15": hcp_local_m15,
            "hcp_visita_p05": hcp_visita_p05,
        }

        max_prob = max(probs_final.values())
        confianza = "alta" if max_prob > 0.55 else ("media" if max_prob > 0.45 else "baja")

        return RespuestaPronostico(
            local=consulta.local, visitante=consulta.visitante, hora=hora_partido,
            probabilidades=probs_final, mercados=mercados,
            confianza=confianza, marcador_top=mejor_marcador,
            marcador_prob=mejor_prob, fuente=fuente,
        )
