"""Testes dos textos gerados para a seção 4 do dashboard (issue #19)."""

from __future__ import annotations

import re

import pandas as pd
import pytest

from src.formatacao import porcentagem
from src.grafico_g3 import dados_g3
from src.monte_carlo import Proporcao, margem_esperada
from src.textos import CONSERVADOR, LIBERAL, PERTO, classificar, texto_erro_tipo_i


def _frases(texto: str) -> int:
    return len(re.findall(r"[.](?:\s|$)", texto))


def _tabela(taxas: dict[tuple[str, str], int], alpha: float = 0.05) -> pd.DataFrame:
    """Tabela no formato de dados_g3 a partir do número de rejeições em 10.000."""
    linhas = []
    for (situacao, teste), rejeicoes in taxas.items():
        proporcao = Proporcao(rejeicoes, 10_000)
        inferior, superior = proporcao.intervalo()
        linhas.append(
            {
                "situacao": situacao, "delta_mu": 0.0, "teste": teste, "alpha": alpha,
                "repeticoes": 10_000, "rejeicoes": rejeicoes, "taxa": proporcao.taxa,
                "ic95_inferior": inferior, "ic95_superior": superior,
            }
        )
    return pd.DataFrame(linhas)


def test_classificar() -> None:
    margem = margem_esperada(0.05, 10_000)
    assert classificar(0.052, (0.048, 0.056), 0.05, margem) == PERTO
    assert classificar(0.0548, (0.0505, 0.0592), 0.05, margem) == LIBERAL
    assert classificar(0.0453, (0.0400, 0.0499), 0.05, margem) == CONSERVADOR
    # Fora da faixa, mas com o IC contendo α: não conta como desvio.
    assert classificar(0.0545, (0.0499, 0.0590), 0.05, margem) == PERTO


@pytest.mark.parametrize("alpha", [0.05, 0.01])
def test_texto_real_tem_de_2_a_4_frases_e_cita_os_desvios(alpha: float) -> None:
    tabela = dados_g3(alpha=alpha)
    texto = texto_erro_tipo_i(tabela)
    assert 2 <= _frases(texto) <= 4
    assert "Mann-Whitney" in texto and "t de Welch" in texto
    desbalanceado = tabela[(tabela["situacao"] == "desbalanceado") & (tabela["teste"] == "welch")]
    assert porcentagem(float(desbalanceado["taxa"].iloc[0]), 1) in texto
    assert "h₀" not in texto  # a maiúscula do H₀ não pode se perder


def test_texto_quando_tudo_fica_perto_de_alpha() -> None:
    tabela = _tabela(
        {("realista", "welch"): 500, ("realista", "mann_whitney"): 490,
         ("escala_log", "welch"): 510, ("escala_log", "mann_whitney"): 495}
    )
    texto = texto_erro_tipo_i(tabela)
    assert "perto de 5% em todas as situações" in texto
    assert "na situação realista e na escala log" in texto
    assert "conservador" not in texto and "vezes α" not in texto
    assert 2 <= _frases(texto) <= 4


def test_texto_com_desvio_liberal_sem_conservador() -> None:
    tabela = _tabela(
        {("desbalanceado", "welch"): 1_280, ("desbalanceado", "mann_whitney"): 494,
         ("escala_log", "welch"): 480, ("escala_log", "mann_whitney"): 476}
    )
    texto = texto_erro_tipo_i(tabela)
    assert texto.count("Com grupos desbalanceados") == 1  # começa a frase com maiúscula
    assert "12,8%" in texto and "2,6 vezes α" in texto


def test_mann_whitney_com_amostra_pequena_explica_o_tamanho_exato() -> None:
    tabela = _tabela(
        {("amostras_pequenas", "welch"): 3, ("amostras_pequenas", "mann_whitney"): 79,
         ("realista", "welch"): 20, ("realista", "mann_whitney"): 116},
        alpha=0.01,
    )
    texto = texto_erro_tipo_i(tabela)
    assert "só se afastou de 1% com amostras pequenas (0,79%)" in texto
    assert "teste exato rejeita no máximo 0,89%" in texto
