"""Testes do exemplo com os dois testes aplicados a um conjunto simulado (issue #11)."""

from __future__ import annotations

import numpy as np

from src.exemplo import (
    SAIDA_PADRAO,
    documento,
    gerar_exemplo,
    interpretacao,
    pr_mais_lento,
    tabela_resultados,
)
from src.formatacao import p_valor
from src.parametros import DELTA_MU_OBSERVADO
from src.simulacao import N_POR_GRUPO
from src.testes_estatisticos import aplicar_welch


def test_exemplo_padrao_usa_o_efeito_observado_e_e_reproduzivel() -> None:
    a, b = gerar_exemplo(), gerar_exemplo()
    assert a.delta_mu == DELTA_MU_OBSERVADO
    assert not a.h0_verdadeira
    assert len(a.com_bot) == len(a.sem_bot) == N_POR_GRUPO
    np.testing.assert_array_equal(a.com_bot, b.com_bot)
    assert a.welch == b.welch
    assert a.mann_whitney == b.mann_whitney


def test_acerto_e_tipo_de_erro() -> None:
    com_efeito = gerar_exemplo()
    for resultado in (com_efeito.welch, com_efeito.mann_whitney):
        assert com_efeito.acertou(resultado) == resultado.rejeita_h0
        esperado = None if resultado.rejeita_h0 else "erro tipo II"
        assert com_efeito.tipo_de_erro(resultado) == esperado

    sem_efeito = gerar_exemplo(delta_mu=0.0)
    for resultado in (sem_efeito.welch, sem_efeito.mann_whitney):
        assert sem_efeito.acertou(resultado) == (not resultado.rejeita_h0)
        esperado = "erro tipo I" if resultado.rejeita_h0 else None
        assert sem_efeito.tipo_de_erro(resultado) == esperado


def test_tabela_tem_os_dois_testes_e_bate_com_os_resultados() -> None:
    exemplo = gerar_exemplo()
    tabela = tabela_resultados(exemplo)
    assert list(tabela["Teste"]) == ["t de Welch", "Mann-Whitney"]
    assert list(tabela["p-valor"]) == [
        p_valor(exemplo.welch.p_valor),
        p_valor(exemplo.mann_whitney.p_valor),
    ]
    decisoes = tabela.filter(like="Decisão").iloc[:, 0].tolist()
    for decisao, resultado in zip(decisoes, (exemplo.welch, exemplo.mann_whitney)):
        assert decisao == ("rejeita H₀" if resultado.rejeita_h0 else "não rejeita H₀")


def test_interpretacao_descreve_a_decisao_de_cada_teste() -> None:
    for delta in (DELTA_MU_OBSERVADO, 0.0):
        exemplo = gerar_exemplo(delta_mu=delta)
        texto = interpretacao(exemplo)
        welch, mann_whitney = texto.split("**Mann-Whitney.**")
        for trecho, resultado in ((welch, exemplo.welch), (mann_whitney, exemplo.mann_whitney)):
            decisao = "**rejeitou H₀**" if resultado.rejeita_h0 else "**não rejeitou H₀**"
            assert decisao in trecho
            erro = exemplo.tipo_de_erro(resultado)
            assert (f"**{erro}**" in trecho) if erro else ("acertou" in trecho)
        assert ("H₀ é verdadeira" in texto) == exemplo.h0_verdadeira


def test_pr_mais_lento_e_o_welch_sem_ele() -> None:
    for delta in (DELTA_MU_OBSERVADO, 0.0, 2.0):
        exemplo = gerar_exemplo(delta_mu=delta)
        lento = pr_mais_lento(exemplo)
        com_bot, sem_bot = exemplo.com_bot, exemplo.sem_bot
        no_com_bot = com_bot.max() >= sem_bot.max()

        assert lento.grupo == ("com bot" if no_com_bot else "sem bot")
        assert lento.tempo == max(com_bot.max(), sem_bot.max())
        assert lento.maior_do_outro_grupo == (sem_bot.max() if no_com_bot else com_bot.max())
        if no_com_bot:
            com_bot = np.delete(com_bot, com_bot.argmax())
            assert np.isclose(lento.media_do_grupo_sem_ele, com_bot.mean())
        else:
            sem_bot = np.delete(sem_bot, sem_bot.argmax())
            assert np.isclose(lento.media_do_grupo_sem_ele, sem_bot.mean())
        assert lento.welch_sem_ele == aplicar_welch(com_bot, sem_bot)


def test_docs_exemplo_esta_em_dia_com_o_codigo() -> None:
    """Se falhar, rode `python -m src.exemplo` para regenerar o arquivo."""
    salvo = SAIDA_PADRAO.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert salvo == documento(gerar_exemplo())
