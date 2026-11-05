"""Os dois testes aplicados aos dados reais coletados (issue #22).

Usa as mesmas funções da issue #11 nos 70 PRs de data/prs_merge_time.csv e
monta a tabela e o texto da seção 6 do dashboard. Como referência, o Welch
também é aplicado ao log do tempo, a situação em que as simulações mostraram
que ele funciona bem.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ALPHA
from src.formatacao import numero, p_valor, porcentagem
from src.testes_estatisticos import (
    ResultadoMannWhitney,
    ResultadoWelch,
    aplicar_mann_whitney,
    aplicar_welch,
)

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data" / "prs_merge_time.csv"


@dataclass(frozen=True, eq=False)  # eq=False: os vetores do NumPy não comparam com ==
class ResultadoDadosReais:
    com_bot: np.ndarray
    sem_bot: np.ndarray
    welch: ResultadoWelch
    mann_whitney: ResultadoMannWhitney
    welch_log: ResultadoWelch

    @property
    def razao_geometrica(self) -> float:
        """Quantas vezes o PR com bot é mais lento, pela média geométrica."""
        return math.exp(self.welch_log.diferenca_medias)

    @property
    def ic95_razao_geometrica(self) -> tuple[float, float]:
        inferior, superior = self.welch_log.ic95
        return math.exp(inferior), math.exp(superior)


def carregar_grupos(caminho: Path = DADOS) -> tuple[np.ndarray, np.ndarray]:
    """Tempos até o merge (horas) dos grupos com bot e sem bot."""
    dados = pd.read_csv(caminho)
    com_bot = dados.loc[dados["grupo"] == "com_bot", "tempo_merge_horas"].to_numpy()
    sem_bot = dados.loc[dados["grupo"] == "sem_bot", "tempo_merge_horas"].to_numpy()
    return com_bot, sem_bot


def analisar(caminho: Path = DADOS, alpha: float = ALPHA) -> ResultadoDadosReais:
    com_bot, sem_bot = carregar_grupos(caminho)
    return ResultadoDadosReais(
        com_bot=com_bot,
        sem_bot=sem_bot,
        welch=aplicar_welch(com_bot, sem_bot, alpha),
        mann_whitney=aplicar_mann_whitney(com_bot, sem_bot, alpha),
        welch_log=aplicar_welch(np.log(com_bot), np.log(sem_bot), alpha),
    )


def _conclusao(rejeita: bool, mais_lento_com_bot: bool) -> str:
    if not rejeita:
        return "não rejeita H₀: não dá para dizer que o tempo muda"
    lado = "com bot" if mais_lento_com_bot else "sem bot"
    return f"rejeita H₀: os PRs {lado} demoram mais"


def tabela_dados_reais(resultado: ResultadoDadosReais) -> pd.DataFrame:
    """Estatística, p-valor, tamanho do efeito e conclusão de cada teste."""
    w, m, wl = resultado.welch, resultado.mann_whitney, resultado.welch_log
    inferior, superior = resultado.ic95_razao_geometrica
    return pd.DataFrame(
        [
            {
                "Teste": "t de Welch",
                "Estatística": f"t = {numero(w.t)} (gl = {numero(w.gl, 1)})",
                "p-valor": p_valor(w.p_valor),
                "Tamanho do efeito": (
                    f"diferença de médias = {numero(w.diferenca_medias, 1)} h "
                    f"(IC 95%: {numero(w.ic95[0], 1)} a {numero(w.ic95[1], 1)} h; "
                    f"d = {numero(w.d_cohen)})"
                ),
                "Conclusão (α = 5%)": _conclusao(w.rejeita_h0, w.diferenca_medias > 0),
            },
            {
                "Teste": "Mann-Whitney",
                "Estatística": f"U = {numero(m.u, 0)} de {numero(m.n_pares, 0)} pares",
                "p-valor": p_valor(m.p_valor),
                "Tamanho do efeito": (
                    f"P(PR com bot demorar mais) = {numero(m.prob_superioridade)} "
                    f"(r = {numero(m.correlacao_bisserial)}; diferença típica de "
                    f"{numero(m.hodges_lehmann, 1)} h)"
                ),
                "Conclusão (α = 5%)": _conclusao(m.rejeita_h0, m.prob_superioridade > 0.5),
            },
            {
                "Teste": "t de Welch no log do tempo (referência)",
                "Estatística": f"t = {numero(wl.t)} (gl = {numero(wl.gl, 1)})",
                "p-valor": p_valor(wl.p_valor),
                "Tamanho do efeito": (
                    f"PRs com bot {numero(resultado.razao_geometrica)} vezes mais lentos "
                    f"(IC 95%: {numero(inferior)} a {numero(superior)})"
                ),
                "Conclusão (α = 5%)": _conclusao(wl.rejeita_h0, wl.diferenca_medias > 0),
            },
        ]
    )


def texto_dados_reais(resultado: ResultadoDadosReais) -> str:
    """Texto da seção 6 (2 a 4 frases): resultado, concordância e importância prática."""
    w, m, wl = resultado.welch, resultado.mann_whitney, resultado.welch_log
    mediana_com = float(np.median(resultado.com_bot))
    mediana_sem = float(np.median(resultado.sem_bot))

    frases = [
        f"Nos {len(resultado.com_bot) + len(resultado.sem_bot)} PRs coletados, os PRs com "
        f"bot levaram mais tempo até o merge: mediana de {numero(mediana_com, 1)} h contra "
        f"{numero(mediana_sem, 1)} h sem bot."
    ]
    if m.rejeita_h0 != w.rejeita_h0:
        quem_rejeita, quem_nao = (m, w) if m.rejeita_h0 else (w, m)
        nome_rejeita = "Mann-Whitney" if quem_rejeita is m else "Welch"
        nome_nao = "Welch" if quem_nao is w else "Mann-Whitney"
        frases.append(
            f"Os dois testes discordaram: o {nome_rejeita} rejeitou H₀ "
            f"(p = {p_valor(quem_rejeita.p_valor)}) e o {nome_nao} não "
            f"(p = {p_valor(quem_nao.p_valor)})"
            + (
                ", o que combina com o Welch conservador e com pouco poder que vimos "
                "nas simulações."
                if quem_nao is w
                else "."
            )
        )
    else:
        decisao = "rejeitaram" if m.rejeita_h0 else "não rejeitaram"
        frases.append(
            f"Os dois testes {decisao} H₀ (Mann-Whitney com p = {p_valor(m.p_valor)} e "
            f"Welch com p = {p_valor(w.p_valor)})."
        )
    frases.append(
        f"O efeito é grande na prática: em {porcentagem(m.prob_superioridade, 0)} dos pares o "
        f"PR com bot demorou mais e, pelo log do tempo, os PRs com bot são "
        f"{numero(resultado.razao_geometrica, 1)} vezes mais lentos"
        + (f" (Welch no log com p = {p_valor(wl.p_valor)})." if wl.rejeita_h0 else ".")
    )
    frases.append(
        "Como o estudo é observacional e os PRs com bot também são maiores, essa diferença "
        "não pode ser atribuída só ao bot."
    )
    return " ".join(frases)
