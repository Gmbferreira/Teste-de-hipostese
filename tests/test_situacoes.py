"""Testes das situações de Q3 (issue #16)."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from src.config import N_SIMULACOES
from src.monte_carlo import REALISTA, Proporcao, simular
from src.situacoes import (
    AMOSTRAS_PEQUENAS,
    DESBALANCEADO,
    ESCALA_LOG,
    OUTLIERS,
    POR_CHAVE,
    SAIDA_DOCS,
    SAIDA_ERRO_TIPO_I,
    SAIDA_PODER,
    SITUACOES_Q3,
    TODAS_AS_SITUACOES,
    documento,
    erro_tipo_i_q3,
    poder_q3,
)
from src.testes_estatisticos import tamanho_exato_mann_whitney


@pytest.fixture(scope="module")
def tipo_i() -> pd.DataFrame:
    return erro_tipo_i_q3()


@pytest.fixture(scope="module")
def poder() -> pd.DataFrame:
    return poder_q3()


def test_situacoes_sao_as_registradas_na_expectativa() -> None:
    assert (AMOSTRAS_PEQUENAS.n_com, AMOSTRAS_PEQUENAS.n_sem) == (10, 10)
    assert (DESBALANCEADO.n_com, DESBALANCEADO.n_sem) == (10, 60)
    assert OUTLIERS.prob_outlier == 0.05
    assert OUTLIERS.atraso_outlier_horas == (168.0, 672.0)  # de 1 a 4 semanas
    assert ESCALA_LOG.escala_log and not REALISTA.escala_log
    assert len(SITUACOES_Q3) >= 2
    assert TODAS_AS_SITUACOES[0] is REALISTA
    assert set(POR_CHAVE) == {s.chave for s in TODAS_AS_SITUACOES}
    for situacao in SITUACOES_Q3:
        assert situacao.nome and situacao.descricao and situacao.motivo


def test_erro_tipo_i_em_cada_situacao(tipo_i: pd.DataFrame) -> None:
    assert len(tipo_i) == 2 * len(SITUACOES_Q3)
    assert (tipo_i["delta_mu"] == 0).all()
    assert (tipo_i["repeticoes"] == N_SIMULACOES).all()


def test_poder_tem_ao_menos_5_efeitos_comecando_em_zero(poder: pd.DataFrame) -> None:
    for situacao in SITUACOES_Q3:
        efeitos = sorted(poder.loc[poder["situacao"] == situacao.chave, "delta_mu"].unique())
        assert len(efeitos) >= 5
        assert efeitos[0] == 0


def test_poder_com_delta_zero_e_o_proprio_erro_tipo_i(tipo_i, poder) -> None:
    zero = poder[poder["delta_mu"] == 0].reset_index(drop=True)
    pd.testing.assert_frame_equal(zero, tipo_i.reset_index(drop=True))


def test_mann_whitney_nao_muda_na_escala_log() -> None:
    """Tirar o log não muda a ordem dos tempos, então U e o p-valor são os mesmos."""
    for delta in (0.0, 1.0):
        normal = simular(REALISTA, delta, repeticoes=2_000)
        log = simular(ESCALA_LOG, delta, repeticoes=2_000)
        np.testing.assert_array_equal(log.p["mann_whitney"], normal.p["mann_whitney"])
        assert not np.array_equal(log.p["welch"], normal.p["welch"])


def test_mann_whitney_fica_perto_do_tamanho_exato(tipo_i: pd.DataFrame) -> None:
    """Com H₀ verdadeira, U tem a distribuição exata em qualquer situação de Q3."""
    for situacao in SITUACOES_Q3:
        linha = tipo_i[(tipo_i["situacao"] == situacao.chave) & (tipo_i["teste"] == "mann_whitney")]
        taxa = float(linha["taxa"].iloc[0])
        exato = tamanho_exato_mann_whitney(situacao.n_com, situacao.n_sem)
        erro_padrao = math.sqrt(exato * (1 - exato) / N_SIMULACOES)
        assert abs(taxa - exato) < 4 * erro_padrao


def test_csvs_e_docs_estao_em_dia(tipo_i: pd.DataFrame, poder: pd.DataFrame) -> None:
    """Se falhar, rode `python -m src.situacoes` para regenerar os arquivos."""
    for arquivo, tabela in ((SAIDA_ERRO_TIPO_I, tipo_i), (SAIDA_PODER, poder)):
        salvo = pd.read_csv(arquivo)
        pd.testing.assert_frame_equal(
            salvo, tabela.round(6), check_dtype=False, check_exact=False, atol=1e-6
        )
    salvo = SAIDA_DOCS.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert salvo == documento(tipo_i, poder)


def test_proporcao_do_desbalanceado_bate_com_a_contagem(tipo_i: pd.DataFrame) -> None:
    linha = tipo_i[(tipo_i["situacao"] == "desbalanceado") & (tipo_i["teste"] == "welch")]
    proporcao = Proporcao(int(linha["rejeicoes"].iloc[0]), int(linha["repeticoes"].iloc[0]))
    assert math.isclose(proporcao.taxa, float(linha["taxa"].iloc[0]))
