"""Testes da conclusão do dashboard (issue #23)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.conclusao import (
    CONFIRMADO,
    EM_PARTE,
    NAO_CONFIRMADO,
    previsoes,
    tabela_esperado_encontrado,
    texto_balanco,
    texto_limitacao,
    texto_recomendacao,
)
from src.dados_reais import analisar, carregar_poder_por_tamanho
from src.formatacao import porcentagem
from src.grafico_g4 import dados_g4


@pytest.fixture(scope="module")
def poder() -> pd.DataFrame:
    return dados_g4()


@pytest.fixture(scope="module")
def poder_por_n() -> pd.DataFrame:
    return carregar_poder_por_tamanho()


def _mudar(tabela: pd.DataFrame, situacao: str, teste: str, delta: float, taxa: float) -> pd.DataFrame:
    """Cópia da tabela com a taxa de um ponto trocada."""
    nova = tabela.copy()
    linha = (nova["situacao"] == situacao) & (nova["teste"] == teste) & np.isclose(nova["delta_mu"], delta)
    assert linha.sum() == 1
    nova.loc[linha, "taxa"] = taxa
    return nova


def test_resultado_de_cada_previsao(poder, poder_por_n) -> None:
    """O que se confirmou e o que não, com os resultados atuais (α = 5%)."""
    resultados = [p.resultado for p in previsoes(poder, poder_por_n)]
    assert resultados == [
        CONFIRMADO,  # Mann-Whitney perto de 5% em todas as situações
        EM_PARTE,  # Welch conservador na realista, mas abaixo dos 3% a 4,5%
        CONFIRMADO,  # Welch mais conservador com amostras pequenas
        NAO_CONFIRMADO,  # Welch menos conservador com outliers, e não mais
        CONFIRMADO,  # Welch liberal com grupos desbalanceados
        CONFIRMADO,  # os dois perto de 5% na escala log
        CONFIRMADO,  # Mann-Whitney com mais poder em todo efeito na realista
        CONFIRMADO,  # Mann-Whitney com 50% a 60% no efeito observado
        NAO_CONFIRMADO,  # Welch abaixo dos 20% a 35% no efeito observado
        CONFIRMADO,  # amostras pequenas e desbalanceado
        EM_PARTE,  # outliers: o Welch perde, mas o Mann-Whitney também
        CONFIRMADO,  # escala log
    ]


def test_tabela_tem_erro_tipo_i_e_poder(poder, poder_por_n) -> None:
    tabela = tabela_esperado_encontrado(poder, poder_por_n)
    assert list(tabela.columns) == ["", "O que esperávamos", "O que encontramos", "Resultado"]
    assert tabela[""].value_counts().to_dict() == {"Erro tipo I": 6, "Poder": 6}
    assert tabela["O que encontramos"].str.len().gt(0).all()


def test_numeros_encontrados_vem_dos_resultados(poder, poder_por_n) -> None:
    linhas = {p.esperado: p.encontrado for p in previsoes(poder, poder_por_n)}
    welch_realista = poder[
        (poder["situacao"] == "realista") & (poder["teste"] == "welch") & (poder["delta_mu"] == 0)
    ]["taxa"].iloc[0]
    texto = next(v for k, v in linhas.items() if k.startswith("Welch conservador"))
    assert texto.startswith(porcentagem(welch_realista, 1))
    em_35 = poder_por_n[(poder_por_n["modelo"] == "lognormal") & (poder_por_n["n_por_grupo"] == 35)]
    welch_35 = em_35.set_index("teste").loc["welch", "taxa"]
    assert porcentagem(welch_35, 1) in " ".join(linhas.values())


def test_regras_respondem_aos_numeros(poder, poder_por_n) -> None:
    """Se os outliers tivessem deixado o Welch mais conservador, a previsão se confirmaria."""
    ajustada = _mudar(poder, "outliers", "welch", 0.0, 0.015)
    ajustada = _mudar(ajustada, "outliers", "mann_whitney", 1.0, 0.54)
    resultados = [p.resultado for p in previsoes(ajustada, poder_por_n)]
    assert resultados[3] == CONFIRMADO
    assert resultados[10] == CONFIRMADO

    liberal_demais = _mudar(poder, "desbalanceado", "welch", 0.0, 0.05)
    assert previsoes(liberal_demais, poder_por_n)[4].resultado == NAO_CONFIRMADO

    mw_fora = _mudar(poder, "amostras_pequenas", "mann_whitney", 0.0, 0.04)
    assert previsoes(mw_fora, poder_por_n)[0].resultado == EM_PARTE


def test_balanco_conta_as_previsoes(poder, poder_por_n) -> None:
    texto = texto_balanco(poder, poder_por_n)
    assert "Das 12 previsões, 8 se confirmaram, 2 em parte e 2 não." in texto
    assert "docs/expectativa.md" in texto


def test_recomendacao_e_quando_mudaria(poder, poder_por_n) -> None:
    texto = texto_recomendacao(poder, poder_por_n, analisar())
    assert "recomendamos o **Mann-Whitney**" in texto
    assert "12,8%" in texto  # Welch com grupos desbalanceados
    assert "p = 0,023 contra 0,055" in texto
    assert "**Quando a escolha mudaria.**" in texto
    assert "escala log" in texto and "2,7 vezes" in texto
    assert "a partir de δ = 1,25" in texto
    assert "média de horas" in texto


def test_limitacao(poder_por_n) -> None:
    texto = texto_limitacao(poder_por_n)
    assert texto.startswith("**Principal limitação.** As conclusões sobre poder dependem do modelo")
    assert "17% de poder ao Welch e 54% ao Mann-Whitney" in texto
    assert "(60% e 63%)" in texto
    assert "um repositório, um bot e 8 dias de PRs" in texto
    assert "observacional" in texto
