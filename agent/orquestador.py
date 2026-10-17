"""Orquestador principal del agente CON datos reales de Bzzoiro v2."""
from __future__ import annotations
import logging
import os
from dataclasses import dataclass, field
from typing import Optional
import httpx

from agent.validacion import validar_texto, ConsultaPartido, ValidacionError
from models.poisson_bivariante import PoissonBivariante
from models.goles import calcular_lambda
from models.pi_ratings import PiRatings
from models.ensemble import combinar_1x2
from auditoria.guardar import GuardadorPronosticos, DatosPronostico

logger = logging.getLogger(__name__)
BASE_URL = "https://sports.bzzoiro.com/api/v2"

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
        self.guardador = GuardadorPronosticos()
        self.api_key = os.getenv("BZZOIRO_API_KEY", "")

    async def _consultar_bzzoiro(self, local: str, visitante: str) -> Optional[dict]:
        if not self.api_key:
            logger.warning("BZZOIRO_API_KEY no configurada")
            return None
        
        headers = {"Authorization": f"Token {self.api_key}"}
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as c:
                # Pedimos las predicciones (vienen en una lista gigante)
                r = await c.get(f"{BASE_URL}/predictions/", headers=headers)
                if r.status_code != 200:
                    logger.error(f"Error API Bzzoiro: {r.status_code}")
                    return None
                    
                data = r.json()
                results = data.get("results", [])
                
                # Buscamos el partido que coincida
                for item in results:
                    ev = item.get("event", {})
                    # Como no vimos las llaves exactas del evento, probamos las variantes más comunes
                    h_name = str(ev.get("home_team", ev.get("home", ev.get("local", "")))).lower()
                    a_name = str(ev.get("away_team", ev.get("away", ev.get("visitante", "")))).lower()
                    
                    if local.lower() in h_name and visitante.lower() in a_name:
                        logger.info(f"¡Partido encontrado en Bzzoiro!")
                        return item
                        
                logger.warning(f"No se encontró {local} vs {visitante} en Bzzoiro")
                return None
                    
        except Exception as e:
            logger.error(f"Error crítico en Bzzoiro: {e}")
            return None

    async def procesar(self, texto: str, guardar: bool = True) -> RespuestaPronostico:
        consulta = validar_texto(texto)
        logger.info(f"Procesando: {consulta.local} vs {consulta.visitante}")
        
        prediccion_bzz = await self._consultar_bzzoiro(consulta.local, consulta.visitante)
        
        fuente = "APROX"
        probs_final = {}
        mercados_bzz = {}

        if prediccion_bzz and "markets" in prediccion_bzz:
            fuente = "BZZOIRO"
            mkts = prediccion_bzz["markets"]
            
            # 1. Extraer 1X2
            mr = mkts.get("match_result", {})
            if mr:
                probs_final = {
                    "local": float(mr.get("prob_home", 0)) / 100.0,
                    "empate": float(mr.get("prob_draw", 0)) / 100.0,
                    "visitante": float(mr.get("prob_away", 0)) / 100.0
                }
            
            # 2. Extraer otros mercados (si están disponibles)
            ou = mkts.get("over_under", {})
            if ou:
                mercados_bzz["over_15"] = float(ou.get("prob_over_15", 0)) / 100.0
                mercados_bzz["over_25"] = float(ou.get("prob_over_25", 0)) / 100.0
                mercados_bzz["over_35"] = float(ou.get("prob_over_35", 0)) / 100.0
            
            btts = mkts.get("btts", {})
            if btts:
                mercados_bzz["btts_si"] = float(btts.get("prob_yes", 0)) / 100.0
                mercados_bzz["btts_no"] = float(btts.get("prob_no", 0)) / 100.0
        
        # Si falló Bzzoiro o no hay probs, usamos respaldo (Poisson)
        if fuente == "APROX" or not probs_final:
            fuente = "APROX"
            goles = calcular_lambda(1.5, 1.2, 1.5, 1.2)
            p1x2 = self.poisson.calcular_1x2(goles.lambda_local, goles.lambda_visitante)
            prob_poisson_dict = {"local": p1x2.local, "empate": p1x2.empate, "visitante": p1x2.visitante}
            prob_local_pi = self.pi_ratings.probabilidad_local(consulta.local, consulta.visitante)
            prob_pi_dict = {"local": prob_local_pi, "empate": 0.25, "visitante": max(0.0, 1.0 - prob_local_pi - 0.25)}
            probs_final = combinar_1x2(prob_poisson_dict, prob_pi_dict)

        # Calcular matriz para el marcador exacto (siempre con Poisson o datos base)
        goles = calcular_lambda(1.5, 1.2, 1.5, 1.2)
        matriz = self.poisson.calcular_matriz(goles.lambda_local, goles.lambda_visitante)
        
        # Llenar los mercados faltantes con Poisson
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
        }

        mejor_marcador = ""
        mejor_prob = 0.0
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
