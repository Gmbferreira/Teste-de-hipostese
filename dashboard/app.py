"""Dashboard do Laboratório 04 — Testes de Hipótese.

As 7 seções seguem a ordem oficial do enunciado. O visual (abertura, números do
estudo, navegação e cartões das seções) fica em dashboard/layout.py, da issue
#26; o conteúdo de cada seção continua vindo das issues de cada uma.
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

from dashboard.layout import (  # noqa: E402
    Numero,
    Secao,
    abertura,
    aplicar_estilo,
    navegacao,
    numeros_do_estudo,
    rodape,
    secao,
)
from src.config import ALPHA, N_SIMULACOES, SEED  # noqa: E402
from src.dados_reais import (  # noqa: E402
    DADOS,
    analisar,
    carregar_poder_por_tamanho,
    tabela_dados_reais,
    tabela_tamanho_amostra,
    texto_dados_reais,
    texto_tamanho_amostra,
)
from src.exemplo import gerar_exemplo, interpretacao, pr_mais_lento, tabela_resultados  # noqa: E402
from src.formatacao import numero, p_valor, porcentagem  # noqa: E402
from src.grafico_g1 import grafico_g1  # noqa: E402
from src.grafico_g2 import estatisticas_sob_h0, grafico_g2  # noqa: E402
from src.grafico_g3 import grafico_g3  # noqa: E402
from src.grafico_g4 import grafico_g4  # noqa: E402
from src.monte_carlo import simular, tabela_rejeicoes  # noqa: E402
from src.parametros import (  # noqa: E402
    DELTA_MU_OBSERVADO,
    GRADE_DELTA_MU_SUGERIDA,
    RAZAO_GEOMETRICA_OBSERVADA,
)
from src.situacoes import POR_CHAVE, TODAS_AS_SITUACOES  # noqa: E402
from src.textos import (  # noqa: E402
    efeito_mais_perto_do_observado,
    texto_cenario,
    texto_dados,
    texto_erro_tipo_i,
    texto_poder,
)

REPOSITORIO_URL = "https://github.com/Gmbferreira/Teste-de-hipostese"
PROJECTS_URL = "https://github.com/users/Gmbferreira/projects/4"
DASHBOARD_URL: str | None = None  # preencher quando o dashboard for publicado

st.set_page_config(
    page_title="Bot de revisão × tempo até o merge",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
aplicar_estilo()

SECOES = [
    Secao(1, "Cenário", "A pergunta, as hipóteses de cada teste e o que seria errar para cada lado.", (1, 2, 8)),
    Secao(2, "Os dados", "Como são os tempos reais e os simulados, e de onde vieram os parâmetros (G1).", (3, 4)),
    Secao(
        3,
        "Como os testes funcionam",
        "A distribuição de cada estatística quando H₀ é verdadeira, num conjunto simulado (G2).",
        (5, 6, 7),
    ),
    Secao(4, "Erro tipo I", "Com que frequência cada teste acusa um efeito que não existe (G3).", (9, 11, 12)),
    Secao(5, "Poder", "Com que frequência cada teste detecta um efeito que existe (G4).", (10, 12)),
    Secao(6, "Dados reais", "Os dois testes nos 70 PRs coletados, com o tamanho do efeito.", (14,)),
    Secao(7, "Conclusão", "O que esperávamos, o que encontramos e qual teste recomendamos.", (13, 15)),
]


# ---------------------------------------------------------------------------
# Simulações guardadas em cache e textos montados a partir dos resultados
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="Simulando 10.000 conjuntos com H₀ verdadeira...")
def estatisticas_do_g2():
    """t e U em 10.000 conjuntos sem efeito, para as barras do G2."""
    return estatisticas_sob_h0()


@st.cache_resource(
    show_spinner="Rodando 10.000 conjuntos por situação e tamanho de efeito (leva alguns segundos)..."
)
def simulacoes_de_poder():
    """P-valores dos dois testes em cada situação e efeito da grade (Q1, Q2 e Q3).

    Rodam uma vez só; trocar o α no dashboard só reconta as rejeições.
    """
    return [
        simular(situacao, delta)
        for situacao in TODAS_AS_SITUACOES
        for delta in GRADE_DELTA_MU_SUGERIDA
    ]


def simulacoes_com_h0():
    """Só as simulações com δ = 0: situação realista (Q1) e as de Q3, para o G3."""
    return [sim for sim in simulacoes_de_poder() if sim.delta_mu == 0]


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
        "rejeição (faixa cinza) fica nas duas pontas e reúne no máximo 5% dos valores "
        f"sob H₀ (|t| > {numero(w.t_critico)}; U ≤ {numero(inferior, 0)} ou "
        f"U ≥ {numero(superior, 0)}), e o p-valor do exemplo é a área pintada: a chance "
        "de sair uma estatística tão extrema sem efeito nenhum, e não a chance de H₀ ser "
        "verdadeira. As barras mostram a estatística em 10.000 conjuntos simulados sem "
        "efeito: no Mann-Whitney elas seguem a curva exata, mas no Welch formam dois "
        "picos perto de ±1 e quase não chegam às pontas, porque um PR muito lento pesa "
        "na média e no desvio-padrão ao mesmo tempo, e por isso o Welch rejeita menos de "
        f"5% no G3. No exemplo, {cenario}, {resultado(m, 'Mann-Whitney')} e "
        f"{resultado(w, 'Welch')}{motivo}."
    )


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


def tabela_poder_para_exibir(tabela, delta: float):
    """Uma linha por situação, com o poder de cada teste no efeito `delta`."""
    no_efeito = tabela[tabela["delta_mu"] == delta]
    linhas = []
    for chave, grupo in no_efeito.groupby("situacao", sort=False):
        taxa = grupo.set_index("teste")["taxa"]
        linhas.append(
            {
                "Situação": POR_CHAVE[chave].nome,
                "t de Welch": porcentagem(taxa["welch"], 1),
                "Mann-Whitney": porcentagem(taxa["mann_whitney"], 1),
                "Diferença (Mann-Whitney − Welch)": (
                    f"{numero(100 * (taxa['mann_whitney'] - taxa['welch']), 1)} p.p."
                ),
            }
        )
    return linhas


def numeros_principais(resultado_real, poder_por_n) -> list[Numero]:
    """Os números do topo, todos calculados a partir dos dados e das simulações."""
    dados = pd.read_csv(DADOS)
    datas = pd.to_datetime(dados["mergeado_em"])
    n_com = int((dados["grupo"] == "com_bot").sum())
    n_sem = int((dados["grupo"] == "sem_bot").sum())

    realista = simulacoes_com_h0()[0]
    tipo_i = {t: realista.proporcao(t, ALPHA).taxa for t in ("welch", "mann_whitney")}

    em_35 = poder_por_n[(poder_por_n["modelo"] == "lognormal") & (poder_por_n["n_por_grupo"] == 35)]
    poder = em_35.set_index("teste")["taxa"]

    w, m = resultado_real.welch, resultado_real.mann_whitney
    rejeitaram = [nome for nome, r in (("t de Welch", w), ("Mann-Whitney", m)) if r.rejeita_h0]
    if len(rejeitaram) == 1:
        nota_real = f"Só o {rejeitaram[0]} rejeitou H₀ com α = {porcentagem(ALPHA, 0)}."
    elif rejeitaram:
        nota_real = f"Os dois rejeitaram H₀ com α = {porcentagem(ALPHA, 0)}."
    else:
        nota_real = f"Nenhum rejeitou H₀ com α = {porcentagem(ALPHA, 0)}."

    return [
        Numero(
            rotulo="Amostra real",
            valor=f"{n_com + n_sem} PRs",
            nota=(
                f"{n_com} com review do CodeRabbit e {n_sem} sem, mergeados entre "
                f"{datas.min():%d/%m} e {datas.max():%d/%m/%Y}."
            ),
        ),
        Numero(
            rotulo="Efeito observado",
            valor=f"{numero(RAZAO_GEOMETRICA_OBSERVADA, 1)}×",
            nota=(
                "PRs com bot mais lentos, pela média geométrica "
                f"(δ = {numero(DELTA_MU_OBSERVADO)})."
            ),
        ),
        Numero(
            rotulo="Erro tipo I",
            por_teste=(
                ("welch", porcentagem(tipo_i["welch"], 1)),
                ("mann_whitney", porcentagem(tipo_i["mann_whitney"], 1)),
            ),
            nota=f"Situação realista, sem efeito. O esperado é {porcentagem(ALPHA, 0)}.",
        ),
        Numero(
            rotulo="Poder com 35 por grupo",
            por_teste=(
                ("welch", porcentagem(poder["welch"], 0)),
                ("mann_whitney", porcentagem(poder["mann_whitney"], 0)),
            ),
            nota="No efeito observado, com o modelo lognormal.",
        ),
        Numero(
            rotulo="Nos dados reais",
            por_teste=(
                ("welch", f"p = {p_valor(w.p_valor)}"),
                ("mann_whitney", f"p = {p_valor(m.p_valor)}"),
            ),
            nota=nota_real,
        ),
    ]


# ---------------------------------------------------------------------------
# Barra lateral, abertura e números do estudo (issue #26)
# ---------------------------------------------------------------------------
resultado_real = analisar()
poder_por_n = carregar_poder_por_tamanho()

navegacao(
    SECOES,
    rodape=(
        f"Semente {SEED} · {numero(N_SIMULACOES, 0)} repetições por ponto · "
        f"α = {porcentagem(ALPHA, 0)}, bicaudal"
    ),
)

abertura(
    chapeu="Laboratório 04 · Laboratório de Experimentação de Software",
    titulo="O bot de revisão muda o tempo até o merge?",
    texto=(
        f"Comparamos o t de Welch e o Mann-Whitney em "
        f"{len(resultado_real.com_bot) + len(resultado_real.sem_bot)} pull requests reais "
        "do supabase/supabase e em conjuntos simulados em que sabemos a resposta certa, "
        "para ver quantas vezes cada teste acerta e erra."
    ),
    etiquetas=[
        "Par P1: t de Welch × Mann-Whitney",
        f"α = {porcentagem(ALPHA, 0)}, bicaudal",
        f"{numero(N_SIMULACOES, 0)} repetições por ponto",
        f"Semente {SEED}",
    ],
    links=[
        ("Repositório", REPOSITORIO_URL),
        ("GitHub Projects", PROJECTS_URL),
        ("Dashboard publicado", DASHBOARD_URL),
    ],
)
numeros_do_estudo("O estudo em números", numeros_principais(resultado_real, poder_por_n))

# ---------------------------------------------------------------------------
# 1. Cenário (issue #7)
# ---------------------------------------------------------------------------
with secao(SECOES[0]):
    st.markdown(texto_cenario())

# ---------------------------------------------------------------------------
# 2. Os dados (issue #7)
# ---------------------------------------------------------------------------
with secao(SECOES[1]):
    st.markdown(texto_dados())
    st.pyplot(
        grafico_g1(),
        alt=(
            "G1: histogramas do tempo até o merge dos grupos com e sem bot, "
            "em dados reais e simulados, em escala logarítmica."
        ),
    )

# ---------------------------------------------------------------------------
# 3. Como os testes funcionam (issues #11, #12 e #13)
# ---------------------------------------------------------------------------
with secao(SECOES[2]):
    exemplo = gerar_exemplo()
    st.markdown(texto_como_os_testes_funcionam(exemplo))

    st.pyplot(
        grafico_g2(exemplo, estatisticas_do_g2()),
        alt=(
            "G2: distribuição t de Welch e distribuição exata de U de Mann-Whitney sob H₀, "
            "com barras da estatística em 10.000 conjuntos simulados sem efeito, a região "
            "de rejeição em cinza e o p-valor do exemplo como área pintada."
        ),
    )

    st.markdown("**Resultado dos dois testes no conjunto de exemplo**")
    st.table(tabela_resultados(exemplo).set_index("Teste"))
    with st.expander("Interpretação completa do exemplo"):
        st.markdown(interpretacao(exemplo))

# ---------------------------------------------------------------------------
# 4. Erro tipo I (issues #14, #16, #18 e #19)
# ---------------------------------------------------------------------------
with secao(SECOES[3]):
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
            "os mesmos e a diferença entre elas vem só do que foi alterado. As quatro "
            "situações de Q3 foram registradas na expectativa antes de simular. A "
            "reamostragem dos tempos reais entrou depois, como análise de sensibilidade: "
            "a lognormal ajustada gera PRs bem mais lentos que os da amostra, e essa "
            "situação mostra o que muda com a cauda real."
        )

# ---------------------------------------------------------------------------
# 5. Poder (issues #15, #20 e #21)
# ---------------------------------------------------------------------------
with secao(SECOES[4]):
    alpha_g4 = st.radio(
        "Nível de significância (α)",
        options=[0.05, 0.01],
        format_func=lambda a: porcentagem(a, 0),
        horizontal=True,
        key="alpha_poder",
        help="Com 1% fica mais difícil rejeitar H₀; compare as duas opções no G4.",
    )
    tabela_g4 = tabela_rejeicoes(simulacoes_de_poder(), alpha_g4)
    st.markdown(texto_poder(tabela_g4))
    st.pyplot(
        grafico_g4(tabela_g4),
        alt=(
            "G4: curvas de poder do t de Welch e do Mann-Whitney por tamanho do efeito, "
            "um painel por situação simulada, com linhas em α, em 80% e no efeito observado."
        ),
    )
    delta_tabela = efeito_mais_perto_do_observado(tabela_g4)
    st.markdown(
        f"**Poder com α = {porcentagem(alpha_g4, 0)} e δ = {numero(delta_tabela)}** "
        f"(PRs com bot {numero(math.exp(delta_tabela), 1)} vezes mais lentos, o ponto da "
        f"grade mais perto do efeito observado, δ = {numero(DELTA_MU_OBSERVADO)})"
    )
    st.table(
        pd.DataFrame(tabela_poder_para_exibir(tabela_g4, delta_tabela)).set_index("Situação")
    )
    st.caption(
        "Poder: % dos 10.000 conjuntos simulados com efeito em que o teste rejeitou H₀. "
        "Cada valor tem intervalo de 95% de no máximo ±1 ponto percentual."
    )

# ---------------------------------------------------------------------------
# 6. Dados reais (issue #22)
# ---------------------------------------------------------------------------
with secao(SECOES[5]):
    st.markdown(texto_dados_reais(resultado_real))
    st.markdown(
        "**Os dois testes nos dados coletados** "
        "(35 PRs com bot e 35 sem bot do `supabase/supabase`, α = 5% bicaudal)"
    )
    st.table(tabela_dados_reais(resultado_real).set_index("Teste"))
    st.caption(
        "A última linha é só referência: o Welch aplicado ao log do tempo, a situação em "
        "que ele ficou perto de 5% nas simulações. A diferença típica do Mann-Whitney é a "
        "mediana das diferenças entre todos os pares (estimador de Hodges-Lehmann)."
    )

    st.markdown("**Para discutir: poder com o tamanho da amostra**")
    st.markdown(texto_tamanho_amostra(poder_por_n, resultado_real))
    st.table(tabela_tamanho_amostra(poder_por_n).set_index("Modelo dos dados"))
    st.caption(
        "Poder estimado com 10.000 conjuntos simulados por ponto, no efeito observado nos "
        "dados reais. O número de PRs para 80% é interpolado entre os tamanhos simulados "
        "(35 a 400 por grupo)."
    )

# ---------------------------------------------------------------------------
# 7. Conclusão
# ---------------------------------------------------------------------------
with secao(SECOES[6]):
    st.info(
        "Em construção — Sprint 02: expectativa registrada na #10 × resultados "
        "encontrados, com a recomendação final."
    )

rodape(
    f"Laboratório de Experimentação de Software · Engenharia de Software · "
    f"semente fixa {SEED} (src/config.py)"
)
