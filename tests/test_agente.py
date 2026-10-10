"""Tests para el agente orquestador."""
import pytest
from agent.validacion import validar_texto, ConsultaPartido, ValidacionError
from agent.orquestador import Orquestador, RespuestaPronostico

def test_validar_formato_vs():
    c = validar_texto("Real Madrid vs Barcelona")
    assert c.local == "Real Madrid"
    assert c.visitante == "Barcelona"

def test_validar_formato_guion():
    c = validar_texto("Real Madrid - Barcelona")
    assert c.local == "Real Madrid"
    assert c.visitante == "Barcelona"

def test_validar_texto_vacio():
    with pytest.raises(ValidacionError):
        validar_texto("")

def test_validar_formato_invalido():
    with pytest.raises(ValidacionError):
        validar_texto("texto sin separador")

def test_orquestador_procesa():
    orq = Orquestador()
    r = orq.procesar("Real Madrid vs Barcelona", guardar=False)
    assert isinstance(r, RespuestaPronostico)
    assert r.local == "Real Madrid"
    assert "local" in r.probabilidades

def test_orquestador_probabilidades_validas():
    orq = Orquestador()
    r = orq.procesar("Equipo A vs Equipo B", guardar=False)
    total = sum(r.probabilidades.values())
    assert 0.99 <= total <= 1.01

__all__ = []
