"""Dashboard do Laboratório 04 — Testes de Hipótese.

Esqueleto com as 7 seções exigidas na ordem oficial. As seções são
preenchidas pelas issues seguintes (#8, #5, #7, #12, #13 e Sprint 02).
"""

import streamlit as st

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
# 3. Como os testes funcionam
# ---------------------------------------------------------------------------
st.header("3. Como os testes funcionam")
st.info(
    "Em construção — aplicação dos testes (#11) e gráfico G2 (#12), "
    "integrados na issue #13."
)

# ---------------------------------------------------------------------------
# 4. Erro tipo I
# ---------------------------------------------------------------------------
st.header("4. Erro tipo I")
st.info(
    "Em construção — Sprint 02: simulações de Q1 e Q3 e gráfico G3."
)

# ---------------------------------------------------------------------------
# 5. Poder
# ---------------------------------------------------------------------------
st.header("5. Poder")
st.info(
    "Em construção — Sprint 02: simulações de Q2 e Q3 e gráfico G4."
)

# ---------------------------------------------------------------------------
# 6. Dados reais
# ---------------------------------------------------------------------------
st.header("6. Dados reais")
st.info(
    "Em construção — tabela com estatística, p-valor, tamanho do efeito "
    "e conclusão de cada teste (#3, #4 e #11)."
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
