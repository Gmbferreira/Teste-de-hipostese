"""Gráfico G4: curvas de poder dos dois testes (issue #20).

Um painel por situação simulada, com as curvas dos dois testes no mesmo painel:
proporção de rejeições × tamanho do efeito. O primeiro painel é a Q2 (situação
realista, issue #15), depois vêm as situações de Q3 e, por último, a análise de
sensibilidade com os tempos reais reamostrados (issue #16).

Com δ = 0 a proporção é o erro tipo I, então cada curva começa perto de α. A
linha tracejada marca o efeito observado nos dados reais.

Uso:
    python -m src.grafico_g4
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MultipleLocator

from src.config import ALPHA, N_SIMULACOES
from src.estilo import CORES_TESTE, ROTULOS_TESTE
from src.formatacao import numero, porcentagem
from src.grafico_g2 import EIXO, GRADE, TINTA, TINTA_FRACA, TINTA_SECUNDARIA
from src.monte_carlo import TESTES, poder
from src.parametros import DELTA_MU_OBSERVADO, GRADE_DELTA_MU_SUGERIDA
from src.situacoes import POR_CHAVE, SENSIBILIDADE, TODAS_AS_SITUACOES

RAIZ = Path(__file__).resolve().parent.parent
FIGURA_PADRAO = RAIZ / "docs" / "figuras" / "g4_curvas_de_poder.png"

PODER_DE_REFERENCIA = 0.80
COLUNAS = 3
EFEITOS_NO_EIXO = (0.0, 0.5, 1.0, 1.5, 2.0)
FUNDO_SENSIBILIDADE = "#f6f5f1"


def dados_g4(
    alpha: float = ALPHA,
    repeticoes: int = N_SIMULACOES,
    grade: tuple[float, ...] = GRADE_DELTA_MU_SUGERIDA,
) -> pd.DataFrame:
    """Poder dos dois testes na situação realista (Q2) e nas de Q3, em cada efeito.

    Com α = 5% é a junção de resultados/q2_poder.csv e resultados/q3_poder.csv.
    """
    return poder(TODAS_AS_SITUACOES, grade, repeticoes, alpha=alpha)


def _titulo_painel(chave: str) -> str:
    situacao = POR_CHAVE[chave]
    tamanhos = f"{situacao.n_com} × {situacao.n_sem} PRs"
    if chave == "realista":
        return f"Realista (Q2) · {tamanhos}"
    if situacao.base_log is not None:
        return f"Tempos reais reamostrados · {tamanhos}"
    if situacao.escala_log:
        return f"Escala log · {tamanhos}, log do tempo"
    return f"{situacao.nome} · {tamanhos}"


def _subtitulo_painel(chave: str) -> str:
    situacao = POR_CHAVE[chave]
    if chave == "realista":
        return "lognormal ajustada aos dados reais"
    if situacao in SENSIBILIDADE:
        return "sensibilidade, incluída depois de simular"
    if situacao.prob_outlier:
        return "5% dos PRs esquecidos por 1 a 4 semanas"
    if situacao.escala_log:
        return "referência boa para o Welch"
    return "situação de Q3"


def _rotulo_efeito(delta: float, _=None) -> str:
    return f"{numero(delta)}\n{numero(math.exp(delta), 1)}×"


def grafico_g4(tabela: pd.DataFrame | None = None, alpha: float | None = None) -> Figure:
    """Monta o G4 a partir da tabela de `dados_g4` (ou calcula, se não for passada)."""
    if tabela is None:
        tabela = dados_g4(alpha if alpha is not None else ALPHA)
    alpha = float(tabela["alpha"].iloc[0]) if alpha is None else alpha
    repeticoes = int(tabela["repeticoes"].iloc[0])

    chaves = [s.chave for s in TODAS_AS_SITUACOES if s.chave in set(tabela["situacao"])]
    linhas = math.ceil(len(chaves) / COLUNAS)

    fig = Figure(figsize=(13, 4.4 * linhas + 1.6), layout="constrained", facecolor="white")
    eixos = np.atleast_1d(fig.subplots(linhas, COLUNAS, sharex=True, sharey=True)).ravel()
    delta_max = float(tabela["delta_mu"].max())

    for ax, chave in zip(eixos, chaves):
        _desenhar_painel(ax, tabela[tabela["situacao"] == chave], chave, alpha, delta_max)
    for ax in eixos[len(chaves):]:
        ax.set_visible(False)

    for ax in eixos[: len(chaves)]:
        ax.tick_params(labelbottom=True)
    # Rótulo do eixo x no painel do meio da última linha, centralizado na figura.
    meio = eixos[min((linhas - 1) * COLUNAS + COLUNAS // 2, len(chaves) - 1)]
    meio.set_xlabel(
        "Tamanho do efeito δ (diferença na escala log) e quantas vezes os PRs com bot "
        "ficam mais lentos",
        color=TINTA_SECUNDARIA,
        fontsize=12,
        labelpad=10,
    )
    fig.supylabel(
        "Poder: % dos conjuntos em que o teste rejeitou H₀",
        color=TINTA_SECUNDARIA,
        fontsize=12,
    )

    itens = [
        Line2D([], [], color=CORES_TESTE[t], marker="o", markersize=6, linewidth=2.2,
               markeredgecolor="white", label=ROTULOS_TESTE[t])
        for t in TESTES
    ]
    itens += [
        Line2D([], [], color=TINTA, linewidth=1.1,
               label=f"α = {porcentagem(alpha, 0)} (erro tipo I esperado com δ = 0)"),
        Line2D([], [], color=TINTA_FRACA, linewidth=1.2, linestyle="--",
               label=f"efeito observado nos dados reais (δ = {numero(DELTA_MU_OBSERVADO)}, "
                     f"{numero(math.exp(DELTA_MU_OBSERVADO), 1)}×)"),
        Line2D([], [], color=TINTA_FRACA, linewidth=1.2, linestyle=":",
               label=f"poder de {porcentagem(PODER_DE_REFERENCIA, 0)} (referência usual)"),
    ]
    legenda = fig.legend(
        handles=itens,
        loc="outside lower center",
        ncol=3,
        frameon=False,
        fontsize=11,
        labelcolor=TINTA_SECUNDARIA,
        title=(
            "Cada painel é uma situação simulada, com as curvas dos dois testes. O intervalo "
            "de 95% de cada ponto tem no máximo ±1 ponto percentual e não aparece no gráfico."
        ),
        title_fontsize=11,
    )
    legenda.get_title().set_color(TINTA_FRACA)
    fig.suptitle(
        f"G4 — Poder dos dois testes por tamanho do efeito "
        f"(α = {porcentagem(alpha, 0)}, {numero(repeticoes, 0)} repetições por ponto)",
        x=0.01,
        ha="left",
        fontsize=16,
        fontweight="bold",
        color=TINTA,
    )
    return fig


def _desenhar_painel(
    ax: Axes, dados: pd.DataFrame, chave: str, alpha: float, delta_max: float
) -> None:
    if POR_CHAVE[chave] in SENSIBILIDADE:
        ax.set_facecolor(FUNDO_SENSIBILIDADE)

    ax.axhline(100 * alpha, color=TINTA, linewidth=1.1, zorder=1)
    ax.axhline(100 * PODER_DE_REFERENCIA, color=TINTA_FRACA, linewidth=1.2, linestyle=":", zorder=1)
    ax.axvline(DELTA_MU_OBSERVADO, color=TINTA_FRACA, linewidth=1.2, linestyle="--", zorder=1)

    for teste in TESTES:
        curva = dados[dados["teste"] == teste].sort_values("delta_mu")
        ax.plot(
            curva["delta_mu"],
            100 * curva["taxa"],
            color=CORES_TESTE[teste],
            marker="o",
            markersize=6,
            markeredgecolor="white",
            markeredgewidth=1.2,
            linewidth=2.2,
            zorder=3,
        )

    ax.set_title(_titulo_painel(chave), loc="left", fontsize=12.5, color=TINTA, pad=18)
    ax.text(
        0, 1.015, _subtitulo_painel(chave), transform=ax.transAxes,
        fontsize=10.5, color=TINTA_FRACA, va="bottom",
    )
    ax.set_xlim(-0.08, delta_max + 0.08)
    ax.set_ylim(0, 102)
    ax.set_xticks([d for d in EFEITOS_NO_EIXO if d <= delta_max])
    ax.xaxis.set_major_formatter(FuncFormatter(_rotulo_efeito))
    ax.yaxis.set_major_locator(MultipleLocator(20))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{numero(v, 0)}%"))
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(EIXO)
    ax.tick_params(axis="both", colors=TINTA_FRACA, labelsize=10.5, length=0)
    ax.grid(axis="y", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)


def salvar_g4(destino: Path = FIGURA_PADRAO, tabela: pd.DataFrame | None = None) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    grafico_g4(tabela).savefig(destino, dpi=150, bbox_inches="tight")
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=FIGURA_PADRAO)
    args = parser.parse_args()
    print(f"G4 salvo em {salvar_g4(args.saida)}")


if __name__ == "__main__":
    main()
