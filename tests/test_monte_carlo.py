"""Testes do motor de simulação e do erro tipo I da situação realista (issue #14)."""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from src.config import ALPHA, N_SIMULACOES, make_rng
from src.monte_carlo import (
    REALISTA,
    SAIDA_Q1,
    Proporcao,
    erro_tipo_i,
    gerar_conjuntos,
    margem_esperada,
    p_valores,
    simular,
    tabela_rejeicoes,
)
from src.simulacao import gerar_grupos
from src.testes_estatisticos import aplicar_mann_whitney, aplicar_welch


def test_conjuntos_da_situacao_realista_vem_do_gerador() -> None:
    com, sem = gerar_conjuntos(REALISTA, 0.5, 20, make_rng(3))
    com_ref, sem_ref = gerar_grupos(0.5, 35, 35, repeticoes=20, rng=make_rng(3))
    np.testing.assert_array_equal(com, com_ref)
    np.testing.assert_array_equal(sem, sem_ref)


def test_tamanho_dos_grupos_segue_a_situacao() -> None:
    situacao = replace(REALISTA, n_com=10, n_sem=60)
    com, sem = gerar_conjuntos(situacao, 0.0, 7, make_rng(1))
    assert com.shape == (7, 10)
    assert sem.shape == (7, 60)


def test_escala_log_so_tira_o_log_dos_mesmos_sorteios() -> None:
    log = replace(REALISTA, escala_log=True)
    com, sem = gerar_conjuntos(REALISTA, 1.0, 30, make_rng(5))
    com_log, sem_log = gerar_conjuntos(log, 1.0, 30, make_rng(5))
    np.testing.assert_allclose(com_log, np.log(com))
    np.testing.assert_allclose(sem_log, np.log(sem))


def test_outliers_somam_de_uma_a_quatro_semanas_em_cerca_de_5_por_cento() -> None:
    outliers = replace(REALISTA, prob_outlier=0.05)
    com, sem = gerar_conjuntos(REALISTA, 0.0, 4_000, make_rng(9))
    com_out, sem_out = gerar_conjuntos(outliers, 0.0, 4_000, make_rng(9))
    for base, contaminado in ((com, com_out), (sem, sem_out)):
        atraso = contaminado - base
        esquecidos = atraso > 0
        assert math.isclose(esquecidos.mean(), 0.05, abs_tol=0.005)
        assert atraso[esquecidos].min() >= 168 and atraso[esquecidos].max() <= 672
        np.testing.assert_array_equal(atraso[~esquecidos], 0)


def test_p_valores_vetorizados_batem_com_os_testes_da_issue_11() -> None:
    com, sem = gerar_conjuntos(REALISTA, 0.8, 5, make_rng(11))
    p = p_valores(com, sem)
    for i in range(5):
        assert math.isclose(p["welch"][i], aplicar_welch(com[i], sem[i]).p_valor)
        assert math.isclose(p["mann_whitney"][i], aplicar_mann_whitney(com[i], sem[i]).p_valor)


def test_intervalo_de_wilson() -> None:
    proporcao = Proporcao(rejeicoes=500, repeticoes=10_000)
    inferior, superior = proporcao.intervalo()
    # Fórmula de Wilson com p = 0,05, n = 10.000 e z = 1,96, feita à mão.
    assert proporcao.taxa == 0.05
    assert math.isclose(inferior, 0.045898, abs_tol=1e-6)
    assert math.isclose(superior, 0.054447, abs_tol=1e-6)
    assert Proporcao(0, 100).intervalo()[0] == pytest.approx(0.0, abs=1e-12)


def test_margem_esperada_com_10_mil_repeticoes() -> None:
    assert math.isclose(margem_esperada(0.05, 10_000), 0.00427, abs_tol=1e-5)


def test_simulacao_e_reproduzivel() -> None:
    a = simular(REALISTA, 0.3, repeticoes=500)
    b = simular(REALISTA, 0.3, repeticoes=500)
    for teste in ("welch", "mann_whitney"):
        np.testing.assert_array_equal(a.p[teste], b.p[teste])
    assert a.repeticoes == 500


def test_proporcao_conta_p_valores_abaixo_de_alpha() -> None:
    sim = simular(REALISTA, 1.0, repeticoes=400)
    for teste in ("welch", "mann_whitney"):
        assert sim.proporcao(teste).rejeicoes == int((sim.p[teste] < ALPHA).sum())
        assert sim.proporcao(teste, 0.01).rejeicoes <= sim.proporcao(teste).rejeicoes


def test_tabela_de_rejeicoes_tem_uma_linha_por_teste() -> None:
    tabela = tabela_rejeicoes([simular(REALISTA, 0.0, repeticoes=300)])
    assert list(tabela["teste"]) == ["welch", "mann_whitney"]
    assert (tabela["ic95_inferior"] <= tabela["taxa"]).all()
    assert (tabela["taxa"] <= tabela["ic95_superior"]).all()


def test_q1_usa_10_mil_repeticoes_e_o_csv_esta_em_dia() -> None:
    """Se falhar, rode `python -m src.monte_carlo` para regenerar o CSV."""
    tabela = erro_tipo_i()
    assert N_SIMULACOES == 10_000
    assert (tabela["repeticoes"] == N_SIMULACOES).all()
    assert (tabela["delta_mu"] == 0).all()

    salvo = pd.read_csv(SAIDA_Q1)
    pd.testing.assert_frame_equal(
        salvo, tabela.round(6), check_dtype=False, check_exact=False, atol=1e-6
    )
