"""Dashboard do Laboratório 04 — Testes de Hipótese.

Placeholder mínimo criado na issue #2. O esqueleto com as 7 seções é
construído na issue #6.
"""

import streamlit as st

st.set_page_config(
    page_title="Testes de Hipótese — Tempo até o merge de PRs",
    page_icon="📊",
    layout="wide",
)

st.title("Testes de Hipótese — Tempo até o merge de PRs")

st.markdown(
    """
    Comparação entre o **teste t de Welch** e o **teste de Mann-Whitney**
    para o tempo até o merge de pull requests com e sem bot de revisão.

    **Repositório:** https://github.com/Gmbferreira/Teste-de-hipostese
    """
)

st.info("Dashboard em construção — seções e gráficos serão adicionados nas próximas issues.")
