"""Testes do gráfico G4 (issue #20)."""

from __future__ import annotations

import math

import matplotlib.colors as mcolors
import pandas as pd
import pytest

from src.estilo import CORES_TESTE
from src.grafico_g4 import dados_g4, grafico_g4, salvar_g4
from src.monte_carlo import SAIDA_Q2
from src.parametros import DELTA_MU_OBSERVADO
from src.situacoes import SAIDA_PODER, TODAS_AS_SITUACOES


@pytest.fixture(scope="module")
def tabela() -> pd.DataFrame:
    return dados_g4()


def _paineis(fig):
    return [ax for ax in fig.axes if ax.get_visible()]


def _horizontais(ax) -> list[float]:
    return [linha.get_ydata()[0] for linha in ax.get_lines() if len(set(linha.get_ydata())) == 1]


def _verticais(ax) -> list[float]:
    return [linha.get_xdata()[0] for linha in ax.get_lines() if len(set(linha.get_xdata())) == 1]


def test_dados_juntam_os_resultados_da_15_e_da_16(tabela: pd.DataFrame) -> None:
    """Com α = 5% o G4 usa exatamente o que está nos CSVs da Q2 e da Q3."""
    salvos = pd.concat([pd.read_csv(SAIDA_Q2), pd.read_csv(SAIDA_PODER)], ignore_index=True)
    pd.testing.assert_frame_equal(
        salvos, tabela.round(6), check_dtype=False, check_exact=False, atol=1e-6
    )
    assert list(dict.fromkeys(tabela["situacao"])) == [s.chave for s in TODAS_AS_SITUACOES]


def test_g4_tem_um_painel_por_situacao_com_os_dois_testes(tabela: pd.DataFrame) -> None:
    paineis = _paineis(grafico_g4(tabela))
    assert len(paineis) == len(TODAS_AS_SITUACOES)
    efeitos = tabela["delta_mu"].nunique()
    for ax in paineis:
        curvas = [linha for linha in ax.get_lines() if len(linha.get_xdata()) == efeitos]
        assert {mcolors.to_hex(c.get_color()) for c in curvas} == {
            CORES_TESTE["welch"],
            CORES_TESTE["mann_whitney"],
        }
    assert paineis[0].get_title(loc="left").startswith("Realista (Q2)")


def test_g4_tem_titulo_eixos_com_unidade_e_legenda(tabela: pd.DataFrame) -> None:
    fig = grafico_g4(tabela)
    assert "G4" in fig.get_suptitle() and "α = 5%" in fig.get_suptitle()
    assert "Poder" in fig.get_supylabel() and "%" in fig.get_supylabel()
    rotulos_x = [ax.get_xlabel() for ax in _paineis(fig) if ax.get_xlabel()]
    assert len(rotulos_x) == 1
    assert "Tamanho do efeito δ" in rotulos_x[0] and "mais lentos" in rotulos_x[0]
    textos = [t.get_text() for t in fig.legends[0].get_texts()]
    assert "t de Welch" in textos and "Mann-Whitney" in textos
    assert any("α = 5%" in t for t in textos)
    assert any("efeito observado" in t for t in textos)


def test_g4_marca_alpha_80_por_cento_e_o_efeito_observado(tabela: pd.DataFrame) -> None:
    for ax in _paineis(grafico_g4(tabela)):
        assert 5.0 in _horizontais(ax)
        assert 80.0 in _horizontais(ax)
        assert any(math.isclose(x, DELTA_MU_OBSERVADO) for x in _verticais(ax))


def test_g4_com_alpha_de_1_por_cento() -> None:
    tabela = dados_g4(alpha=0.01, repeticoes=500)
    fig = grafico_g4(tabela, alpha=0.01)
    assert "α = 1%" in fig.get_suptitle()
    assert 1.0 in _horizontais(_paineis(fig)[0])


def test_salvar_g4(tmp_path, tabela: pd.DataFrame) -> None:
    destino = salvar_g4(tmp_path / "g4.png", tabela)
    assert destino.exists() and destino.stat().st_size > 10_000
