"""Testes dos parâmetros da simulação (issue #4)."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.parametros import (
    DELTA_MU_OBSERVADO,
    GRADE_DELTA_MU_SUGERIDA,
    GRUPO_CONTROLE,
    PARAMETROS_REAIS,
    RAZAO_GEOMETRICA_OBSERVADA,
)

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "data" / "prs_merge_time.csv"


def test_formulas_da_lognormal() -> None:
    for parametros in PARAMETROS_REAIS.values():
        assert math.isclose(parametros.mediana, math.exp(parametros.mu))
        assert math.isclose(
            parametros.media, math.exp(parametros.mu + parametros.sigma**2 / 2)
        )
        assert math.isclose(
            parametros.variancia,
            (math.exp(parametros.sigma**2) - 1)
            * math.exp(2 * parametros.mu + parametros.sigma**2),
        )
        assert math.isclose(parametros.desvio, math.sqrt(parametros.variancia))
        assert math.isclose(parametros.quantil(0.5), parametros.mediana, rel_tol=1e-12)


def test_quantis_sao_crescentes() -> None:
    for parametros in PARAMETROS_REAIS.values():
        quantis = [parametros.quantil(p) for p in (0.1, 0.5, 0.9, 0.99)]
        assert quantis == sorted(quantis)
        assert all(valor > 0 for valor in quantis)


def test_parametros_batem_com_os_dados() -> None:
    dados = pd.read_csv(DADOS)
    for grupo, parametros in PARAMETROS_REAIS.items():
        x = dados.loc[dados["grupo"] == grupo, "tempo_merge_horas"].to_numpy()
        sigma, loc, scale = stats.lognorm.fit(x, floc=0)

        assert loc == 0
        assert parametros.n_real == len(x)
        assert math.isclose(parametros.mu, math.log(scale), rel_tol=1e-6)
        assert math.isclose(parametros.sigma, sigma, rel_tol=1e-6)
        assert math.isclose(
            parametros.mediana_amostral, float(np.median(x)), rel_tol=1e-4
        )


def test_efeito_observado_e_consistente() -> None:
    delta_esperado = PARAMETROS_REAIS["com_bot"].mu - PARAMETROS_REAIS["sem_bot"].mu
    assert math.isclose(DELTA_MU_OBSERVADO, delta_esperado)
    assert math.isclose(
        RAZAO_GEOMETRICA_OBSERVADA, math.exp(delta_esperado), rel_tol=1e-12
    )


def test_grupo_controle_e_grade_de_efeitos() -> None:
    assert GRUPO_CONTROLE in PARAMETROS_REAIS
    assert GRADE_DELTA_MU_SUGERIDA[0] == 0.0
    assert len(GRADE_DELTA_MU_SUGERIDA) >= 5
    assert GRADE_DELTA_MU_SUGERIDA == tuple(sorted(GRADE_DELTA_MU_SUGERIDA))
