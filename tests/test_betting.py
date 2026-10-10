"""Tests para el modulo de apuestas."""
import pytest
from betting.value_betting import DetectorValue
from betting.bankroll import GestorBankroll
from betting.combinadas import GeneradorCombinadas

def test_value_betting_ev_positivo():
    detector = DetectorValue()
    ev = detector.calcular_ev(0.60, 2.0)
    assert ev == pytest.approx(0.20, abs=0.01)

def test_value_betting_ev_negativo():
    detector = DetectorValue()
    ev = detector.calcular_ev(0.40, 2.0)
    assert ev < 0

def test_value_betting_detecta():
    detector = DetectorValue()
    probs = {"1x2": {"local": 0.60, "empate": 0.25, "visitante": 0.15}}
    cuotas = {"1x2": {"local": 2.0, "empate": 3.5, "visitante": 5.0}}
    vb = detector.detectar(probs, cuotas)
    assert len(vb) >= 1

def test_bankroll_kelly_basico():
    gestor = GestorBankroll(1000.0)
    apuesta = gestor.calcular_stake(0.60, 2.0)
    assert apuesta.stake > 0
    assert apuesta.stake <= 50.0

def test_bankroll_probabilidad_baja():
    gestor = GestorBankroll(1000.0)
    apuesta = gestor.calcular_stake(0.30, 1.5)
    assert apuesta.stake == 0.0

def test_combinadas_minimo_dos_picks():
    gen = GeneradorCombinadas()
    candidatos = [
        {"mercado": "over_2_5", "probabilidad": 0.65, "cuota": 1.70},
        {"mercado": "btts", "probabilidad": 0.60, "cuota": 1.80},
    ]
    comb = gen.generar(candidatos)
    assert len(comb.picks) >= 2
    assert comb.cuota_total >= 1.50

def test_combinadas_pocos_candidatos():
    gen = GeneradorCombinadas()
    candidatos = [{"mercado": "x", "probabilidad": 0.60, "cuota": 1.50}]
    comb = gen.generar(candidatos)
    assert len(comb.picks) == 0

__all__ = []
