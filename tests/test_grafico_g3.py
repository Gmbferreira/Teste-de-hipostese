"""Testes do gráfico G3 (issue #18)."""

from __future__ import annotations

import matplotlib.colors as mcolors
import pandas as pd
import pytest

from src.estilo import CORES_TESTE
from src.grafico_g3 import dados_g3, grafico_g3, salvar_g3
from src.monte_carlo import margem_esperada
from src.situacoes import TODAS_AS_SITUACOES


@pytest.fixture(scope="module")
def tabela() -> pd.DataFrame:
    return dados_g3()


def test_dados_tem_q1_e_todas_as_situacoes_de_q3(tabela: pd.DataFrame) -> None:
    assert list(dict.fromkeys(tabela["situacao"])) == [s.chave for s in TODAS_AS_SITUACOES]
    assert set(tabela["teste"]) == {"welch", "mann_whitney"}
    assert (tabela["delta_mu"] == 0).all()


def test_g3_tem_titulo_eixo_e_legenda(tabela: pd.DataFrame) -> None:
    fig = grafico_g3(tabela)
    ax = fig.axes[0]
    assert "G3" in fig.get_suptitle()
    assert "Erro tipo I" in ax.get_xlabel() and "%" in ax.get_xlabel()
    # O enunciado pede nome nos dois eixos; o vertical é o das situações.
    assert "Situação simulada" in ax.get_ylabel() and "PRs" in ax.get_ylabel()
    textos = [t.get_text() for t in ax.get_legend().get_texts()]
    assert any("t de Welch" in t for t in textos)
    assert any("Mann-Whitney" in t for t in textos)
    assert any("α = 5%" in t for t in textos)
    assert len(ax.get_yticklabels()) == len(TODAS_AS_SITUACOES)


def test_g3_usa_a_cor_de_cada_teste_e_a_linha_em_alpha(tabela: pd.DataFrame) -> None:
    ax = grafico_g3(tabela).axes[0]
    cores = {mcolors.to_hex(linha.get_color()) for linha in ax.get_lines()}
    assert {CORES_TESTE["welch"], CORES_TESTE["mann_whitney"]} <= cores
    verticais = [linha.get_xdata()[0] for linha in ax.get_lines() if len(set(linha.get_xdata())) == 1]
    assert 5.0 in verticais


def test_g3_rotula_so_os_pontos_fora_da_faixa(tabela: pd.DataFrame) -> None:
    ax = grafico_g3(tabela).axes[0]
    margem = margem_esperada(0.05, 10_000)
    fora = tabela[(tabela["taxa"] - 0.05).abs() > margem]
    rotulos = [t for t in ax.texts if t.get_text().endswith("%")]
    assert len(rotulos) == len(fora) > 0


def test_g3_com_alpha_de_1_por_cento() -> None:
    fig = grafico_g3(dados_g3(alpha=0.01), alpha=0.01)
    ax = fig.axes[0]
    verticais = [linha.get_xdata()[0] for linha in ax.get_lines() if len(set(linha.get_xdata())) == 1]
    assert 1.0 in verticais
    assert "α = 1%" in fig.get_suptitle()


def test_salvar_g3(tmp_path, tabela: pd.DataFrame) -> None:
    destino = salvar_g3(tmp_path / "g3.png", tabela)
    assert destino.exists() and destino.stat().st_size > 10_000
