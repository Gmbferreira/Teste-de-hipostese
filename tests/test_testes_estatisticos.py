"""Testes da aplicação do t de Welch e do Mann-Whitney (issue #11)."""

from __future__ import annotations

import itertools
import math

import numpy as np
import pytest
from scipy import stats

from src.config import ALPHA, make_rng
from src.testes_estatisticos import (
    aplicar_testes,
    distribuicao_nula_u,
    limites_rejeicao_u,
    p_valor_exato_u,
    aplicar_mann_whitney,
    aplicar_welch,
)


@pytest.fixture
def dados() -> tuple[np.ndarray, np.ndarray]:
    rng = make_rng(10)
    return rng.lognormal(2.0, 1.0, size=30), rng.lognormal(1.5, 1.2, size=25)


def test_welch_bate_com_o_scipy_e_com_a_formula(dados) -> None:
    com_bot, sem_bot = dados
    resultado = aplicar_welch(com_bot, sem_bot)
    referencia = stats.ttest_ind(com_bot, sem_bot, equal_var=False)

    assert math.isclose(resultado.t, referencia.statistic)
    assert math.isclose(resultado.p_valor, referencia.pvalue)

    v1 = com_bot.var(ddof=1) / len(com_bot)
    v2 = sem_bot.var(ddof=1) / len(sem_bot)
    gl = (v1 + v2) ** 2 / (v1**2 / (len(com_bot) - 1) + v2**2 / (len(sem_bot) - 1))
    assert math.isclose(resultado.gl, gl)
    assert math.isclose(resultado.t, (com_bot.mean() - sem_bot.mean()) / math.sqrt(v1 + v2))


def test_welch_regiao_de_rejeicao_e_intervalo(dados) -> None:
    resultado = aplicar_welch(*dados)
    cauda = 2 * stats.t.sf(resultado.t_critico, resultado.gl)
    assert math.isclose(cauda, ALPHA)
    assert resultado.rejeita_h0 == (abs(resultado.t) > resultado.t_critico)
    inferior, superior = resultado.ic95
    assert inferior < resultado.diferenca_medias < superior
    # O IC de 95% exclui o zero exatamente quando o teste rejeita com alpha = 5%.
    assert resultado.rejeita_h0 == (inferior > 0 or superior < 0)


def test_welch_p_valor_e_a_area_das_duas_caudas(dados) -> None:
    resultado = aplicar_welch(*dados)
    area = 2 * stats.t.sf(abs(resultado.t), resultado.gl)
    assert math.isclose(area, resultado.p_valor)


def test_mann_whitney_u_conta_os_pares(dados) -> None:
    com_bot, sem_bot = dados
    resultado = aplicar_mann_whitney(com_bot, sem_bot)
    pares_com_bot_maior = (com_bot[:, None] > sem_bot[None, :]).sum()

    assert resultado.metodo == "exact"
    assert resultado.u == pares_com_bot_maior
    assert resultado.n_pares == len(com_bot) * len(sem_bot)
    assert math.isclose(resultado.prob_superioridade, pares_com_bot_maior / resultado.n_pares)
    assert math.isclose(resultado.correlacao_bisserial, 2 * resultado.prob_superioridade - 1)


def test_mann_whitney_p_valor_e_a_area_da_distribuicao_exata(dados) -> None:
    resultado = aplicar_mann_whitney(*dados)
    referencia = stats.mannwhitneyu(*dados, alternative="two-sided", method="exact")
    assert math.isclose(resultado.p_valor, referencia.pvalue)
    area = p_valor_exato_u(resultado.u, resultado.n_com, resultado.n_sem)
    assert math.isclose(area, resultado.p_valor, rel_tol=1e-9)


@pytest.mark.parametrize(("n1", "n2"), [(3, 4), (5, 5), (4, 6)])
def test_distribuicao_nula_u_bate_com_a_enumeracao(n1: int, n2: int) -> None:
    """Com H₀ verdadeira, todas as ordenações dos n1 + n2 valores têm a mesma chance."""
    contagem = np.zeros(n1 * n2 + 1)
    for posicoes in itertools.combinations(range(n1 + n2), n1):
        grupo_1 = set(posicoes)
        # U = pares (x do grupo 1, y do grupo 2) com x > y, olhando só as posições.
        u = sum(
            1 for i in grupo_1 for j in range(n1 + n2) if j not in grupo_1 and i > j
        )
        contagem[u] += 1
    np.testing.assert_allclose(distribuicao_nula_u(n1, n2), contagem / contagem.sum())


@pytest.mark.parametrize(("n1", "n2"), [(35, 35), (10, 10), (10, 60)])
def test_distribuicao_nula_u_media_variancia_e_simetria(n1: int, n2: int) -> None:
    pmf = distribuicao_nula_u(n1, n2)
    u = np.arange(pmf.size)
    media = (u * pmf).sum()
    variancia = ((u - media) ** 2 * pmf).sum()

    assert math.isclose(pmf.sum(), 1.0)
    np.testing.assert_allclose(pmf, pmf[::-1], atol=1e-15)
    assert math.isclose(media, n1 * n2 / 2)
    assert math.isclose(variancia, n1 * n2 * (n1 + n2 + 1) / 12)


@pytest.mark.parametrize(("n1", "n2"), [(35, 35), (10, 10), (10, 60)])
def test_limites_de_rejeicao_de_u(n1: int, n2: int) -> None:
    inferior, superior = limites_rejeicao_u(n1, n2)
    total = n1 * n2
    assert inferior + superior == total

    # Os limites rejeitam e o valor logo depois deles já não rejeita.
    assert p_valor_exato_u(superior, n1, n2) < ALPHA
    assert p_valor_exato_u(superior - 1, n1, n2) >= ALPHA
    assert p_valor_exato_u(inferior, n1, n2) < ALPHA
    assert p_valor_exato_u(inferior + 1, n1, n2) >= ALPHA


def test_mann_whitney_com_empates_usa_aproximacao_normal() -> None:
    resultado = aplicar_mann_whitney(np.array([1.0, 2.0, 2.0, 5.0]), np.array([2.0, 3.0, 4.0]))
    assert resultado.metodo == "asymptotic"


def test_hodges_lehmann_recupera_um_deslocamento() -> None:
    sem_bot = make_rng(5).normal(10, 1, size=40)
    resultado = aplicar_mann_whitney(sem_bot + 3.0, sem_bot)
    assert math.isclose(resultado.hodges_lehmann, 3.0)


def test_aplicar_testes_devolve_os_dois(dados) -> None:
    resultados = aplicar_testes(*dados)
    assert set(resultados) == {"welch", "mann_whitney"}
    for resultado in resultados.values():
        assert 0 <= resultado.p_valor <= 1
        assert resultado.rejeita_h0 == (resultado.p_valor < ALPHA)


def test_rejeita_vetor_com_menos_de_duas_observacoes() -> None:
    with pytest.raises(ValueError):
        aplicar_welch(np.array([1.0]), np.array([1.0, 2.0]))
    with pytest.raises(ValueError):
        aplicar_mann_whitney(np.ones((2, 3)), np.ones(3))
