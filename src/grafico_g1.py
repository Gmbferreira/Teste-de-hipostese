"""Gráfico G1: dados reais × dados simulados (issue #5).

Cada linha compara um grupo nos dados reais (à esquerda) e nos dados
simulados (à direita). O eixo x fica em escala logarítmica porque o tempo
até o merge é muito assimétrico: poucos PRs demoram muito e puxam a cauda
direita. Os dados simulados usam o mesmo gerador do exemplo/G2: efeito
observado, 35 PRs por grupo e semente 42.

Uso:
    python -m src.grafico_g1
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
from matplotlib.ticker import FixedLocator, FuncFormatter, MaxNLocator

from src.dados_reais import carregar_grupos
from src.estilo import CORES_GRUPO, ROTULOS_GRUPO
from src.formatacao import numero
from src.grafico_g2 import EIXO, GRADE, TINTA, TINTA_FRACA, TINTA_SECUNDARIA
from src.simulacao import gerar_dataframe

RAIZ = Path(__file__).resolve().parent.parent
FIGURA_PADRAO = RAIZ / "docs" / "figuras" / "g1_dados_reais_simulados.png"

ORIGENS = ("real", "simulado")
ROTULOS_ORIGEM = {"real": "Dados reais", "simulado": "Dados simulados"}
GRUPOS = ("com_bot", "sem_bot")

# Faixas log-espaçadas comuns aos quatro painéis. Com 35 observações por
# painel, 12 faixas deixam a forma da distribuição visível sem excesso de
# barras vazias.
N_BINS = 12

# Ticks "redondos" na escala logarítmica, filtrados pelos limites do gráfico.
TICKS_HORAS = (0.03, 0.1, 0.3, 1, 3, 10, 30, 100, 300, 1000)


def dados_g1() -> pd.DataFrame:
    """Dados reais e simulados no formato longo usado pelo G1.

    Colunas: ``origem`` (real/simulado), ``grupo`` (com_bot/sem_bot) e
    ``tempo_merge_horas``. Os dados simulados são gerados com o efeito
    observado e a semente fixa do projeto, então dois chamados produzem
    exatamente a mesma tabela.
    """
    real_com, real_sem = carregar_grupos()
    simulado = gerar_dataframe()
    sim_com = simulado.loc[
        simulado["grupo"] == "com_bot", "tempo_merge_horas"
    ].to_numpy(dtype=float)
    sim_sem = simulado.loc[
        simulado["grupo"] == "sem_bot", "tempo_merge_horas"
    ].to_numpy(dtype=float)

    registros = [
        (origem, grupo, float(valor))
        for origem, com, sem in (
            ("real", real_com, real_sem),
            ("simulado", sim_com, sim_sem),
        )
        for grupo, valores in (("com_bot", com), ("sem_bot", sem))
        for valor in valores
    ]
    return pd.DataFrame(
        registros, columns=["origem", "grupo", "tempo_merge_horas"]
    )


def _serie(dados: pd.DataFrame, origem: str, grupo: str) -> np.ndarray:
    filtro = (dados["origem"] == origem) & (dados["grupo"] == grupo)
    valores = dados.loc[filtro, "tempo_merge_horas"].to_numpy(dtype=float)
    if valores.size == 0:
        raise ValueError(f"Sem dados para origem={origem!r} e grupo={grupo!r}.")
    if (valores <= 0).any():
        raise ValueError("O tempo até o merge precisa ser positivo.")
    return valores


def _faixas(tempos: pd.Series) -> np.ndarray:
    """Bins log-espaçados que cobrem todos os tempos, com uma folga pequena."""
    minimo = float(tempos.min())
    maximo = float(tempos.max())
    if minimo <= 0:
        raise ValueError("O tempo até o merge precisa ser positivo.")
    return np.geomspace(minimo * 0.8, maximo * 1.1, N_BINS + 1)


def _formata_horas(valor: float, _pos: int) -> str:
    if valor >= 1:
        return numero(valor, 0)
    if valor >= 0.1:
        return numero(valor, 1)
    return numero(valor, 2)


def _estilizar_painel(ax: Axes, faixas: np.ndarray, topo: int) -> None:
    ax.set_xscale("log")
    ax.set_xlim(faixas[0], faixas[-1])
    ax.set_ylim(0, topo)

    ticks = [tick for tick in TICKS_HORAS if faixas[0] <= tick <= faixas[-1]]
    ax.xaxis.set_major_locator(FixedLocator(ticks))
    ax.xaxis.set_major_formatter(FuncFormatter(_formata_horas))
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: numero(valor, 0)))

    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(EIXO)
    ax.tick_params(axis="both", colors=TINTA_FRACA, labelsize=9)
    ax.tick_params(axis="x", which="minor", colors=EIXO, length=2)
    ax.grid(axis="y", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)


def grafico_g1(dados: pd.DataFrame | None = None) -> Figure:
    """Monta o G1 com os quatro histogramas (2 grupos × 2 origens)."""
    if dados is None:
        dados = dados_g1()

    faixas = _faixas(dados["tempo_merge_horas"])
    contagens = [
        np.histogram(_serie(dados, origem, grupo), bins=faixas)[0]
        for grupo in GRUPOS
        for origem in ORIGENS
    ]
    topo = int(max(contagem.max() for contagem in contagens)) + 1

    fig = Figure(figsize=(12, 8), facecolor="white")
    axes = fig.subplots(2, 2, sharex=True, sharey=True)
    fig.subplots_adjust(
        top=0.84, bottom=0.09, left=0.09, right=0.98,
        hspace=0.38, wspace=0.16,
    )

    for linha, grupo in enumerate(GRUPOS):
        for coluna, origem in enumerate(ORIGENS):
            ax = axes[linha, coluna]
            valores = _serie(dados, origem, grupo)
            mediana = float(np.median(valores))

            ax.hist(
                valores,
                bins=faixas,
                color=CORES_GRUPO[grupo],
                edgecolor="white",
                linewidth=0.8,
                zorder=3,
            )
            ax.axvline(
                mediana,
                color=TINTA,
                linestyle="--",
                linewidth=1.3,
                zorder=4,
            )
            ax.set_title(
                f"{ROTULOS_GRUPO[grupo]} — {ROTULOS_ORIGEM[origem]}\n"
                f"n = {len(valores)} · mediana = {numero(mediana, 1)} h",
                loc="left",
                fontsize=10.5,
                color=TINTA,
                pad=6,
            )
            _estilizar_painel(ax, faixas, topo)

    for ax in axes[1, :]:
        ax.set_xlabel(
            "Tempo até o merge (horas, escala logarítmica)",
            color=TINTA_SECUNDARIA,
            labelpad=4,
        )
    for ax in axes[:, 0]:
        ax.set_ylabel("Número de PRs", color=TINTA_SECUNDARIA, labelpad=4)

    handles = [
        Patch(
            facecolor=CORES_GRUPO["com_bot"],
            edgecolor="white",
            label=ROTULOS_GRUPO["com_bot"],
        ),
        Patch(
            facecolor=CORES_GRUPO["sem_bot"],
            edgecolor="white",
            label=ROTULOS_GRUPO["sem_bot"],
        ),
        Line2D(
            [0], [0],
            color=TINTA,
            linestyle="--",
            linewidth=1.3,
            label="Mediana",
        ),
    ]
    fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.932),
        ncol=3,
        frameon=False,
        fontsize=9,
        labelcolor=TINTA,
    )
    fig.suptitle(
        "G1 — Tempo até o merge: dados reais × dados simulados",
        x=0.01,
        y=0.985,
        ha="left",
        fontsize=13,
        fontweight="bold",
        color=TINTA,
    )
    fig.text(
        0.01,
        0.947,
        "35 PRs por grupo · dados simulados com o efeito observado e semente 42",
        ha="left",
        va="top",
        fontsize=9,
        color=TINTA_SECUNDARIA,
    )
    return fig


def salvar_g1(
    destino: Path = FIGURA_PADRAO, dados: pd.DataFrame | None = None
) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    grafico_g1(dados).savefig(destino, dpi=150, bbox_inches="tight")
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=FIGURA_PADRAO)
    args = parser.parse_args()
    print(f"G1 salvo em {salvar_g1(args.saida)}")


if __name__ == "__main__":
    main()
