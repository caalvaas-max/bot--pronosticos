"""Orquestador principal del agente."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field

from agent.validacion import validar_texto
from models.poisson_bivariante import PoissonBivariante
from models.goles import calcular_lambda
from models.pi_ratings import PiRatings
from models.ensemble import combinar_1x2
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


class Orquestador:
    def __init__(self, bankroll: float = 1000.0):
        self.poisson = PoissonBivariante()
        self.pi_ratings = PiRatings()
        self.guardador = GuardadorPronosticos()

    def procesar(self, texto: str, guardar: bool = True) -> RespuestaPronostico:
        consulta = validar_texto(texto)
        logger.info(f"Procesando: {consulta.local} vs {consulta.visitante}")

        goles = calcular_lambda(1.5, 1.2, 1.3, 1.4)

        matriz = self.poisson.calcular_matriz(
            goles.lambda_local, goles.lambda_visitante
        )

        p1x2 = self.poisson.calcular_1x2(
            goles.lambda_local, goles.lambda_visitante
        )
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

        over15, under15 = self.poisson.calcular_over_under(
            goles.lambda_local, goles.lambda_visitante, 1.5
        )
        over25, under25 = self.poisson.calcular_over_under(
            goles.lambda_local, goles.lambda_visitante, 2.5
        )
        over35, under35 = self.poisson.calcular_over_under(
            goles.lambda_local, goles.lambda_visitante, 3.5
        )
        btts_si, btts_no = self.poisson.calcular_btts(
            goles.lambda_local, goles.lambda_visitante
        )

        mejor_marcador = ""
        mejor_prob = 0.0
        for i in range(5):
            for j in range(5):
                p = float(matriz[i, j])
                if p > mejor_prob:
                    mejor_prob = p
                    mejor_marcador = f"{i}-{j}"

        mercados = {
            "over_15": over15,
            "under_15": under15,
            "over_25": over25,
            "under_25": under25,
            "over_35": over35,
            "under_35": under35,
            "btts_si": btts_si,
            "btts_no": btts_no,
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
