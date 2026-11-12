"""Roda o dashboard sem navegador e confere as 7 seções (issues #7, #13, #19, #21, #22 e #23)."""

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


def test_secao_5_mostra_o_poder_e_troca_o_alpha() -> None:
    """Seção 5 (issue #21): texto, G4, tabela no efeito observado e o seletor de α."""
    from src.grafico_g4 import dados_g4
    from src.textos import texto_poder

    app = _rodar()
    assert not app.exception
    textos = [m.value for m in app.markdown]
    assert texto_poder(dados_g4(alpha=0.05)) in textos
    alts = [imagem.alt for elemento in app.get("image") for imagem in elemento.proto.imgs]
    assert any(alt.startswith("G4") for alt in alts)
    assert any("Diferença (Mann-Whitney − Welch)" in tabela.value.columns for tabela in app.table)
    assert not any("gráfico G4" in info.value for info in app.info)

    app.radio(key="alpha_poder").set_value(0.01).run()
    assert not app.exception
    textos = [m.value for m in app.markdown]
    assert texto_poder(dados_g4(alpha=0.01)) in textos


def test_secao_6_mostra_os_testes_nos_dados_reais() -> None:
    """Seção 6 (issue #22): texto e tabela com os dois testes nos dados coletados."""
    from src.dados_reais import (
        analisar,
        carregar_poder_por_tamanho,
        texto_dados_reais,
        texto_tamanho_amostra,
    )

    app = _rodar()
    assert not app.exception
    textos = [m.value for m in app.markdown]
    assert texto_dados_reais(analisar()) in textos
    assert texto_tamanho_amostra(carregar_poder_por_tamanho(), analisar()) in textos
    assert len(app.table) + len(app.dataframe) >= 3


def test_secao_7_mostra_a_conclusao_com_alpha_de_5_por_cento() -> None:
    """Seção 7 (issue #23): balanço, esperado × encontrado, recomendação e limitação."""
    from src.conclusao import texto_balanco, texto_limitacao, texto_recomendacao
    from src.dados_reais import analisar, carregar_poder_por_tamanho
    from src.grafico_g4 import dados_g4

    app = _rodar()
    assert not app.exception
    poder, poder_por_n = dados_g4(alpha=0.05), carregar_poder_por_tamanho()
    textos = [m.value for m in app.markdown]
    assert texto_balanco(poder, poder_por_n) in textos
    assert texto_recomendacao(poder, poder_por_n, analisar()) in textos
    assert texto_limitacao(poder_por_n) in textos
    assert any("O que esperávamos" in tabela.value.columns for tabela in app.table)
    assert not app.info  # nenhuma seção ficou "Em construção"

    # Trocar o α das seções 4 e 5 não muda a conclusão, que usa o α da expectativa.
    app.radio(key="alpha_poder").set_value(0.01).run()
    assert texto_balanco(poder, poder_por_n) in [m.value for m in app.markdown]


def test_texto_do_g2_tem_de_2_a_4_frases() -> None:
    """Revisão final (issue #24): o texto do G2 fica no app; os outros, em tests/test_revisao_final.py."""
    from tests.test_revisao_final import frases

    app = _rodar()
    texto = next(m.value for m in app.markdown if m.value.startswith("O **t de Welch** compara"))
    assert 2 <= frases(texto) <= 4


def test_topo_tem_abertura_links_numeros_e_navegacao() -> None:
    """Visual de apresentação (issue #26): links no topo, números e índice lateral."""
    app = _rodar()
    assert not app.exception
    textos = " ".join(m.value for m in app.markdown)
    assert "O bot de revisão muda o tempo até o merge?" in textos
    assert "O estudo em números" in textos
    # O enunciado pede os links do dashboard, do repositório e do GitHub Projects no topo.
    assert "https://teste-de-hipostese-gmbf.streamlit.app/" in textos
    assert "https://github.com/Gmbferreira/Teste-de-hipostese" in textos
    assert "https://github.com/users/Gmbferreira/projects/4" in textos
    assert "em breve" not in textos
    lateral = " ".join(m.value for m in app.sidebar.markdown)
    for numero in range(1, 8):
        assert f'href="#secao-{numero}"' in lateral
