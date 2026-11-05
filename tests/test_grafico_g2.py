"""Testes do gráfico G2 (issue #12)."""

from __future__ import annotations

import matplotlib.colors as mcolors
import pytest

from src.estilo import CORES_TESTE
from src.exemplo import gerar_exemplo
from src.grafico_g2 import grafico_g2, salvar_g2


def _linhas_verticais(ax) -> list[float]:
    return [
        linha.get_xdata()[0]
        for linha in ax.get_lines()
        if len(set(linha.get_xdata())) == 1  # axvline tem o mesmo x nas duas pontas
    ]


def test_g2_tem_titulo_eixos_e_legenda() -> None:
    fig = grafico_g2()
    welch, mann_whitney, zoom = fig.axes[:3]

    assert "G2" in fig.get_suptitle()
    for ax in (welch, mann_whitney, zoom):
        assert ax.get_title(loc="left")
        assert ax.get_xlabel()
        assert ax.get_ylabel()
    for ax in (welch, mann_whitney):
        textos = [t.get_text() for t in ax.get_legend().get_texts()]
        assert any("Região de rejeição" in t for t in textos)
        assert any("p-valor" in t for t in textos)


def test_g2_usa_a_cor_de_cada_teste() -> None:
    fig = grafico_g2()
    welch, mann_whitney, zoom = fig.axes[:3]
    pares = ((welch, "welch"), (mann_whitney, "mann_whitney"), (zoom, "mann_whitney"))
    for ax, teste in pares:
        cores = {mcolors.to_hex(linha.get_color()) for linha in ax.get_lines()}
        assert CORES_TESTE[teste] in cores


def test_g2_marca_a_estatistica_observada() -> None:
    exemplo = gerar_exemplo()
    fig = grafico_g2(exemplo)
    welch, mann_whitney, zoom = fig.axes[:3]
    assert exemplo.welch.t in _linhas_verticais(welch)
    assert exemplo.mann_whitney.u in _linhas_verticais(mann_whitney)
    assert exemplo.mann_whitney.u in _linhas_verticais(zoom)


@pytest.mark.parametrize("delta", [0.0, -1.0, 2.0])
def test_g2_funciona_em_outros_exemplos(delta: float) -> None:
    """Sem efeito, com o U na cauda esquerda e com efeito grande."""
    fig = grafico_g2(gerar_exemplo(delta_mu=delta))
    assert len(fig.axes) >= 3


def test_salvar_g2(tmp_path) -> None:
    destino = salvar_g2(tmp_path / "g2.png")
    assert destino.exists()
    assert destino.stat().st_size > 10_000
