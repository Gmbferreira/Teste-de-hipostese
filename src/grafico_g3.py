"""Gráfico G3: erro tipo I dos dois testes em cada situação simulada (issue #18).

Um ponto por teste e situação, com o intervalo de 95% da proporção. A linha
vertical marca α e a faixa em volta dela é o quanto a taxa varia só por acaso
com 10.000 repetições: um ponto fora da faixa indica que o teste se desviou de α.
A primeira linha é a Q1 (situação realista), depois vêm as situações de Q3 e,
por último, a análise de sensibilidade com os tempos reais reamostrados.

Uso:
    python -m src.grafico_g3
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter, MultipleLocator

from src.config import ALPHA, N_SIMULACOES
from src.estilo import CORES_TESTE, ROTULOS_TESTE
from src.formatacao import numero, porcentagem
from src.grafico_g2 import EIXO, GRADE, TINTA, TINTA_FRACA, TINTA_SECUNDARIA
from src.monte_carlo import TESTES, erro_tipo_i, margem_esperada
from src.situacoes import POR_CHAVE, SENSIBILIDADE, TODAS_AS_SITUACOES

RAIZ = Path(__file__).resolve().parent.parent
FIGURA_PADRAO = RAIZ / "docs" / "figuras" / "g3_erro_tipo_i.png"

FAIXA_ACASO = "#e9e7e1"
DESLOCAMENTO = 0.17  # distância vertical entre os dois testes na mesma situação


def dados_g3(alpha: float = ALPHA, repeticoes: int = N_SIMULACOES) -> pd.DataFrame:
    """Erro tipo I dos dois testes na situação realista (Q1) e nas de Q3."""
    return erro_tipo_i(TODAS_AS_SITUACOES, repeticoes=repeticoes, alpha=alpha)


def _rotulo_situacao(chave: str) -> str:
    situacao = POR_CHAVE[chave]
    if situacao.base_log is not None:
        return f"Tempos reais reamostrados\nsensibilidade, {situacao.n_com} × {situacao.n_sem}"
    if situacao.escala_log:
        return f"{situacao.nome}\n{situacao.n_com} × {situacao.n_sem}, log do tempo"
    if situacao.prob_outlier:
        return f"{situacao.nome}\n{situacao.n_com} × {situacao.n_sem}, 5% esquecidos"
    return f"{situacao.nome}\n{situacao.n_com} × {situacao.n_sem} PRs"


def grafico_g3(tabela: pd.DataFrame | None = None, alpha: float | None = None) -> Figure:
    """Monta o G3 a partir da tabela de `dados_g3` (ou calcula, se não for passada)."""
    if tabela is None:
        tabela = dados_g3(alpha if alpha is not None else ALPHA)
    alpha = float(tabela["alpha"].iloc[0]) if alpha is None else alpha
    repeticoes = int(tabela["repeticoes"].iloc[0])
    margem = margem_esperada(alpha, repeticoes)

    chaves = [s.chave for s in TODAS_AS_SITUACOES if s.chave in set(tabela["situacao"])]
    posicao = {chave: len(chaves) - 1 - i for i, chave in enumerate(chaves)}  # de cima para baixo

    fig = Figure(figsize=(10, 6.9), layout="constrained", facecolor="white")
    ax: Axes = fig.subplots()

    ax.axvspan(100 * (alpha - margem), 100 * (alpha + margem), color=FAIXA_ACASO, linewidth=0, zorder=0)
    ax.axvline(100 * alpha, color=TINTA, linewidth=1.4, zorder=1)

    for i, teste in enumerate(TESTES):
        dados = tabela[tabela["teste"] == teste]
        y = np.array([posicao[c] for c in dados["situacao"]]) + (DESLOCAMENTO if i == 0 else -DESLOCAMENTO)
        x = 100 * dados["taxa"].to_numpy()
        erro = 100 * np.vstack(
            [dados["taxa"] - dados["ic95_inferior"], dados["ic95_superior"] - dados["taxa"]]
        )
        ax.errorbar(
            x,
            y,
            xerr=erro,
            fmt="o",
            color=CORES_TESTE[teste],
            markersize=8,
            markeredgecolor="white",
            markeredgewidth=1.5,
            elinewidth=1.6,
            capsize=3,
            zorder=3,
        )
        # Rótulo só nos pontos fora da faixa do acaso, que são a história do gráfico.
        for xi, yi, taxa in zip(x, y, dados["taxa"]):
            if abs(taxa - alpha) > margem:
                ax.annotate(
                    porcentagem(taxa, 2 if taxa < 0.01 else 1),
                    xy=(xi, yi),
                    xytext=(0, 7),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    color=TINTA,
                )

    # Separa a Q1 (primeira linha), as situações de Q3 e a sensibilidade (última).
    if "realista" in posicao and len(chaves) > 1:
        ax.axhline(posicao["realista"] - 0.5, color=EIXO, linewidth=0.8, zorder=1)
    for chave in chaves:
        if POR_CHAVE[chave] in SENSIBILIDADE and posicao[chave] < len(chaves) - 1:
            ax.axhline(posicao[chave] + 0.5, color=EIXO, linewidth=0.8, zorder=1)

    limite_x = max(100 * float(tabela["ic95_superior"].max()) + 1.5, 100 * alpha * 2 + 1)
    ax.set_xlim(0, limite_x)
    ax.set_ylim(-0.6, len(chaves) - 0.4)
    ax.set_yticks(range(len(chaves)))
    ax.set_yticklabels([_rotulo_situacao(c) for c in reversed(chaves)])
    ax.xaxis.set_major_locator(MultipleLocator(2 if limite_x > 8 else 1))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{numero(v, 0)}%"))
    ax.set_xlabel(
        "Erro tipo I: % dos conjuntos com H₀ verdadeira em que o teste rejeitou H₀",
        color=TINTA_SECUNDARIA,
    )
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(EIXO)
    ax.tick_params(axis="x", colors=TINTA_FRACA, labelsize=9)
    ax.tick_params(axis="y", colors=TINTA_SECUNDARIA, labelsize=10, length=0)
    ax.grid(axis="x", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)

    itens = [
        Line2D([], [], color=CORES_TESTE[t], marker="o", markersize=8, linewidth=1.6,
               markeredgecolor="white", label=f"{ROTULOS_TESTE[t]} (com IC de 95%)")
        for t in TESTES
    ]
    itens += [
        Line2D([], [], color=TINTA, linewidth=1.4, label=f"α = {porcentagem(alpha, 0)}"),
        Patch(
            facecolor=FAIXA_ACASO,
            edgecolor="none",
            label=f"variação esperada só pelo acaso (±{numero(100 * margem, 2)} ponto percentual)",
        ),
    ]
    ax.legend(
        handles=itens,
        loc="upper left",
        bbox_to_anchor=(0.0, -0.13),
        ncol=2,
        frameon=False,
        fontsize=9,
        labelcolor=TINTA_SECUNDARIA,
    )
    ax.set_title(
        "Primeira linha: Q1 (situação realista). Depois: situações de Q3. Última: "
        "sensibilidade com a cauda real, incluída depois de simular.",
        loc="left",
        fontsize=10,
        color=TINTA_SECUNDARIA,
    )
    fig.suptitle(
        f"G3 — Erro tipo I dos dois testes em cada situação "
        f"(α = {porcentagem(alpha, 0)}, {numero(repeticoes, 0)} repetições)",
        x=0.01,
        ha="left",
        fontsize=13,
        fontweight="bold",
        color=TINTA,
    )
    return fig


def salvar_g3(destino: Path = FIGURA_PADRAO, tabela: pd.DataFrame | None = None) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    grafico_g3(tabela).savefig(destino, dpi=150, bbox_inches="tight")
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=FIGURA_PADRAO)
    args = parser.parse_args()
    print(f"G3 salvo em {salvar_g3(args.saida)}")


if __name__ == "__main__":
    main()
