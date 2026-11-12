"""Textos curtos do dashboard (issues #7, #19 e #21).

As seções 1 e 2 usam ``texto_cenario`` e ``texto_dados``; a seção 4 usa
``texto_erro_tipo_i`` e a seção 5 usa ``texto_poder``. Os textos são montados a partir dos resultados, para
continuarem certos quando o α muda no dashboard. Um teste fica "perto de α"
quando a taxa cai dentro da variação esperada só pelo acaso com 10.000
repetições, o critério registrado em docs/expectativa.md. Para não chamar de
desvio um ponto que só encostou na borda da faixa, ele também precisa ter um
intervalo de 95% que não contenha α.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import ALPHA, SEED
from src.dados_reais import carregar_grupos
from src.formatacao import numero, porcentagem
from src.monte_carlo import margem_esperada
from src.parametros import (
    DELTA_MU_OBSERVADO,
    GRUPO_CONTROLE,
    PARAMETROS_REAIS,
    RAZAO_GEOMETRICA_OBSERVADA,
)
from src.simulacao import N_POR_GRUPO
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
    "reamostragem": "com os tempos reais reamostrados",
}


def texto_cenario(alpha: float = ALPHA) -> str:
    """Texto da seção 1: pergunta, hipóteses, teste e erros no cenário."""
    alvo = porcentagem(alpha, 0)
    return (
        "**Pergunta:** a revisão feita por um bot muda o tempo que um pull request "
        "leva da abertura até o merge? Comparamos 35 PRs com review do CodeRabbit e "
        "35 sem review de bot no repositório `supabase/supabase`.\n\n"
        "**H₀:** a review do bot não muda o tempo até o merge; os dois grupos têm a "
        "mesma distribuição. **H₁:** a review do bot muda o tempo; um dos grupos "
        "tende a demorar mais.\n\n"
        "| | t de Welch | Mann-Whitney |\n"
        "|---|---|---|\n"
        "| **H₀** | $E[T_{bot}] = E[T_{sem}]$ | "
        "$P(T_{bot} > T_{sem}) = 1/2$ |\n"
        "| **H₁** | $E[T_{bot}] \\neq E[T_{sem}]$ | "
        "$P(T_{bot} > T_{sem}) \\neq 1/2$ |\n\n"
        f"Usamos testes **bicaudais** com α = {alvo}: antes de olhar os dados, as "
        "duas direções eram plausíveis (o bot pode acelerar ou atrasar o merge), e "
        "escolher a cauda depois da coleta cortaria o p-valor pela metade.\n\n"
        "**Erro tipo I:** concluir que o bot muda o tempo quando ele não muda. "
        "**Erro tipo II:** não detectar uma mudança que existe. O cenário completo, "
        "com a justificativa e as limitações, está em "
        "[`docs/cenario.md`](https://github.com/Gmbferreira/Teste-de-hipostese/"
        "blob/main/docs/cenario.md)."
    )


def _contar_outliers_iqr(x: np.ndarray) -> int:
    """Número de valores fora de Q1 - 1,5×IQR e Q3 + 1,5×IQR."""
    q1, q3 = np.percentile(x, [25, 75])
    iqr = q3 - q1
    return int(np.count_nonzero((x < q1 - 1.5 * iqr) | (x > q3 + 1.5 * iqr)))


def texto_dados() -> str:
    """Texto da seção 2 (2 a 4 frases): assimetria, outliers e parâmetros."""
    com_bot, sem_bot = carregar_grupos()
    controle = PARAMETROS_REAIS[GRUPO_CONTROLE]
    n_com = len(com_bot)
    n_sem = len(sem_bot)
    med_com = float(np.median(com_bot))
    med_sem = float(np.median(sem_bot))
    media_com = float(np.mean(com_bot))
    media_sem = float(np.mean(sem_bot))
    max_com = float(np.max(com_bot))
    max_sem = float(np.max(sem_bot))
    out_com = _contar_outliers_iqr(com_bot)
    out_sem = _contar_outliers_iqr(sem_bot)

    return (
        f"Os {n_com + n_sem} PRs reais ({n_com} com bot e {n_sem} sem bot) são "
        "fortemente assimétricos à direita: as medianas são "
        f"{numero(med_com, 1)} h e {numero(med_sem, 1)} h, as médias "
        f"{numero(media_com, 1)} h e {numero(media_sem, 1)} h e os máximos "
        f"{numero(max_com, 1)} h e {numero(max_sem, 1)} h. "
        f"Pelo critério de 1,5×IQR há {out_com} outliers com bot e {out_sem} "
        "sem bot; mantivemos esses valores no ajuste para preservar a cauda. "
        "Por isso modelamos o tempo como uma lognormal ajustada por máxima "
        "verossimilhança ao grupo sem bot "
        f"(μ={numero(controle.mu, 2)}, σ={numero(controle.sigma, 2)}), o controle, "
        f"com {N_POR_GRUPO} PRs por grupo. "
        "Os dados simulados usam essa lognormal e o efeito observado "
        f"δ={numero(DELTA_MU_OBSERVADO, 2)} "
        f"(razão geométrica {numero(RAZAO_GEOMETRICA_OBSERVADA, 2)}×), "
        "reproduzindo a assimetria e a cauda longa; o G1 compara os dois "
        f"conjuntos com a semente {SEED}."
    )


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
        taxas = {c: t for classe in welch.values() for c, t in classe}
        cauda = ""
        if {"reamostragem", "realista"} <= set(taxas) and abs(
            taxas["reamostragem"] - alpha
        ) < abs(taxas["realista"] - alpha):
            cauda = (
                "; como a lognormal gera PRs mais lentos que os reais, com a cauda da "
                "amostra esse desvio fica bem menor"
            )
        frases.append(
            _maiuscula(
                f"{sujeito} foi conservador e rejeitou H₀ menos do que deveria "
                f"({_juntar(itens)}), porque os PRs muito lentos inflam o desvio-padrão "
                f"e o t raramente fica grande{cauda}."
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


# ---------------------------------------------------------------------------
# Seção 5: poder (issue #21)
# ---------------------------------------------------------------------------
# Diferença de poder abaixo da qual os dois testes são tratados como empatados
# (meio ponto percentual, perto do erro-padrão de uma taxa de 10.000 repetições).
EMPATE_PODER = 0.005

NOMES_TESTE = {"welch": "t de Welch", "mann_whitney": "Mann-Whitney"}


def efeito_mais_perto_do_observado(tabela: pd.DataFrame) -> float:
    """O δ da grade mais perto do efeito observado nos dados reais."""
    efeitos = np.array(sorted(tabela.loc[tabela["delta_mu"] > 0, "delta_mu"].unique()))
    return float(efeitos[np.argmin(np.abs(efeitos - DELTA_MU_OBSERVADO))])


def _curvas(tabela: pd.DataFrame, chave: str) -> pd.DataFrame:
    """Poder dos dois testes por efeito numa situação (colunas welch e mann_whitney)."""
    do_caso = tabela[tabela["situacao"] == chave]
    return do_caso.pivot(index="delta_mu", columns="teste", values="taxa").sort_index()


def _quem_lidera(curvas: pd.DataFrame, liberal: bool) -> pd.Series:
    """Para cada δ > 0: o teste com mais poder, ou None se empatarem.

    Quando o Welch já rejeita H₀ demais sem efeito (`liberal`), a vantagem dele não
    é poder de verdade e não conta.
    """
    lider = {}
    for delta, linha in curvas[curvas.index > 0].iterrows():
        diferenca = linha["welch"] - linha["mann_whitney"]
        if abs(diferenca) < EMPATE_PODER or (diferenca > 0 and liberal):
            lider[delta] = None
        else:
            lider[delta] = "welch" if diferenca > 0 else "mann_whitney"
    return pd.Series(lider, dtype=object)


def _welch_inflado(tabela: pd.DataFrame, chave: str, alpha: float, margem: float) -> bool:
    """O Welch já rejeita H₀ demais sem efeito: liberal e acima do Mann-Whitney."""
    zero = tabela[(tabela["situacao"] == chave) & (tabela["delta_mu"] == 0)].set_index("teste")
    if not {"welch", "mann_whitney"} <= set(zero.index):
        return False
    welch = zero.loc["welch"]
    ic95 = (welch["ic95_inferior"], welch["ic95_superior"])
    acima_do_mw = welch["taxa"] - zero.loc["mann_whitney", "taxa"] > EMPATE_PODER
    return acima_do_mw and classificar(welch["taxa"], ic95, alpha, margem) == LIBERAL


def _onde_o_outro_lidera(lideres: pd.Series, outro: str) -> str | None:
    """Em que efeitos o `outro` teste fica na frente (None se em nenhum); empates não contam."""
    definidos = lideres.dropna()
    na_frente = [d for d, teste in definidos.items() if teste == outro]
    if not na_frente:
        return None
    if len(na_frente) == len(definidos):
        return "em todos os efeitos"
    if na_frente == [d for d in definidos.index if d >= na_frente[0]]:
        return f"a partir de δ = {numero(na_frente[0])}"
    if na_frente == [d for d in definidos.index if d <= na_frente[-1]]:
        return f"até δ = {numero(na_frente[-1])}"
    return "em parte dos efeitos"


def texto_poder(tabela: pd.DataFrame) -> str:
    """Texto do G4 (2 a 4 frases): qual teste tem mais poder e onde a vantagem muda de lado.

    A tabela é a de `dados_g4`: uma linha por situação, efeito e teste.
    """
    alpha = float(tabela["alpha"].iloc[0])
    margem = margem_esperada(alpha, int(tabela["repeticoes"].iloc[0]))
    delta = efeito_mais_perto_do_observado(tabela)
    chaves = list(dict.fromkeys(tabela["situacao"]))
    referencia = "realista" if "realista" in chaves else chaves[0]

    curvas_ref = _curvas(tabela, referencia)
    no_efeito = curvas_ref.loc[delta]
    lider = "mann_whitney" if no_efeito["mann_whitney"] >= no_efeito["welch"] else "welch"
    outro = "welch" if lider == "mann_whitney" else "mann_whitney"
    lideres_ref = _quem_lidera(curvas_ref, _welch_inflado(tabela, referencia, alpha, margem))
    em_todos = (lideres_ref.dropna() == lider).all()

    perto = f" (δ = {numero(delta)}, perto do efeito observado)"
    frases = [
        f"{_maiuscula(NA_FRASE.get(referencia, referencia))}, o **{NOMES_TESTE[lider]}** "
        f"detecta o efeito com mais frequência que o **{NOMES_TESTE[outro]}** "
        f"{'em todos os tamanhos de efeito' if em_todos else 'na maior parte dos efeitos'}: "
        f"com PRs {numero(np.exp(delta), 1)} vezes mais lentos{perto}, ele rejeita H₀ em "
        f"{porcentagem(no_efeito[lider], 1)} dos conjuntos, contra "
        f"{porcentagem(no_efeito[outro], 1)} do {NOMES_TESTE[outro].split()[-1]}."
    ]

    mantem, inflados, mudam = [], [], []
    nome_outro = NOMES_TESTE[outro].split()[-1]
    for chave in chaves:
        if chave == referencia:
            continue
        curvas = _curvas(tabela, chave)
        inflado = _welch_inflado(tabela, chave, alpha, margem)
        onde = _onde_o_outro_lidera(_quem_lidera(curvas, inflado), outro)
        if onde is None:
            welch = curvas["welch"]
            caiu = (welch[welch.index > 0] < welch.iloc[0]).any()
            (inflados if inflado and caiu else mantem).append(NA_FRASE.get(chave, chave))
        elif onde == "em todos os efeitos":
            diferenca = curvas[outro] - curvas[lider]
            maior = 100 * float(diferenca[diferenca.index > 0].max())
            unidade = "pontos percentuais" if round(maior, 1) >= 2 else "ponto percentual"
            mudam.append(
                f"{NA_FRASE.get(chave, chave)}, onde o {nome_outro} fica até "
                f"{numero(maior, 1)} {unidade} à frente"
            )
        else:
            mudam.append(
                f"{NA_FRASE.get(chave, chave)}, onde o {nome_outro} passa na frente {onde}"
            )

    if mantem or inflados:
        frase = "A vantagem se mantém " + _juntar(mantem) if mantem else "A vantagem se mantém"
        if inflados:
            frase += (
                (", e também " if mantem else " ")
                + _juntar(inflados)
                + ", onde o Welch rejeita H₀ demais sem efeito e chega a rejeitar menos "
                "com efeito do que sem"
            )
        frases.append(frase + ".")
    if mudam:
        # Cada item já tem vírgula dentro, então os itens são separados por ", e ".
        frases.append(f"Ela só muda de lado {', e '.join(mudam)}.")
    else:
        frases.append("Em nenhuma situação a vantagem muda de lado.")
    return " ".join(frases)
