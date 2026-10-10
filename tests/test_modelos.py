"""Tests para los modelos matematicos."""
import pytest
from models.poisson_bivariante import PoissonBivariante
from models.pi_ratings import PiRatings
from models.goles import calcular_lambda
from models.dixon_coles import factor_tau

def test_poisson_1x2_suma_uno():
    modelo = PoissonBivariante()
    probs = modelo.calcular_1x2(1.5, 1.2)
    total = probs.local + probs.empate + probs.visitante
    assert 0.99 <= total <= 1.01

def test_poisson_matriz_suma_uno():
    modelo = PoissonBivariante()
    matriz = modelo.calcular_matriz(1.5, 1.2)
    assert 0.99 <= matriz.sum() <= 1.01

def test_poisson_lambda_invalido():
    modelo = PoissonBivariante()
    with pytest.raises(ValueError):
        modelo.calcular_matriz(-1.0, 1.2)

def test_pi_ratings_probabilidad():
    ratings = PiRatings()
    prob = ratings.probabilidad_local("Equipo A", "Equipo B")
    assert 0.0 <= prob <= 1.0

def test_pi_ratings_actualizar():
    ratings = PiRatings()
    r1 = ratings.obtener("A").rating
    ratings.actualizar("A", "B", 3, 0)
    r2 = ratings.obtener("A").rating
    assert r2 > r1

def test_goles_lambda_rango():
    r = calcular_lambda(1.5, 1.2, 1.3, 1.4)
    assert 0.3 <= r.lambda_local <= 4.0
    assert 0.3 <= r.lambda_visitante <= 4.0

def test_dixon_coles_factor():
    tau = factor_tau(0, 0, 1.5, 1.2, -0.10)
    assert tau > 0

def test_dixon_coles_marcador_alto():
    tau = factor_tau(3, 2, 1.5, 1.2, -0.10)
    assert tau == 1.0

__all__ = []
