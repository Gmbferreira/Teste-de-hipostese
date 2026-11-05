"""Textos curtos que acompanham os gráficos das simulações no dashboard (issue #19).

Os textos são montados a partir dos resultados, para continuarem certos quando
o α muda no dashboard. Um teste fica "perto de α" quando a taxa cai dentro da
variação esperada só pelo acaso com 10.000 repetições, o critério registrado em
docs/expectativa.md. Para não chamar de desvio um ponto que só encostou na
borda da faixa, ele também precisa ter um intervalo de 95% que não contenha α.
"""

from __future__ import annotations

import pandas as pd

from src.formatacao import numero, porcentagem
from src.monte_carlo import margem_esperada
from src.situacoes import POR_CHAVE
from src.testes_estatisticos import tamanho_exato_mann_whitney

PERTO, CONSERVADOR, LIBERAL = "perto", "conservador", "liberal"

# Como cada situação aparece no meio de uma frase.
NA_FRASE = {
    "realista": "na situação realista",
    "amostras_pequenas": "com amostras pequenas",
    "desbalanceado": "com grupos desbalanceados",
    "outliers": "com outliers",
    "escala_log": "na escala log",
}


def classificar(
    taxa: float, ic95: tuple[float, float], alpha: float, margem: float
) -> str:
    """Perto de α, abaixo (conservador) ou acima (liberal)."""
    inferior, superior = ic95
    if abs(taxa - alpha) <= margem or inferior <= alpha <= superior:
        return PERTO
    return CONSERVADOR if taxa < alpha else LIBERAL


def _taxa(valor: float) -> str:
    return porcentagem(valor, 2 if valor < 0.01 else 1)


def _juntar(itens: list[str]) -> str:
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def _maiuscula(frase: str) -> str:
    return frase[:1].upper() + frase[1:]


def _por_classe(tabela: pd.DataFrame, teste: str, alpha: float, margem: float) -> dict[str, list]:
    classes: dict[str, list] = {PERTO: [], CONSERVADOR: [], LIBERAL: []}
    for linha in tabela[tabela["teste"] == teste].itertuples():
        classe = classificar(
            linha.taxa, (linha.ic95_inferior, linha.ic95_superior), alpha, margem
        )
        classes[classe].append((linha.situacao, linha.taxa))
    return classes


def _frase_mann_whitney(tabela: pd.DataFrame, classes: dict[str, list], alpha: float) -> str:
    alvo = porcentagem(alpha, 0)
    taxas = tabela.loc[tabela["teste"] == "mann_whitney", "taxa"]
    faixa = f"entre {_taxa(taxas.min())} e {_taxa(taxas.max())}"
    if not classes[CONSERVADOR] and not classes[LIBERAL]:
        return (
            f"O **Mann-Whitney** ficou perto de {alvo} em todas as situações, {faixa}, "
            "porque com H₀ verdadeira a distribuição de U não depende da forma dos dados."
        )
    desvios = []
    for chave, taxa in classes[CONSERVADOR] + classes[LIBERAL]:
        situacao = POR_CHAVE[chave]
        desvio = f"{NA_FRASE[chave]} ({_taxa(taxa)})"
        exato = tamanho_exato_mann_whitney(situacao.n_com, situacao.n_sem, alpha)
        if taxa < alpha and exato < 0.95 * alpha:
            desvio += (
                f", porque com {situacao.n_com} × {situacao.n_sem} PRs o U assume poucos "
                f"valores e o teste exato rejeita no máximo {_taxa(exato)} das vezes"
            )
        desvios.append(desvio)
    return f"O **Mann-Whitney** ficou {faixa} e só se afastou de {alvo} {_juntar(desvios)}."


def texto_erro_tipo_i(tabela: pd.DataFrame) -> str:
    """Texto do G3 (2 a 4 frases): se cada teste ficou perto de α e qual se desviou."""
    alpha = float(tabela["alpha"].iloc[0])
    margem = margem_esperada(alpha, int(tabela["repeticoes"].iloc[0]))
    alvo = porcentagem(alpha, 0)
    mw = _por_classe(tabela, "mann_whitney", alpha, margem)
    welch = _por_classe(tabela, "welch", alpha, margem)

    frases = [_frase_mann_whitney(tabela, mw, alpha)]

    if welch[PERTO]:
        chaves = [c for c, _ in welch[PERTO]]
        extra = ", onde os dados são normais" if chaves == ["escala_log"] else ""
        frases.append(
            f"O **t de Welch** só ficou perto de {alvo} "
            f"{_juntar([NA_FRASE[c] for c in chaves])}{extra}."
        )

    if welch[CONSERVADOR]:
        itens = [f"{_taxa(t)} {NA_FRASE[c]}" for c, t in welch[CONSERVADOR]]
        sujeito = "nos tempos em horas ele" if welch[PERTO] else "o **t de Welch**"
        frases.append(
            _maiuscula(
                f"{sujeito} foi conservador e rejeitou H₀ menos do que deveria "
                f"({_juntar(itens)}), porque os PRs muito lentos inflam o desvio-padrão "
                "e o t raramente fica grande."
            )
        )

    desbalanceado = [(c, t) for c, t in welch[LIBERAL] if c == "desbalanceado"]
    outros = [(c, t) for c, t in welch[LIBERAL] if c != "desbalanceado"]
    if desbalanceado:
        taxa = desbalanceado[0][1]
        inicio = "já " if welch[CONSERVADOR] else ""
        frases.append(
            _maiuscula(
                f"{inicio}com grupos desbalanceados ele rejeitou H₀ em {_taxa(taxa)} dos "
                f"casos, {numero(taxa / alpha, 1)} vezes α, porque o grupo de 10 PRs domina "
                "a estatística e o t fica assimétrico."
            )
        )
    if outros:
        partes = []
        for chave, taxa in outros:
            if taxa / alpha < 1.5:
                partes.append(f"{NA_FRASE[chave]} ele ficou um pouco acima de α ({_taxa(taxa)})")
            else:
                partes.append(
                    f"{NA_FRASE[chave]} ele rejeitou H₀ em {_taxa(taxa)} dos casos, "
                    f"{numero(taxa / alpha, 1)} vezes α"
                )
        frases.append(_maiuscula(f"{_juntar(partes)}."))

    return " ".join(frases)
