"""Orquestador principal del agente."""
from __future__ import annotations
import logging
import math
from dataclasses import dataclass, field

from agent.validacion import validar_texto
from models.poisson_bivariante import PoissonBivariante
from models.goles import calcular_lambda
from models.pi_ratings import PiRatings
from models.ensemble import combinar_1x2
from auditoria.guardar import GuardadorPronosticos, DatosPronostico

logger = logging.getLogger(__name__)

CORNERES_PROM = 10.0
TARJETAS_PROM = 4.5


def _poisson_prob(k: int, lam: float) -> float:
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


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

        h_local_m05 = probs_final["local"]
        h_local_m1 = sum(
            float(matriz[i, j])
            for i in range(matriz.shape[0])
            for j in range(matriz.shape[1])
            if i - j > 1
        )
        h_visitante_p05 = probs_final["visitante"] + probs_final["empate"]

        p_corners_over_85 = 1.0 - sum(_poisson_prob(k, CORNERES_PROM) for k in range(9))
        p_corners_over_95 = 1.0 - sum(_poisson_prob(k, CORNERES_PROM) for k in range(10))
        p_corners_over_105 = 1.0 - sum(_poisson_prob(k, CORNERES_PROM) for k in range(11))

        p_tarj_over_35 = 1.0 - sum(_poisson_prob(k, TARJETAS_PROM) for k in range(4))
        p_tarj_over_45 = 1.0 - sum(_poisson_prob(k, TARJETAS_PROM) for k in range(5))
        p_tarj_over_55 = 1.0 - sum(_poisson_prob(k, TARJETAS_PROM) for k in range(6))

        mercados = {
            "over_15": over15,
            "under_15": under15,
            "over_25": over25,
            "under_25": under25,
            "over_35": over35,
            "under_35": under35,
            "btts_si": btts_si,
            "btts_no": btts_no,
            "h_local_m05": h_local_m05,
            "h_local_m1": h_local_m1,
            "h_visitante_p05": h_visitante_p05,
            "corners_over_85": p_corners_over_85,
            "corners_over_95": p_corners_over_95,
            "corners_over_105": p_corners_over_105,
            "tarj_over_35": p_tarj_over_35,
            "tarj_over_45": p_tarj_over_45,
            "tarj_over_55": p_tarj_over_55,
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
