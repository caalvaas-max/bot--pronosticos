"""Orquestador principal del agente."""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Optional

from agent.validacion import validar_texto, ConsultaPartido, ValidacionError
from models.poisson_bivariante import PoissonBivariante
from models.goles import calcular_lambda
from models.pi_ratings import PiRatings
from models.ensemble import combinar_1x2
from betting.value_betting import DetectorValue
from betting.bankroll import GestorBankroll
from betting.combinadas import GeneradorCombinadas
from auditoria.guardar import GuardadorPronosticos, DatosPronostico

logger = logging.getLogger(__name__)

@dataclass
class RespuestaPronostico:
    local: str
    visitante: str
    probabilidades: dict
    value_bets: list = field(default_factory=list)
    combinada: Optional[dict] = None
    confianza: str = "media"

class Orquestador:
    def __init__(self, bankroll: float = 1000.0):
        self.poisson = PoissonBivariante()
        self.pi_ratings = PiRatings()
        self.detector = DetectorValue()
        self.gestor_bankroll = GestorBankroll(bankroll)
        self.generador_comb = GeneradorCombinadas()
        self.guardador = GuardadorPronosticos()

    def procesar(self, texto: str, guardar: bool = True) -> RespuestaPronostico:
        consulta = validar_texto(texto)
        logger.info(f"Procesando: {consulta.local} vs {consulta.visitante}")

        goles = calcular_lambda(1.5, 1.2, 1.3, 1.4)
        probs_poisson = self.poisson.calcular_1x2(
            goles.lambda_local, goles.lambda_visitante
        )
        prob_poisson_dict = {
            "local": probs_poisson.local,
            "empate": probs_poisson.empate,
            "visitante": probs_poisson.visitante,
        }

        prob_local_pi = self.pi_ratings.probabilidad_local(
            consulta.local, consulta.visitante
        )
        prob_pi_dict = {
            "local": prob_local_pi,
            "empate": 0.25,
            "visitante": 1.0 - prob_local_pi - 0.25,
        }

        probs_final = combinar_1x2(prob_poisson_dict, prob_pi_dict)

        confianza = "alta" if max(probs_final.values()) > 0.55 else "media"

        respuesta = RespuestaPronostico(
            local=consulta.local,
            visitante=consulta.visitante,
            probabilidades=probs_final,
            confianza=confianza,
        )

        if guardar:
            for mercado, prob in [("1x2", max(probs_final.values()))]:
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
