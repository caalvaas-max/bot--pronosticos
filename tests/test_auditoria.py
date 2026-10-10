"""Tests para el motor regenerativo (auditoria)."""
import pytest
from auditoria.metricas import CalculadoraMetricas, Metricas
from auditoria.calibrador import CalibradorAutomatico
from auditoria.ajustador_pesos import AjustadorPesos, PESOS_INICIALES

def test_metricas_vacio():
    calc = CalculadoraMetricas()
    m = calc.calcular()
    assert isinstance(m, Metricas)
    assert m.total >= 0

def test_calibrador_sin_entrenar():
    cal = CalibradorAutomatico()
    prob = cal.calibrar(0.60)
    assert prob == 0.60

def test_ajustador_pesos_iniciales():
    aj = AjustadorPesos()
    assert "poisson" in aj.pesos
    assert "pi_ratings" in aj.pesos
    assert "mercado" in aj.pesos

def test_ajustador_suma_uno():
    aj = AjustadorPesos()
    total = sum(aj.pesos.values())
    assert 0.99 <= total <= 1.01

def test_ajustador_brier_alto_baja_peso():
    aj = AjustadorPesos()
    peso_inicial = aj.pesos["poisson"]
    aj.ajustar({"poisson": 0.35})
    assert aj.pesos["poisson"] <= peso_inicial

__all__ = []
