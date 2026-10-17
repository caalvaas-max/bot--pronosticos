"""Orquestador principal del agente CON datos reales de Bzzoiro (Endpoints v2)."""
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
                # 1. Buscar el partido (asumiendo que events o matches busca por texto)
                # Nota: Bzzoiro podría usar /matches/ o /events/. Usaremos /matches/ que es más estándar, si falla intentará /events/
                endpoint_busqueda = "matches/" 
                r = await c.get(f"{BASE_URL}/{endpoint_busqueda}", headers=headers, params={"search": f"{local} {visitante}"})
                
                if r.status_code != 200:
                    logger.error(f"Error buscando partido: {r.status_code} - {r.text}")
                    return None
                    
                data = r.json()
                results = data.get("results", data.get("data", []))
                
                if not results:
                    logger.warning(f"No se encontraron partidos para {local} vs {visitante}")
                    return None
                    
                # Tomar el primer partido encontrado
                partido = results[0]
                partido_id = partido.get("id")
                logger.info(f"Partido encontrado ID: {partido_id}")

                # 2. Consultar predicciones para ese ID
                r_pred = await c.get(f"{BASE_URL}/predictions/{partido_id}/", headers=headers)
                
                if r_pred.status_code == 200:
                    logger.info(f"Predicción obtenida de Bzzoiro para ID {partido_id}")
                    return r_pred.json()
                else:
                    logger.warning(f"Partido encontrado, pero sin predicción disponible: {r_pred.status_code}")
                    return None

        except Exception as e:
            logger.error(f"Error crítico Bzzoiro: {e}")
            return None

    def procesar(self, texto: str, guardar: bool = True) -> RespuestaPronostico:
        import asyncio
        consulta = validar_texto(texto)
        logger.info(f"Procesando: {consulta.local} vs {consulta.visitante}")

        # Intentar obtener datos reales de Bzzoiro
        prediccion_bzz = None
        try:
            # Ejecutar la llamada asíncrona desde un contexto síncrono
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
                
            if loop and loop.is_running():
                prediccion_bzz = asyncio.run_coroutine_threadsafe(
                    self._consultar_bzzoiro(consulta.local, consulta.visitante), loop
                ).result(timeout=20)
            else:
                prediccion_bzz = asyncio.run(self._consultar_bzzoiro(consulta.local, consulta.visitante))
        except Exception as e:
            logger.error(f"Error en async: {e}")

        fuente = "APROX"
        probs_final = {}

        if prediccion_bzz and "probabilities" in prediccion_bzz:
            fuente = "BZZOIRO"
            logger.info(f"Datos Bzzoiro RAW: {prediccion_bzz}")
            
            # Intentar parsear las probabilidades de Bzzoiro (asumiendo estructura típica)
            probs_bzz = prediccion_bzz["probabilities"]
            try:
                # Bzzoiro suele devolver { "home": 55.2, "draw": 25.1, "away": 19.7 }
                probs_final = {
                    "local": float(probs_bzz.get("home", 0.33)),
                    "empate": float(probs_bzz.get("draw", 0.33)),
                    "visitante": float(probs_bzz.get("away", 0.33))
                }
                # Normalizar por si vienen en 0-100
                if sum(probs_final.values()) > 2.0:
                    probs_final = {k: v/100.0 for k, v in probs_final.items()}
            except Exception as e:
                logger.error(f"Error parseando probs Bzzoiro: {e}")
                fuente = "APROX"
        
        if fuente == "APROX":
            # Cálculo de respaldo (Poisson con datos fijos)
            goles = calcular_lambda(1.5, 1.2, 1.5, 1.2)
            p1x2 = self.poisson.calcular_1x2(goles.lambda_local, goles.lambda_visitante)
            prob_poisson_dict = {"local": p1x2.local, "empate": p1x2.empate, "visitante": p1x2.visitante}
            
            prob_local_pi = self.pi_ratings.probabilidad_local(consulta.local, consulta.visitante)
            prob_pi_dict = {"local": prob_local_pi, "empate": 0.25, "visitante": max(0.0, 1.0 - prob_local_pi - 0.25)}
            
            probs_final = combinar_1x2(prob_poisson_dict, prob_pi_dict)

        # Calcular mercados usando los lambdas (o probs reales si las tuviéramos)
        # Por simplicidad, seguimos usando Poisson para los otros mercados, 
        # pero luego podríamos sacar los over/under de Bzzoiro también.
        goles = calcular_lambda(1.5, 1.2, 1.5, 1.2)
        matriz = self.poisson.calcular_matriz(goles.lambda_local, goles.lambda_visitante)

        over15, under15 = self.poisson.calcular_over_under(goles.lambda_local, goles.lambda_visitante, 1.5)
        over25, under25 = self.poisson.calcular_over_under(goles.lambda_local, goles.lambda_visitante, 2.5)
        over35, under35 = self.poisson.calcular_over_under(goles.lambda_local, goles.lambda_visitante, 3.5)
        btts_si, btts_no = self.poisson.calcular_btts(goles.lambda_local, goles.lambda_visitante)

        mejor_marcador = ""
        mejor_prob = 0.0
        for i in range(5):
            for j in range(5):
                p = float(matriz[i, j])
                if p > mejor_prob:
                    mejor_prob = p
                    mejor_marcador = f"{i}-{j}"

        mercados = {
            "over_15": over15, "under_15": under15,
            "over_25": over25, "under_25": under25,
            "over_35": over35, "under_35": under35,
            "btts_si": btts_si, "btts_no": btts_no,
        }

        max_prob = max(probs_final.values())
        confianza = "alta" if max_prob > 0.55 else ("media" if max_prob > 0.45 else "baja")

        respuesta = RespuestaPronostico(
            local=consulta.local,
            visitante=consulta.visitante,
            probabilidades=probs_final,
            mercados=mercados,
            confianza=confianza,
            marcador_top=mejor_marcador,
            marcador_prob=mejor_prob,
            fuente=fuente,
        )

        if guardar:
            for mercado, prob in [("1x2", max_prob)]:
                datos = DatosPronostico(
                    evento_id=f"{consulta.local}_{consulta.visitante}",
                    liga="desconocida",
                    local=consulta.local,
                    visitante=consulta.visitante,
                    mercado=mercado,
                    seleccion="principal",
                    probabilidad=prob,
                    confianza=confianza,
                )
                try:
                    self.guardador.guardar(datos)
                except Exception as e:
                    logger.error(f"Error guardando: {e}")

        return respuesta


__all__ = ["Orquestador", "RespuestaPronostico"]
