"""Os dois testes aplicados aos dados reais coletados (issue #22).

Usa as mesmas funções da issue #11 nos 70 PRs de data/prs_merge_time.csv e
monta a tabela e o texto da seção 6 do dashboard. Como referência, o Welch
também é aplicado ao log do tempo, a situação em que as simulações mostraram
que ele funciona bem.

Para a discussão sobre tamanho da amostra (opcional no enunciado), o módulo
também estima o poder de cada teste no efeito observado, para vários tamanhos
de grupo, com os dois modelos de dados: a lognormal ajustada e a reamostragem
dos tempos reais.

Uso (gera resultados/poder_tamanho_amostra.csv, lido pelo dashboard):
    python -m src.dados_reais
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ALPHA, N_SIMULACOES, SEED
from src.formatacao import numero, p_valor, porcentagem
from src.monte_carlo import PASTA_RESULTADOS, REALISTA, salvar_csv, simular, tabela_rejeicoes
from src.parametros import DELTA_MU_OBSERVADO
from src.situacoes import REAMOSTRAGEM
from src.testes_estatisticos import (
    ResultadoMannWhitney,
    ResultadoWelch,
    aplicar_mann_whitney,
    aplicar_welch,
)

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data" / "prs_merge_time.csv"
SAIDA_PODER_TAMANHO = PASTA_RESULTADOS / "poder_tamanho_amostra.csv"

# Tamanhos de grupo usados para estimar o poder no efeito observado.
TAMANHOS = (35, 50, 70, 100, 150, 200, 300, 400)
MODELOS = {
    "lognormal": REALISTA,
    "reamostragem": REAMOSTRAGEM,
}
NOME_DO_MODELO = {
    "lognormal": "lognormal ajustada",
    "reamostragem": "tempos reais reamostrados",
}


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
                    f"P(PR com bot demorar mais) = {numero(m.prob_superioridade)}, efeito "
                    f"{m.magnitude} (r = {numero(m.correlacao_bisserial)}; diferença "
                    f"típica de {numero(m.hodges_lehmann, 1)} h)"
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
                "nas simulações com a lognormal."
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
    conector = "e" if m.magnitude == "grande" else "mas"
    frases.append(
        f"Pela escala de Vargha e Delaney o efeito é {m.magnitude} (em "
        f"{porcentagem(m.prob_superioridade, 0)} dos pares o PR com bot demorou mais), "
        f"{conector} na prática ele pesa: pelo log do tempo, os PRs com bot são "
        f"{numero(resultado.razao_geometrica, 1)} vezes mais lentos"
        + (f" (Welch no log com p = {p_valor(wl.p_valor)})." if wl.rejeita_h0 else ".")
    )
    frases.append(
        "Como o estudo é observacional e os PRs com bot também são maiores, essa diferença "
        "não pode ser atribuída só ao bot."
    )
    return " ".join(frases)


def poder_por_tamanho(
    tamanhos: tuple[int, ...] = TAMANHOS,
    delta_mu: float = DELTA_MU_OBSERVADO,
    repeticoes: int = N_SIMULACOES,
    semente: int = SEED,
    alpha: float = ALPHA,
) -> pd.DataFrame:
    """Poder dos dois testes no efeito observado, por tamanho de grupo e modelo."""
    partes = []
    for chave, situacao in MODELOS.items():
        simulacoes = [
            simular(replace(situacao, n_com=n, n_sem=n), delta_mu, repeticoes, semente)
            for n in tamanhos
        ]
        tabela = tabela_rejeicoes(simulacoes, alpha)
        tabela.insert(0, "modelo", chave)
        tabela.insert(1, "n_por_grupo", [n for n in tamanhos for _ in range(2)])
        partes.append(tabela.drop(columns="situacao"))
    return pd.concat(partes, ignore_index=True)


def carregar_poder_por_tamanho() -> pd.DataFrame:
    """Lê o CSV gerado por `python -m src.dados_reais`; sem ele, faz as contas."""
    if SAIDA_PODER_TAMANHO.exists():
        return pd.read_csv(SAIDA_PODER_TAMANHO)
    return poder_por_tamanho()


def n_para_poder(
    tabela: pd.DataFrame, modelo: str, teste: str, alvo: float = 0.8
) -> float | None:
    """Tamanho de grupo em que o poder chega ao alvo, interpolando entre os pontos.

    Devolve None quando nem o maior tamanho simulado chega lá.
    """
    curva = tabela[(tabela["modelo"] == modelo) & (tabela["teste"] == teste)]
    curva = curva.sort_values("n_por_grupo")
    n, poder = curva["n_por_grupo"].to_numpy(float), curva["taxa"].to_numpy(float)
    if poder[0] >= alvo:
        return float(n[0])
    for i in range(1, len(n)):
        if poder[i] >= alvo:
            fracao = (alvo - poder[i - 1]) / (poder[i] - poder[i - 1])
            return float(n[i - 1] + fracao * (n[i] - n[i - 1]))
    return None


def _n_em_texto(n: float | None, maior: int) -> str:
    return f"mais de {maior}" if n is None else f"cerca de {round(n)}"


def tabela_tamanho_amostra(tabela: pd.DataFrame) -> pd.DataFrame:
    """Poder com 35 PRs por grupo e PRs por grupo para 80% de poder, por modelo."""
    maior = int(tabela["n_por_grupo"].max())
    linhas = []
    for modelo in MODELOS:
        no_real = tabela[(tabela["modelo"] == modelo) & (tabela["n_por_grupo"] == 35)]
        por_teste = no_real.set_index("teste")["taxa"]
        linhas.append(
            {
                "Modelo dos dados": NOME_DO_MODELO[modelo],
                "Poder com 35 por grupo: t de Welch": porcentagem(por_teste["welch"], 0),
                "Poder com 35 por grupo: Mann-Whitney": porcentagem(por_teste["mann_whitney"], 0),
                "PRs por grupo para 80%: t de Welch": _n_em_texto(
                    n_para_poder(tabela, modelo, "welch"), maior
                ),
                "PRs por grupo para 80%: Mann-Whitney": _n_em_texto(
                    n_para_poder(tabela, modelo, "mann_whitney"), maior
                ),
            }
        )
    return pd.DataFrame(linhas)


def texto_tamanho_amostra(tabela: pd.DataFrame, resultado: ResultadoDadosReais) -> str:
    """Texto curto sobre poder e tamanho da amostra (perguntas da seção 6 do enunciado)."""
    maior = int(tabela["n_por_grupo"].max())

    def poder(modelo: str, teste: str) -> str:
        linha = tabela[
            (tabela["modelo"] == modelo) & (tabela["teste"] == teste) & (tabela["n_por_grupo"] == 35)
        ]
        return porcentagem(float(linha["taxa"].iloc[0]), 0)

    def n80(modelo: str, teste: str) -> str:
        n = n_para_poder(tabela, modelo, teste)
        return f"mais de {maior}" if n is None else f"uns {round(n)}"

    frases = [
        f"Com o efeito observado (δ = {numero(DELTA_MU_OBSERVADO)}) e 35 PRs por grupo, o "
        f"poder depende do modelo: na lognormal o Welch rejeitaria H₀ em {poder('lognormal', 'welch')} "
        f"das amostras e o Mann-Whitney em {poder('lognormal', 'mann_whitney')}, e com os tempos "
        f"reais reamostrados os dois ficam em {poder('reamostragem', 'welch')} e "
        f"{poder('reamostragem', 'mann_whitney')}."
    ]
    if not resultado.welch.rejeita_h0:
        frases.append(
            f"Então o p = {p_valor(resultado.welch.p_valor)} do Welch não mostra que o bot "
            "não muda o tempo: com esse tamanho de amostra, deixar de ver o efeito era "
            "bem possível."
        )
    frases.append(
        f"Para chegar a 80% de poder seriam precisos {n80('lognormal', 'mann_whitney')} PRs por "
        f"grupo no Mann-Whitney e {n80('lognormal', 'welch')} no Welch com a lognormal, ou "
        f"{n80('reamostragem', 'mann_whitney')} e {n80('reamostragem', 'welch')} com a cauda "
        "real; como o repositório teve 160 PRs mergeados em cerca de 8 dias, juntar PRs "
        "suficientes para o Mann-Whitney levaria poucas semanas."
    )
    return " ".join(frases)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=SAIDA_PODER_TAMANHO)
    args = parser.parse_args()

    tabela = poder_por_tamanho()
    salvar_csv(tabela, args.saida)
    for modelo in MODELOS:
        for teste in ("welch", "mann_whitney"):
            n = n_para_poder(tabela, modelo, teste)
            print(f"{modelo:<13} {teste:<13} n para 80% = {'-' if n is None else round(n)}")
    print(f"Resultado salvo em {args.saida}")


if __name__ == "__main__":
    main()
