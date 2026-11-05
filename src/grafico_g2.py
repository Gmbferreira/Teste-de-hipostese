"""Gráfico G2: distribuição da estatística de cada teste quando H₀ é verdadeira (issue #12).

Um painel para cada teste e um terceiro com o zoom na cauda do Mann-Whitney,
onde a área do p-valor é pequena demais para aparecer na escala cheia. A faixa
cinza é a região de rejeição com α = 5% bicaudal, a área colorida é o p-valor
do exemplo da issue #11 e a linha escura marca a estatística observada nele.

Uso:
    python -m src.grafico_g2
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter
from scipy import stats

from src.estilo import CORES_TESTE, ROTULOS_TESTE
from src.exemplo import Exemplo, gerar_exemplo
from src.formatacao import numero, p_valor, porcentagem
from src.testes_estatisticos import ResultadoMannWhitney, distribuicao_nula_u

RAIZ = Path(__file__).resolve().parent.parent
FIGURA_PADRAO = RAIZ / "docs" / "figuras" / "g2_estatistica_sob_h0.png"

# Tinta e superfícies dos gráficos. O texto nunca usa a cor do teste: a cor
# fica nas linhas e áreas, e o texto ao lado identifica o que cada uma é.
TINTA = "#0b0b0b"
TINTA_SECUNDARIA = "#52514e"
TINTA_FRACA = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"
FAIXA_REJEICAO = "#ecebe6"
OPACIDADE_P_VALOR = 0.4


def _formatar_eixos(ax: Axes, casas_x: int, casas_y: int) -> None:
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: numero(v, casas_x)))
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: numero(v, casas_y)))
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(EIXO)
    ax.tick_params(colors=TINTA_FRACA, labelsize=9)
    ax.grid(axis="y", color=GRADE, linewidth=0.8)
    ax.set_axisbelow(True)


def _rotular_linha(ax: Axes, x: float, y: float, texto: str, *, direita: bool = True) -> None:
    ax.annotate(
        texto,
        xy=(x, y),
        xytext=(5 if direita else -5, 0),
        textcoords="offset points",
        ha="left" if direita else "right",
        va="top",
        fontsize=9,
        color=TINTA,
    )


def _legenda(ax: Axes, cor: str, *, curva: str, regiao: str, area: str, observado: str) -> None:
    itens = [
        Line2D([], [], color=cor, linewidth=2, label=curva),
        Patch(facecolor=FAIXA_REJEICAO, edgecolor="none", label=f"{regiao} (α = 5%)"),
        Patch(facecolor=cor, alpha=OPACIDADE_P_VALOR, edgecolor="none", label=area),
        Line2D([], [], color=TINTA, linewidth=1.4, label=observado),
    ]
    ax.legend(
        handles=itens,
        loc="upper left",
        bbox_to_anchor=(0.0, -0.16),
        frameon=False,
        fontsize=9,
        labelcolor=TINTA_SECUNDARIA,
    )


def _painel_welch(ax: Axes, exemplo: Exemplo) -> None:
    w = exemplo.welch
    cor = CORES_TESTE["welch"]
    limite = max(4.5, abs(w.t) + 0.8)
    x = np.linspace(-limite, limite, 2001)
    densidade = stats.t.pdf(x, w.gl)
    topo = densidade.max() * 1.18

    for inicio, fim in ((-limite, -w.t_critico), (w.t_critico, limite)):
        ax.axvspan(inicio, fim, color=FAIXA_REJEICAO, linewidth=0, zorder=0)
    ax.fill_between(
        x,
        densidade,
        where=np.abs(x) >= abs(w.t),
        interpolate=True,
        color=cor,
        alpha=OPACIDADE_P_VALOR,
        linewidth=0,
        zorder=2,
    )
    ax.plot(x, densidade, color=cor, linewidth=2, zorder=3)
    ax.axvline(w.t, color=TINTA, linewidth=1.4, zorder=4)
    ax.axvline(-w.t, color=TINTA_FRACA, linewidth=1.0, zorder=4)
    _rotular_linha(ax, w.t, topo * 0.97, f"t observado = {numero(w.t)}", direita=w.t >= 0)

    ax.set_xlim(-limite, limite)
    ax.set_ylim(0, topo)
    ax.set_title(
        f"{ROTULOS_TESTE['welch']}: compara as médias", loc="left", fontsize=11, color=TINTA
    )
    ax.set_xlabel("Estatística t (sem unidade)", color=TINTA_SECUNDARIA)
    ax.set_ylabel("Densidade de probabilidade", color=TINTA_SECUNDARIA)
    _formatar_eixos(ax, casas_x=0, casas_y=1)
    _legenda(
        ax,
        cor,
        curva=f"Distribuição t com {numero(w.gl, 1)} graus de liberdade",
        regiao=f"Região de rejeição: |t| > {numero(w.t_critico)}",
        area=f"p-valor do exemplo = {p_valor(w.p_valor)} (área pintada)",
        observado=f"t observado = {numero(w.t)} (linha cinza: {numero(-w.t)})",
    )


def _faixa_u(m: ResultadoMannWhitney) -> tuple[np.ndarray, np.ndarray, float, float]:
    pmf = distribuicao_nula_u(m.n_com, m.n_sem)
    u = np.arange(pmf.size, dtype=float)
    centro = m.n_pares / 2
    desvio = np.sqrt(m.n_com * m.n_sem * (m.n_com + m.n_sem + 1) / 12)
    afastamento = max(4.2 * desvio, abs(m.u - centro) + 0.6 * desvio)
    inicio = max(0.0, centro - afastamento)
    fim = min(float(m.n_pares), centro + afastamento)
    return u, 100 * pmf, inicio, fim  # probabilidade em %


def _painel_mann_whitney(ax: Axes, exemplo: Exemplo) -> None:
    m = exemplo.mann_whitney
    cor = CORES_TESTE["mann_whitney"]
    u, probabilidade, inicio_x, fim_x = _faixa_u(m)
    topo = probabilidade.max() * 1.18
    inferior, superior = m.regiao_rejeicao
    espelho = m.n_pares - m.u

    ax.axvspan(inicio_x, inferior + 0.5, color=FAIXA_REJEICAO, linewidth=0, zorder=0)
    ax.axvspan(superior - 0.5, fim_x, color=FAIXA_REJEICAO, linewidth=0, zorder=0)
    ax.fill_between(
        u,
        probabilidade,
        where=(u <= min(m.u, espelho)) | (u >= max(m.u, espelho)),
        step="mid",
        color=cor,
        alpha=OPACIDADE_P_VALOR,
        linewidth=0,
        zorder=2,
    )
    ax.plot(u, probabilidade, color=cor, linewidth=2, drawstyle="steps-mid", zorder=3)
    ax.axvline(m.u, color=TINTA, linewidth=1.4, zorder=4)
    ax.axvline(espelho, color=TINTA_FRACA, linewidth=1.0, zorder=4)
    # Perto da borda direita o rótulo vai para a esquerda da linha.
    posicao = (m.u - inicio_x) / (fim_x - inicio_x)
    _rotular_linha(ax, m.u, topo * 0.97, f"U observado = {numero(m.u, 0)}", direita=posicao < 0.7)

    ax.set_xlim(inicio_x, fim_x)
    ax.set_ylim(0, topo)
    ax.set_title(
        f"{ROTULOS_TESTE['mann_whitney']}: compara os postos",
        loc="left",
        fontsize=11,
        color=TINTA,
    )
    ax.set_xlabel(
        "Estatística U (nº de pares em que o PR com bot demorou mais)",
        color=TINTA_SECUNDARIA,
    )
    ax.set_ylabel("Probabilidade (%)", color=TINTA_SECUNDARIA)
    _formatar_eixos(ax, casas_x=0, casas_y=2)
    _legenda(
        ax,
        cor,
        curva=f"Distribuição exata de U ({m.n_com} × {m.n_sem} PRs)",
        regiao=f"Região de rejeição: U ≤ {numero(inferior, 0)} ou U ≥ {numero(superior, 0)}",
        area=f"p-valor do exemplo = {p_valor(m.p_valor)} (área pintada)",
        observado=(
            f"U observado = {numero(m.u, 0)} (linha cinza: {numero(espelho, 0)}, "
            "à mesma distância do centro)"
        ),
    )


def _painel_zoom(ax: Axes, exemplo: Exemplo) -> None:
    """Cauda do lado do U observado, ampliada para a área do p-valor aparecer."""
    m = exemplo.mann_whitney
    cor = CORES_TESTE["mann_whitney"]
    u, probabilidade, inicio_x, fim_x = _faixa_u(m)
    inferior, superior = m.regiao_rejeicao
    direita = m.u >= m.n_pares / 2

    if direita:
        inicio, fim = min(m.u, superior) - 20, fim_x
        faixa = (superior - 0.5, fim)
        cauda = u >= m.u
    else:
        inicio, fim = inicio_x, max(m.u, inferior) + 20
        faixa = (inicio, inferior + 0.5)
        cauda = u <= m.u
    janela = (u >= inicio) & (u <= fim)
    topo = probabilidade[janela].max() * 1.1

    ax.axvspan(*faixa, color=FAIXA_REJEICAO, linewidth=0, zorder=0)
    ax.fill_between(
        u[janela],
        probabilidade[janela],
        where=cauda[janela],
        step="mid",
        color=cor,
        alpha=OPACIDADE_P_VALOR,
        linewidth=0,
        zorder=2,
    )
    ax.plot(u[janela], probabilidade[janela], color=cor, linewidth=2,
            drawstyle="steps-mid", zorder=3)
    ax.axvline(m.u, color=TINTA, linewidth=1.4, zorder=4)

    # Seta apontando a área: cada cauda vale metade do p-valor.
    alvo_x = m.u + (8 if direita else -8)
    alvo_y = probabilidade[int(round(alvo_x))] * 0.4
    ax.annotate(
        f"área desta cauda\n= {porcentagem(m.p_valor / 2, 3)}\n"
        f"(metade do p-valor,\n{numero(m.p_valor, 5)})",
        xy=(alvo_x, alvo_y),
        xytext=(0.76 if direita else 0.24, 0.6),
        textcoords="axes fraction",
        ha="center",
        fontsize=9,
        color=TINTA,
        arrowprops={"arrowstyle": "-|>", "color": TINTA_SECUNDARIA, "linewidth": 1},
    )

    ax.set_xlim(inicio, fim)
    ax.set_ylim(0, topo)
    ax.set_title("Zoom na cauda (a outra é igual)", loc="left", fontsize=11, color=TINTA)
    ax.set_xlabel("Estatística U (nº de pares)", color=TINTA_SECUNDARIA)
    ax.set_ylabel("Probabilidade (%)", color=TINTA_SECUNDARIA)
    _formatar_eixos(ax, casas_x=0, casas_y=3)


def grafico_g2(exemplo: Exemplo | None = None) -> Figure:
    """Monta o G2 para o exemplo da issue #11 (ou outro conjunto, se passado)."""
    if exemplo is None:
        exemplo = gerar_exemplo()

    # Figure direto, sem pyplot: o Streamlit roda o script fora da thread
    # principal, e assim não há estado global nem janela para fechar.
    fig = Figure(figsize=(14, 5.8), layout="constrained", facecolor="white")
    ax_welch, ax_mw, ax_zoom = fig.subplots(1, 3, width_ratios=[1, 1, 0.55])
    _painel_welch(ax_welch, exemplo)
    _painel_mann_whitney(ax_mw, exemplo)
    _painel_zoom(ax_zoom, exemplo)

    fig.suptitle(
        "G2 — Distribuição da estatística de cada teste quando H₀ é verdadeira "
        f"(α = {porcentagem(exemplo.welch.alpha, 0)}, bicaudal)",
        x=0.01,
        ha="left",
        fontsize=13,
        fontweight="bold",
        color=TINTA,
    )
    return fig


def salvar_g2(destino: Path = FIGURA_PADRAO, exemplo: Exemplo | None = None) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    grafico_g2(exemplo).savefig(destino, dpi=150, bbox_inches="tight")
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=FIGURA_PADRAO)
    args = parser.parse_args()
    print(f"G2 salvo em {salvar_g2(args.saida)}")


if __name__ == "__main__":
    main()
