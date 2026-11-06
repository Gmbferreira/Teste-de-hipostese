"""Testes dos dois testes aplicados aos dados reais (issue #22)."""

from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd
import pytest

from src.dados_reais import (
    DADOS,
    analisar,
    carregar_grupos,
    tabela_dados_reais,
    texto_dados_reais,
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
