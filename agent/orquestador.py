"""Orquestador con normalizacion de caracteres especiales (ø, å, æ)."""
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
    # Reemplazar letras especiales nórdicas
    texto = texto.replace('ø', 'o').replace('å', 'a').replace('æ', 'ae')
    # Quitar tildes
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn')
    # Quitar prefijos
    for prefijo in ['as ', 'fc ', 'cf ', 'real ', 'cd ', 'ca ', 'club ']:
        if texto.startswith(prefijo):
            texto = texto.replace(prefijo, '', 1)
    return texto.strip()

@dataclass
class RespuestaPronostico:
    local: str
    visitante: str
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

    async def _consultar_bzzoiro(self, local: str, visitante: str) -> dict:
        if not self.api_key:
            return {"error": "BZZOIRO_API_KEY vacia"}
            
        headers = {"Authorization": f"Token {self.api_key}", "User-Agent": "Mozilla/5.0"}
        loc_norm = normalizar(local)
        vis_norm = normalizar(visitante)
        
        try:
            async with httpx.AsyncClient(timeout=20.0) as c:
                for offset in range(0, 250, 50):
                    r = await c.get(f"{BASE_URL}/predictions/", headers=headers, params={"limit": 50, "offset": offset})
                    if r.status_code != 200:
                        return {"error": f"API Status {r.status_code}"}
                    
                    data = r.json()
                    results = data.get("results", [])
                    if not results:
                        break
                    
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

        if "success" in res:
            fuente = "BZZOIRO"
            mkts = res["data"].get("markets", {})
            
            mr = mkts.get("match_result", {})
            if mr:
                probs_final = {
                    "local": float(mr.get("prob_home", 0)) / 100.0,
                    "empate": float(mr.get("prob_draw", 0)) / 100.0,
                    "visitante": float(mr.get("prob_away", 0)) / 100.0
                }
            
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
            
            score_mkt = mkts.get("score", {})
            if score_mkt:
                try:
                    mejor_marcador = max(score_mkt, key=score_mkt.get)
                    mejor_prob = float(score_mkt[mejor_marcador]) / 100.0
                except: pass

            corners = mkts.get("corners", {})
            if corners:
                mercados_bzz["corners_over_85"] = float(corners.get("prob_over_85", 0)) / 100.0
                mercados_bzz["corners_over_95"] = float(corners.get("prob_over_95", 0)) / 100.0
            cards = mkts.get("cards", {})
            if cards:
                mercados_bzz["cards_over_35"] = float(cards.get("prob_over_35", 0)) / 100.0
                mercados_bzz["cards_over_45"] = float(cards.get("prob_over_45", 0)) / 100.0

        else:
            fuente = f"ERROR: {res.get('error', 'Desconocido')[:40]}"
            goles = calcular_lambda(1.6, 1.15, 1.6, 1.15)
            p1x2 = self.poisson.calcular_1x2(goles.lambda_local, goles.lambda_visitante)
            probs_final = {"local": p1x2.local, "empate": p1x2.empate, "visitante": p1x2.visitante}

        if not probs_final:
            goles = calcular_lambda(1.6, 1.15, 1.6, 1.15)
            p1x2 = self.poisson.calcular_1x2(goles.lambda_local, goles.lambda_visitante)
            prob_poisson_dict = {"local": p1x2.local, "empate": p1x2.empate, "visitante": p1x2.visitante}
            prob_local_pi = self.pi_ratings.probabilidad_local(consulta.local, consulta.visitante)
            prob_pi_dict = {"local": prob_local_pi, "empate": 0.25, "visitante": max(0.0, 1.0 - prob_local_pi - 0.25)}
            probs_final = combinar_1x2(prob_poisson_dict, prob_pi_dict)

        goles = calcular_lambda(1.6, 1.15, 1.6, 1.15)
        matriz = self.poisson.calcular_matriz(goles.lambda_local, goles.lambda_visitante)
        
        doble_1x = probs_final.get("local", 0) + probs_final.get("empate", 0)
        doble_12 = probs_final.get("local", 0) + probs_final.get("visitante", 0)
        doble_x2 = probs_final.get("empate", 0) + probs_final.get("visitante", 0)
        
        p_local_menos_05 = sum(matriz[i, j] for i in range(5) for j in range(5) if i > j)
        p_local_menos_15 = sum(matriz[i, j] for i in range(5) for j in range(5) if i - j >= 2)
        p_visita_mas_05 = sum(matriz[i, j] for i in range(5) for j in range(5) if j > i or i == j)

        o15, _ = self.poisson.calcular_over_under(goles.lambda_local, goles.lambda_visitante, 1.5)
        o25, _ = self.poisson.calcular_over_under(goles.lambda_local, goles.lambda_visitante, 2.5)
        o35, _ = self.poisson.calcular_over_under(goles.lambda_local, goles.lambda_visitante, 3.5)
        b_si, b_no = self.poisson.calcular_btts(goles.lambda_local, goles.lambda_visitante)

        mercados = {
            "over_15": mercados_bzz.get("over_15", o15),
            "over_25": mercados_bzz.get("over_25", o25),
            "over_35": mercados_bzz.get("over_35", o35),
            "btts_si": mercados_bzz.get("btts_si", b_si),
            "btts_no": mercados_bzz.get("btts_no", b_no),
            "doble_1x": doble_1x,
            "doble_12": doble_12,
            "doble_x2": doble_x2,
            "hcp_local_m05": p_local_menos_05,
            "hcp_local_m15": p_local_menos_15,
            "hcp_visita_p05": p_visita_mas_05,
            "corners_over_85": mercados_bzz.get("corners_over_85", 0.5),
            "corners_over_95": mercados_bzz.get("corners_over_95", 0.5),
            "cards_over_35": mercados_bzz.get("cards_over_35", 0.5),
            "cards_over_45": mercados_bzz.get("cards_over_45", 0.5),
        }

        if not mejor_marcador:
            for i in range(5):
                for j in range(5):
                    p = float(matriz[i, j])
                    if p > mejor_prob:
                        mejor_prob = p
                        mejor_marcador = f"{i}-{j}"

        max_prob = max(probs_final.values())
        confianza = "alta" if max_prob > 0.55 else ("media" if max_prob > 0.45 else "baja")

        return RespuestaPronostico(
            local=consulta.local, visitante=consulta.visitante,
            probabilidades=probs_final, mercados=mercados,
            confianza=confianza, marcador_top=mejor_marcador,
            marcador_prob=mejor_prob, fuente=fuente,
        )

    async def obtener_partidos_disponibles(self, limite: int = 10) -> list:
        """Obtiene la lista de partidos disponibles en Bzzoiro para mostrarlos como botones."""
        if not self.api_key:
            return []
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
                        if h and a:
                            partidos.append(f"{h} vs {a}")
                    return partidos
        except Exception as e:
            logger.error(f"Error obteniendo partidos: {e}")
        return []
