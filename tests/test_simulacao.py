"""Testes de sanidade do gerador de dados simulados (issue #9)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.config import make_rng
from src.parametros import DELTA_MU_OBSERVADO, GRUPO_CONTROLE, PARAMETROS_REAIS
from src.simulacao import (
    MU_CONTROLE,
    N_POR_GRUPO,
    SIGMA_CONTROLE,
    gerar_dataframe,
    gerar_grupos,
)

DADOS = Path(__file__).resolve().parents[1] / "data" / "prs_merge_time.csv"


def test_parametros_vem_do_grupo_de_controle() -> None:
    controle = PARAMETROS_REAIS[GRUPO_CONTROLE]
    assert MU_CONTROLE == controle.mu
    assert SIGMA_CONTROLE == controle.sigma
    assert N_POR_GRUPO == controle.n_real == 35


def test_formato_de_um_conjunto_e_de_varias_repeticoes() -> None:
    com_bot, sem_bot = gerar_grupos(n_com=12, n_sem=20)
    assert com_bot.shape == (12,)
    assert sem_bot.shape == (20,)

    com_bot, sem_bot = gerar_grupos(n_com=12, n_sem=20, repeticoes=50)
    assert com_bot.shape == (50, 12)
    assert sem_bot.shape == (50, 20)


def test_tempos_sao_positivos() -> None:
    com_bot, sem_bot = gerar_grupos(delta_mu=1.0, repeticoes=200)
    assert (com_bot > 0).all()
    assert (sem_bot > 0).all()


def test_mesma_semente_gera_os_mesmos_dados() -> None:
    a = gerar_grupos(delta_mu=0.5, rng=make_rng(7))
    b = gerar_grupos(delta_mu=0.5, rng=make_rng(7))
    c = gerar_grupos(delta_mu=0.5, rng=make_rng(8))
    np.testing.assert_array_equal(a[0], b[0])
    np.testing.assert_array_equal(a[1], b[1])
    assert not np.array_equal(a[0], c[0])


def test_sem_rng_usa_a_semente_fixa_do_projeto() -> None:
    a = gerar_grupos()
    b = gerar_grupos(rng=make_rng())
    np.testing.assert_array_equal(a[0], b[0])
    np.testing.assert_array_equal(a[1], b[1])


def test_grupo_sem_bot_nao_depende_do_efeito() -> None:
    _, sem_h0 = gerar_grupos(delta_mu=0.0, rng=make_rng(3))
    _, sem_h1 = gerar_grupos(delta_mu=1.5, rng=make_rng(3))
    np.testing.assert_array_equal(sem_h0, sem_h1)


def test_com_h0_os_dois_grupos_seguem_a_lognormal_do_controle() -> None:
    com_bot, sem_bot = gerar_grupos(
        delta_mu=0.0, n_com=200_000, n_sem=200_000, rng=make_rng(1)
    )
    for amostra in (com_bot, sem_bot):
        log_t = np.log(amostra)
        assert math.isclose(log_t.mean(), MU_CONTROLE, abs_tol=0.02)
        assert math.isclose(log_t.std(ddof=1), SIGMA_CONTROLE, abs_tol=0.02)
        assert math.isclose(
            np.median(amostra), PARAMETROS_REAIS[GRUPO_CONTROLE].mediana, rel_tol=0.03
        )


def test_efeito_multiplica_a_mediana_por_exp_delta() -> None:
    for delta in (0.25, 1.0, 2.0):
        com_bot, sem_bot = gerar_grupos(
            delta_mu=delta, n_com=200_000, n_sem=200_000, rng=make_rng(2)
        )
        razao = np.median(com_bot) / np.median(sem_bot)
        assert math.isclose(razao, math.exp(delta), rel_tol=0.04)


@pytest.mark.parametrize(
    ("grupo", "delta"), [("sem_bot", 0.0), ("com_bot", DELTA_MU_OBSERVADO)]
)
def test_mediana_real_e_plausivel_para_o_modelo(grupo: str, delta: float) -> None:
    """A mediana real cai no miolo das medianas de amostras simuladas de n = 35."""
    real = pd.read_csv(DADOS)
    mediana_real = real.loc[real["grupo"] == grupo, "tempo_merge_horas"].median()

    com_bot, sem_bot = gerar_grupos(delta_mu=delta, repeticoes=5_000, rng=make_rng(4))
    simuladas = np.median(com_bot if grupo == "com_bot" else sem_bot, axis=1)
    inferior, superior = np.percentile(simuladas, [2.5, 97.5])
    assert inferior < mediana_real < superior


def test_dataframe_tem_o_formato_do_csv_real() -> None:
    df = gerar_dataframe()
    assert list(df.columns) == ["grupo", "tempo_merge_horas"]
    assert (df["grupo"] == "com_bot").sum() == N_POR_GRUPO
    assert (df["grupo"] == "sem_bot").sum() == N_POR_GRUPO
    assert (df["tempo_merge_horas"] > 0).all()


@pytest.mark.parametrize(
    "argumentos",
    [{"n_com": 0}, {"n_sem": 0}, {"sigma": 0.0}, {"repeticoes": 0}],
)
def test_argumentos_invalidos(argumentos: dict) -> None:
    with pytest.raises(ValueError):
        gerar_grupos(**argumentos)
