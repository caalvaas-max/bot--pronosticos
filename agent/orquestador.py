"""Orquestador principal del agente con datos reales de Bzzoiro."""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from agent.validacion import validar_texto, ConsultaPartido, ValidacionError
from models.poisson_bivariante import PoissonBivariante
from models.goles import calcular_lambda
from models.pi_ratings import PiRatings
from models.ensemble import combinar_1x2
from data.bzzoiro_client import BzzoiroClient
from auditoria.guardar import GuardadorPronosticos, DatosPronostico

logger = logging.getLogger(__name__)


@dataclass
class RespuestaPronostico:
    local: str
    visitante: str
    probabilidades: dict
    mercados: dict = field(default_factory=dict)
    confianza: str = "media"
    marcador_top: str = ""
    marcador_prob: float = 0.0
    datos_reales: bool = False


class Orquestador:
    def __init__(self, bankroll: float = 1000.0):
        self.poisson = PoissonBivariante()
        self.pi_ratings = PiRatings()
        self.bzzoiro = BzzoiroClient()
        self.guardador = GuardadorPronosticos()

    async def procesar(self, texto: str, guardar: bool = True) -> RespuestaPronostico:
        consulta = validar_texto(texto)
        logger.info(f"Procesando: {consulta.local} vs {consulta.visitante}")

        # Intentar obtener datos reales de Bzzoiro
        lambda_local = 1.5
        lambda_visitante = 1.2
        datos_reales = False

        try:
            partido = await self.bzzoiro.buscar_partido(
                consulta.local, consulta.visitante
            )
            if partido:
                evento_id = partido.get("id")
                logger.info(f"Partido encontrado en Bzzoiro: {evento_id}")

                stats = await self.bzzoiro.stats_partido(evento_id)
                if stats and "stats" in stats:
                    home_xg = stats["stats"].get("home", {}).get("xg", {})
                    away_xg = stats["stats"].get("away", {}).get("xg", {})
                    xg_home = home_xg.get("actual") if isinstance(home_xg, dict) else None
                    xg_away = away_xg.get("actual") if isinstance(away_xg, dict) else None
                    if xg_home and xg_away:
                        lambda_local = float(xg_home)
                        lambda_visitante = float(xg_away)
                        datos_reales = True
                        logger.info(f"xG reales: {lambda_local} vs {lambda_visitante}")
        except Exception as e:
            logger.warning(f"Bzzoiro no disponible: {e}")

        goles = calcular_lambda(lambda_local, lambda_local, lambda_visitante, lambda_visitante)

        matriz = self.poisson.calcular_matriz(goles.lambda_local, goles.lambda_visitante)

        p1x2 = self.poisson.calcular_1x2(goles.lambda_local, goles.lambda_visitante)
        prob_poisson_dict = {
            "local": p1x2.local,
            "empate": p1x2.empate,
            "visitante": p1x2.visitante,
        }

        prob_local_pi = self.pi_ratings.probabilidad_local(
            consulta.local, consulta.visitante
        )
        prob_pi_dict = {
            "local": prob_local_pi,
            "empate": 0.25,
            "visitante": max(0.0, 1.0 - prob_local_pi - 0.25),
        }

        probs_final = combinar_1x2(prob_poisson_dict, prob_pi_dict)

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
        if max_prob > 0.55:
            confianza = "alta"
        elif max_prob > 0.45:
            confianza = "media"
        else:
            confianza = "baja"

        respuesta = RespuestaPronostico(
            local=consulta.local,
            visitante=consulta.visitante,
            probabilidades=probs_final,
            mercados=mercados,
            confianza=confianza,
            marcador_top=mejor_marcador,
            marcador_prob=mejor_prob,
            datos_reales=datos_reales,
        )

        if guardar:
            datos = DatosPronostico(
                evento_id=f"{consulta.local}_{consulta.visitante}",
                liga="desconocida",
                local=consulta.local,
                visitante=consulta.visitante,
                mercado="1x2",
                seleccion="principal",
                probabilidad=max_prob,
                confianza=confianza,
            )
            try:
                self.guardador.guardar(datos)
            except Exception as e:
                logger.error(f"Error guardando: {e}")

        return respuesta


__all__ = ["Orquestador", "RespuestaPronostico"]
