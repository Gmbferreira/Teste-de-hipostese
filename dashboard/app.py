"""Dashboard do Laboratório 04 — Testes de Hipótese.

Esqueleto com as 7 seções exigidas na ordem oficial. As seções são
preenchidas pelas issues seguintes (#8, #5, #7, #12, #13 e Sprint 02).
"""

import math
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

# O `streamlit run` só coloca a pasta dashboard/ no caminho de importação.
# A raiz do repositório entra aqui para o dashboard usar o código de src/.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from src.dados_reais import analisar, tabela_dados_reais, texto_dados_reais  # noqa: E402
from src.exemplo import gerar_exemplo, interpretacao, pr_mais_lento, tabela_resultados  # noqa: E402
from src.formatacao import numero, p_valor, porcentagem  # noqa: E402
from src.grafico_g2 import grafico_g2  # noqa: E402
from src.grafico_g3 import grafico_g3  # noqa: E402
from src.monte_carlo import simular, tabela_rejeicoes  # noqa: E402
from src.situacoes import POR_CHAVE, TODAS_AS_SITUACOES  # noqa: E402
from src.textos import texto_erro_tipo_i  # noqa: E402

REPOSITORIO_URL = "https://github.com/Gmbferreira/Teste-de-hipostese"
PROJECTS_URL = "https://github.com/users/Gmbferreira/projects/4"
DASHBOARD_URL: str | None = None  # preencher quando o dashboard for publicado

st.set_page_config(
    page_title="Testes de Hipótese — Tempo até o merge de PRs",
    page_icon="📊",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------------------
st.title("Testes de Hipótese — Tempo até o merge de PRs")

dashboard_link = f"[Dashboard]({DASHBOARD_URL})" if DASHBOARD_URL else "**Dashboard:** em breve"
st.markdown(
    f"[Repositório]({REPOSITORIO_URL}) · "
    f"[GitHub Projects]({PROJECTS_URL}) · "
    f"{dashboard_link}"
)

st.caption(
    "Par de testes: **t de Welch × Mann-Whitney** · "
    "Cenário: tempo até o merge de pull requests com e sem bot de revisão."
)

st.divider()

# ---------------------------------------------------------------------------
# 1. Cenário
# ---------------------------------------------------------------------------
st.header("1. Cenário")
st.info("Em construção — pergunta, H₀ e H₁ entram na issue #8.")

# ---------------------------------------------------------------------------
# 2. Os dados
# ---------------------------------------------------------------------------
st.header("2. Os dados")
st.info(
    "Em construção — dados reais (#3 e #4) e gráfico G1 (#5), "
    "integrados na issue #7."
)

# ---------------------------------------------------------------------------
# 3. Como os testes funcionam (issues #11, #12 e #13)
# ---------------------------------------------------------------------------
st.header("3. Como os testes funcionam")


def texto_como_os_testes_funcionam(exemplo) -> str:
    """Texto do G2: o que cada teste compara, a região de rejeição e o p-valor."""
    w, m = exemplo.welch, exemplo.mann_whitney
    inferior, superior = m.regiao_rejeicao
    total = len(exemplo.com_bot) + len(exemplo.sem_bot)

    def resultado(r, nome: str) -> str:
        decisao = "rejeitou H₀" if r.rejeita_h0 else "não rejeitou H₀"
        return f"o {nome} {decisao} (p = {p_valor(r.p_valor)})"

    if exemplo.h0_verdadeira:
        cenario = "um conjunto simulado sem efeito"
    else:
        vezes = numero(math.exp(exemplo.delta_mu))
        cenario = f"um conjunto simulado em que os PRs com bot são {vezes} vezes mais lentos"

    lento = pr_mais_lento(exemplo)
    motivo = ""
    if lento.mudou_a_decisao_do_welch(w) and not w.rejeita_h0:
        motivo = (
            f", porque um único PR de {numero(lento.tempo, 0)} h inflou a média e o "
            f"desvio-padrão do grupo {lento.grupo}"
        )

    return (
        "O **t de Welch** compara as médias dos dois grupos, e o **Mann-Whitney** "
        "compara os postos, isto é, se os PRs com bot tendem a ficar no fim quando os "
        f"{total} tempos são colocados em ordem. Como o teste é bicaudal, a região de "
        "rejeição (faixa cinza) fica nas duas pontas da distribuição de cada estatística "
        f"sob H₀ e soma 5%: |t| > {numero(w.t_critico)} no Welch e "
        f"U ≤ {numero(inferior, 0)} ou U ≥ {numero(superior, 0)} no Mann-Whitney. "
        "O p-valor é a área pintada: a chance de, sem efeito nenhum, sair uma "
        "estatística tão afastada do centro quanto a do exemplo, e não a chance de H₀ "
        f"ser verdadeira. No exemplo, {cenario}, {resultado(m, 'Mann-Whitney')} e "
        f"{resultado(w, 'Welch')}{motivo}."
    )


exemplo = gerar_exemplo()
st.markdown(texto_como_os_testes_funcionam(exemplo))

st.pyplot(
    grafico_g2(exemplo),
    alt=(
        "G2: distribuição t de Welch e distribuição exata de U de Mann-Whitney sob H₀, "
        "com a região de rejeição em cinza e o p-valor do exemplo como área pintada."
    ),
)

st.markdown("**Resultado dos dois testes no conjunto de exemplo**")
st.table(tabela_resultados(exemplo).set_index("Teste"))
with st.expander("Interpretação completa do exemplo"):
    st.markdown(interpretacao(exemplo))

# ---------------------------------------------------------------------------
# 4. Erro tipo I (issues #14, #16, #18 e #19)
# ---------------------------------------------------------------------------
st.header("4. Erro tipo I")


@st.cache_resource(show_spinner="Rodando 10.000 conjuntos com H₀ verdadeira em cada situação...")
def simulacoes_com_h0():
    """P-valores dos dois testes com δ = 0 na situação realista (Q1) e nas de Q3."""
    return [simular(situacao, 0.0) for situacao in TODAS_AS_SITUACOES]


def tabela_erro_tipo_i_para_exibir(tabela):
    """Uma linha por situação, com a taxa e o IC de 95% de cada teste."""
    linhas = []
    for chave, grupo in tabela.groupby("situacao", sort=False):
        linha = {"Situação": POR_CHAVE[chave].nome}
        for teste, rotulo in (("welch", "t de Welch"), ("mann_whitney", "Mann-Whitney")):
            r = grupo[grupo["teste"] == teste].iloc[0]
            linha[rotulo] = (
                f"{porcentagem(r.taxa, 2)} "
                f"({porcentagem(r.ic95_inferior, 2)} a {porcentagem(r.ic95_superior, 2)})"
            )
        linhas.append(linha)
    return linhas


alpha_g3 = st.radio(
    "Nível de significância (α)",
    options=[0.05, 0.01],
    format_func=lambda a: porcentagem(a, 0),
    horizontal=True,
    key="alpha_erro_tipo_i",
    help="Com 1% a região de rejeição encolhe; compare as duas opções no G3.",
)
tabela_g3 = tabela_rejeicoes(simulacoes_com_h0(), alpha_g3)
st.markdown(texto_erro_tipo_i(tabela_g3))
st.pyplot(
    grafico_g3(tabela_g3),
    alt=(
        "G3: erro tipo I do t de Welch e do Mann-Whitney em cada situação simulada, "
        "com intervalo de 95% e uma linha vertical em α."
    ),
)
st.markdown(
    f"**Erro tipo I com α = {porcentagem(alpha_g3, 0)}** "
    "(10.000 conjuntos por situação, intervalo de 95% entre parênteses)"
)
st.table(pd.DataFrame(tabela_erro_tipo_i_para_exibir(tabela_g3)).set_index("Situação"))
with st.expander("Como cada situação foi simulada"):
    st.markdown(
        "| Situação | O que muda | Por que incluímos |\n|---|---|---|\n"
        + "\n".join(
            f"| {s.nome} | {s.descricao} | {s.motivo} |" for s in TODAS_AS_SITUACOES
        )
        + "\n\nTodas as situações usam a mesma semente, então os sorteios de base são "
        "os mesmos e a diferença entre elas vem só do que foi alterado. As situações "
        "foram registradas na expectativa antes de simular."
    )

# ---------------------------------------------------------------------------
# 5. Poder
# ---------------------------------------------------------------------------
st.header("5. Poder")
st.info(
    "Em construção — Sprint 02: simulações de Q2 e Q3 e gráfico G4."
)

# ---------------------------------------------------------------------------
# 6. Dados reais (issue #22)
# ---------------------------------------------------------------------------
st.header("6. Dados reais")
resultado_real = analisar()
st.markdown(texto_dados_reais(resultado_real))
st.markdown(
    "**Os dois testes nos dados coletados** "
    "(35 PRs com bot e 35 sem bot do `supabase/supabase`, α = 5% bicaudal)"
)
st.table(tabela_dados_reais(resultado_real).set_index("Teste"))
st.caption(
    "A última linha é só referência: o Welch aplicado ao log do tempo, a situação em que "
    "ele ficou perto de 5% nas simulações. A diferença típica do Mann-Whitney é a "
    "mediana das diferenças entre todos os pares (estimador de Hodges-Lehmann)."
)

# ---------------------------------------------------------------------------
# 7. Conclusão
# ---------------------------------------------------------------------------
st.header("7. Conclusão")
st.info(
    "Em construção — Sprint 02: expectativa registrada na #10 × resultados "
    "encontrados, com a recomendação final."
)

st.divider()
st.caption(
    "Laboratório de Experimentação de Software · Engenharia de Software · "
    "Semente fixa: `42` (ver `src/config.py`)."
)
