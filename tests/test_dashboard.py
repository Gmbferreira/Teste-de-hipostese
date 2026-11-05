"""Roda o dashboard sem navegador e confere as seções 1, 2, 3, 4 e 6 (issues #7, #13, #19 e #22)."""

from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.exemplo import gerar_exemplo
from src.formatacao import p_valor

APP = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"

SECOES = [
    "1. Cenário",
    "2. Os dados",
    "3. Como os testes funcionam",
    "4. Erro tipo I",
    "5. Poder",
    "6. Dados reais",
    "7. Conclusão",
]


def _rodar() -> AppTest:
    app = AppTest.from_file(str(APP), default_timeout=60)
    app.run()
    return app


def test_dashboard_roda_sem_erros_e_mantem_as_secoes_na_ordem() -> None:
    app = _rodar()
    assert not app.exception
    assert [h.value for h in app.header] == SECOES


def test_secao_1_mostra_o_cenario() -> None:
    """Seção 1 (issue #7): pergunta, hipóteses, teste e erros no cenário."""
    from src.textos import texto_cenario

    app = _rodar()
    textos = [m.value for m in app.markdown]
    assert texto_cenario() in textos
    assert not any("Em construção — pergunta" in info.value for info in app.info)


def test_secao_2_mostra_o_texto_e_o_g1() -> None:
    """Seção 2 (issue #7): texto sobre os dados e o gráfico G1."""
    from src.textos import texto_dados

    app = _rodar()
    textos = [m.value for m in app.markdown]
    assert texto_dados() in textos
    alts = [
        imagem.alt
        for elemento in app.get("image")
        for imagem in elemento.proto.imgs
    ]
    assert any("G1" in alt for alt in alts)
    assert not any("issue #7" in info.value for info in app.info)


def test_secao_3_tem_texto_tabela_e_interpretacao() -> None:
    app = _rodar()
    exemplo = gerar_exemplo()
    textos = " ".join(m.value for m in app.markdown)

    assert "t de Welch" in textos and "Mann-Whitney" in textos
    assert f"p = {p_valor(exemplo.mann_whitney.p_valor)}" in textos
    assert f"p = {p_valor(exemplo.welch.p_valor)}" in textos
    assert len(app.table) + len(app.dataframe) >= 1
    assert any(e.label == "Interpretação completa do exemplo" for e in app.expander)


def test_secao_4_mostra_o_erro_tipo_i_e_troca_o_alpha() -> None:
    """Seção 4 (issue #19): texto, tabela e o seletor de α."""
    from src.grafico_g3 import dados_g3
    from src.textos import texto_erro_tipo_i

    app = _rodar()
    textos = [m.value for m in app.markdown]
    assert texto_erro_tipo_i(dados_g3(alpha=0.05)) in textos
    assert any(e.label == "Como cada situação foi simulada" for e in app.expander)
    assert len(app.table) + len(app.dataframe) >= 2

    app.radio(key="alpha_erro_tipo_i").set_value(0.01).run()
    assert not app.exception
    textos = [m.value for m in app.markdown]
    assert texto_erro_tipo_i(dados_g3(alpha=0.01)) in textos


def test_secao_6_mostra_os_testes_nos_dados_reais() -> None:
    """Seção 6 (issue #22): texto e tabela com os dois testes nos dados coletados."""
    from src.dados_reais import analisar, texto_dados_reais

    app = _rodar()
    assert not app.exception
    textos = [m.value for m in app.markdown]
    assert texto_dados_reais(analisar()) in textos
    assert len(app.table) + len(app.dataframe) >= 3
