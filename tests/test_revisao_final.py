"""Revisão final dos gráficos (issue #24).

O enunciado pede que todo gráfico tenha título, eixos nomeados, legenda e um
texto de 2 a 4 frases. Este teste confere os quatro gráficos do dashboard de uma
vez, com α = 5% e com α = 1% onde o dashboard deixa trocar o α. O texto do G2
fica em dashboard/app.py e é conferido em tests/test_dashboard.py.
"""

from __future__ import annotations

import re

import pytest
from matplotlib.figure import Figure

from src.exemplo import gerar_exemplo
from src.grafico_g1 import grafico_g1
from src.grafico_g2 import estatisticas_sob_h0, grafico_g2
from src.grafico_g3 import dados_g3, grafico_g3
from src.grafico_g4 import dados_g4, grafico_g4
from src.textos import texto_dados, texto_erro_tipo_i, texto_poder


def frases(texto: str) -> int:
    """Conta frases pelo ponto final; "p.p." e números com vírgula não contam."""
    return len(re.findall(r"[.!?](?:\s|$)", texto.replace("p.p.", "pp")))


def _verificar_figura(fig: Figure, nome: str) -> None:
    eixos = [ax for ax in fig.axes if ax.get_visible()]
    titulo = fig.get_suptitle() or " ".join(ax.get_title(loc="left") for ax in eixos)
    assert titulo.startswith(nome), f"{nome}: sem título"

    rotulos_x = [ax.get_xlabel() for ax in eixos if ax.get_xlabel()] + [fig.get_supxlabel()]
    rotulos_y = [ax.get_ylabel() for ax in eixos if ax.get_ylabel()] + [fig.get_supylabel()]
    assert any(r.strip() for r in rotulos_x), f"{nome}: eixo x sem nome"
    assert any(r.strip() for r in rotulos_y), f"{nome}: eixo y sem nome"

    legendas = list(fig.legends) + [ax.get_legend() for ax in eixos if ax.get_legend()]
    assert legendas and any(leg.get_texts() for leg in legendas), f"{nome}: sem legenda"


@pytest.fixture(scope="module")
def estatisticas():
    return estatisticas_sob_h0()


def test_g1(estatisticas) -> None:
    _verificar_figura(grafico_g1(), "G1")
    assert 2 <= frases(texto_dados()) <= 4


def test_g2(estatisticas) -> None:
    _verificar_figura(grafico_g2(gerar_exemplo(), estatisticas), "G2")


@pytest.mark.parametrize("alpha", [0.05, 0.01])
def test_g3(alpha: float) -> None:
    tabela = dados_g3(alpha=alpha)
    _verificar_figura(grafico_g3(tabela, alpha=alpha), "G3")
    assert 2 <= frases(texto_erro_tipo_i(tabela)) <= 4


@pytest.mark.parametrize("alpha", [0.05, 0.01])
def test_g4(alpha: float) -> None:
    tabela = dados_g4(alpha=alpha)
    _verificar_figura(grafico_g4(tabela, alpha=alpha), "G4")
    assert 2 <= frases(texto_poder(tabela)) <= 4
