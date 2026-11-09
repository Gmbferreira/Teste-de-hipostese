"""Testes do gráfico G2 (issue #12)."""

from __future__ import annotations

import math

import matplotlib.colors as mcolors
import numpy as np
import pytest
from scipy import stats

from src.config import N_SIMULACOES
from src.estilo import CORES_TESTE
from src.exemplo import gerar_exemplo
from src.grafico_g2 import estatisticas_sob_h0, grafico_g2, salvar_g2
from src.monte_carlo import REALISTA, simular


@pytest.fixture(scope="module")
def simuladas() -> dict[str, np.ndarray]:
    return estatisticas_sob_h0()


def _linhas_verticais(ax) -> list[float]:
    return [
        linha.get_xdata()[0]
        for linha in ax.get_lines()
        if len(set(linha.get_xdata())) == 1  # axvline tem o mesmo x nas duas pontas
    ]


def test_g2_tem_titulo_eixos_e_legenda(simuladas) -> None:
    fig = grafico_g2(simuladas=simuladas)
    welch, mann_whitney, zoom = fig.axes[:3]

    assert "G2" in fig.get_suptitle()
    for ax in (welch, mann_whitney, zoom):
        assert ax.get_title(loc="left")
        assert ax.get_xlabel()
        assert ax.get_ylabel()
    # Uma legenda só, no rodapé, com uma coluna para cada teste.
    textos = [t.get_text() for t in fig.legends[0].get_texts()]
    assert any("Região de rejeição: |t|" in t for t in textos)
    assert any("Região de rejeição: U" in t for t in textos)
    assert sum("p-valor do exemplo" in t for t in textos) == 2
    assert sum("conjuntos simulados com H₀ verdadeira" in t for t in textos) == 2


def test_g2_usa_a_cor_de_cada_teste(simuladas) -> None:
    fig = grafico_g2(simuladas=simuladas)
    welch, mann_whitney, zoom = fig.axes[:3]
    pares = ((welch, "welch"), (mann_whitney, "mann_whitney"), (zoom, "mann_whitney"))
    for ax, teste in pares:
        cores = {mcolors.to_hex(linha.get_color()) for linha in ax.get_lines()}
        assert CORES_TESTE[teste] in cores


def test_g2_marca_a_estatistica_observada(simuladas) -> None:
    exemplo = gerar_exemplo()
    fig = grafico_g2(exemplo, simuladas)
    welch, mann_whitney, zoom = fig.axes[:3]
    assert exemplo.welch.t in _linhas_verticais(welch)
    assert exemplo.mann_whitney.u in _linhas_verticais(mann_whitney)
    assert exemplo.mann_whitney.u in _linhas_verticais(zoom)


def test_g2_desenha_as_barras_simuladas(simuladas) -> None:
    welch, mann_whitney, _ = grafico_g2(simuladas=simuladas).axes[:3]
    for ax in (welch, mann_whitney):
        assert len(ax.patches) > 20  # as barras do histograma


def test_estatisticas_simuladas_sao_as_da_q1(simuladas) -> None:
    """Os t e U simulados vêm dos mesmos conjuntos da Q1 (situação realista)."""
    assert simuladas["welch"].size == simuladas["mann_whitney"].size == N_SIMULACOES
    q1 = simular(REALISTA, 0.0)
    p_welch = 2 * stats.t.sf(np.abs(simuladas["welch"]), _gl_welch_da_q1())
    np.testing.assert_allclose(p_welch, q1.p["welch"], rtol=1e-9)


def _gl_welch_da_q1() -> np.ndarray:
    from src.config import make_rng
    from src.monte_carlo import gerar_conjuntos

    com, sem = gerar_conjuntos(REALISTA, 0.0, N_SIMULACOES, make_rng())
    return stats.ttest_ind(com, sem, axis=1, equal_var=False).df


def test_u_simulado_segue_a_distribuicao_exata(simuladas) -> None:
    u = simuladas["mann_whitney"]
    assert math.isclose(u.mean(), 35 * 35 / 2, rel_tol=0.01)
    assert math.isclose(u.std(), math.sqrt(35 * 35 * 71 / 12), rel_tol=0.03)


def test_t_simulado_tem_dois_picos_e_caudas_leves(simuladas) -> None:
    """Sustenta o texto da seção 3: picos perto de ±1 e pouca massa além de ±2."""
    t = simuladas["welch"]
    centro = np.mean(np.abs(t) < 0.25)
    perto_de_um = np.mean((np.abs(t) > 0.75) & (np.abs(t) < 1.25)) / 2
    assert perto_de_um > centro  # mais massa em cada pico do que no meio
    assert np.mean(np.abs(t) > 2) < 0.05


@pytest.mark.parametrize("delta", [0.0, -1.0, 2.0])
def test_g2_funciona_em_outros_exemplos(delta: float, simuladas) -> None:
    """Sem efeito, com o U na cauda esquerda e com efeito grande."""
    fig = grafico_g2(gerar_exemplo(delta_mu=delta), simuladas)
    assert len(fig.axes) >= 3


def test_salvar_g2(tmp_path, simuladas) -> None:
    destino = salvar_g2(tmp_path / "g2.png", simuladas=simuladas)
    assert destino.exists()
    assert destino.stat().st_size > 10_000
