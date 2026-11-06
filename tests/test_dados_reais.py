"""Testes dos dois testes aplicados aos dados reais (issue #22)."""

from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd
import pytest

from src.dados_reais import (
    DADOS,
    SAIDA_PODER_TAMANHO,
    analisar,
    carregar_grupos,
    carregar_poder_por_tamanho,
    n_para_poder,
    poder_por_tamanho,
    tabela_dados_reais,
    tabela_tamanho_amostra,
    texto_dados_reais,
    texto_tamanho_amostra,
)
from src.formatacao import p_valor
from src.testes_estatisticos import aplicar_mann_whitney, aplicar_welch


@pytest.fixture(scope="module")
def resultado():
    return analisar()


def test_grupos_vem_do_csv_real() -> None:
    com_bot, sem_bot = carregar_grupos()
    dados = pd.read_csv(DADOS)
    assert len(com_bot) == (dados["grupo"] == "com_bot").sum() == 35
    assert len(sem_bot) == (dados["grupo"] == "sem_bot").sum() == 35
    assert (com_bot > 0).all() and (sem_bot > 0).all()


def test_usa_os_testes_da_issue_11(resultado) -> None:
    com_bot, sem_bot = carregar_grupos()
    assert resultado.welch == aplicar_welch(com_bot, sem_bot)
    assert resultado.mann_whitney == aplicar_mann_whitney(com_bot, sem_bot)
    assert resultado.welch_log == aplicar_welch(np.log(com_bot), np.log(sem_bot))
    assert resultado.mann_whitney.metodo == "exact"  # não há empates nos dados reais


def test_razao_geometrica(resultado) -> None:
    com_bot, sem_bot = carregar_grupos()
    esperado = math.exp(np.log(com_bot).mean() - np.log(sem_bot).mean())
    assert math.isclose(resultado.razao_geometrica, esperado)
    inferior, superior = resultado.ic95_razao_geometrica
    assert inferior < resultado.razao_geometrica < superior


def test_tabela_tem_estatistica_p_valor_efeito_e_conclusao(resultado) -> None:
    tabela = tabela_dados_reais(resultado)
    assert list(tabela.columns) == [
        "Teste", "Estatística", "p-valor", "Tamanho do efeito", "Conclusão (α = 5%)",
    ]
    assert list(tabela["p-valor"]) == [
        p_valor(resultado.welch.p_valor),
        p_valor(resultado.mann_whitney.p_valor),
        p_valor(resultado.welch_log.p_valor),
    ]
    for conclusao, teste in zip(
        tabela["Conclusão (α = 5%)"],
        (resultado.welch, resultado.mann_whitney, resultado.welch_log),
    ):
        assert conclusao.startswith("rejeita") == teste.rejeita_h0


def test_texto_tem_de_2_a_4_frases_e_os_p_valores(resultado) -> None:
    texto = texto_dados_reais(resultado)
    assert 2 <= len(re.findall(r"[.](?:\s|$)", texto)) <= 4
    assert f"p = {p_valor(resultado.mann_whitney.p_valor)}" in texto
    assert f"p = {p_valor(resultado.welch.p_valor)}" in texto
    if resultado.welch.rejeita_h0 != resultado.mann_whitney.rejeita_h0:
        assert "discordaram" in texto


def test_texto_usa_a_escala_de_vargha_e_delaney(resultado) -> None:
    texto = texto_dados_reais(resultado)
    assert f"o efeito é {resultado.mann_whitney.magnitude}" in texto
    assert "Vargha e Delaney" in texto


def test_n_para_poder_interpola_entre_os_tamanhos() -> None:
    tabela = pd.DataFrame(
        {
            "modelo": ["m"] * 3, "teste": ["welch"] * 3,
            "n_por_grupo": [35, 50, 70], "taxa": [0.5, 0.7, 0.9],
        }
    )
    assert math.isclose(n_para_poder(tabela, "m", "welch"), 60.0)
    assert n_para_poder(tabela, "m", "welch", alvo=0.95) is None
    assert n_para_poder(tabela, "m", "welch", alvo=0.4) == 35.0


def test_csv_do_poder_por_tamanho_esta_em_dia() -> None:
    """Confere só os tamanhos baratos. Se falhar, rode `python -m src.dados_reais`."""
    salvo = pd.read_csv(SAIDA_PODER_TAMANHO)
    assert set(salvo["n_por_grupo"]) >= {35, 50, 70, 100}
    assert set(salvo["modelo"]) == {"lognormal", "reamostragem"}
    recalculado = poder_por_tamanho(tamanhos=(35, 50))
    parte = salvo[salvo["n_por_grupo"].isin([35, 50])].reset_index(drop=True)
    pd.testing.assert_frame_equal(
        parte, recalculado.round(6), check_dtype=False, check_exact=False, atol=1e-6
    )


def test_tabela_e_texto_do_tamanho_da_amostra(resultado) -> None:
    tabela = carregar_poder_por_tamanho()
    resumo = tabela_tamanho_amostra(tabela)
    assert len(resumo) == 2
    texto = texto_tamanho_amostra(tabela, resultado)
    assert 2 <= len(re.findall(r"[.](?:\s|$)", texto)) <= 4
    assert "80%" in texto and "35 PRs por grupo" in texto
