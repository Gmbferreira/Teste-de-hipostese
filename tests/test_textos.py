"""Testes dos textos gerados para as seções 1, 2 e 4 do dashboard (issues #7 e #19)."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from src.config import SEED
from src.dados_reais import carregar_grupos
from src.formatacao import numero, porcentagem
from src.grafico_g3 import dados_g3
from src.monte_carlo import Proporcao, margem_esperada
from src.parametros import (
    DELTA_MU_OBSERVADO,
    GRUPO_CONTROLE,
    PARAMETROS_REAIS,
    RAZAO_GEOMETRICA_OBSERVADA,
)
from src.simulacao import N_POR_GRUPO
from src.textos import (
    CONSERVADOR,
    LIBERAL,
    PERTO,
    classificar,
    texto_cenario,
    texto_dados,
    texto_erro_tipo_i,
    texto_poder,
)


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


def _outliers_iqr(x: np.ndarray) -> int:
    q1, q3 = np.percentile(x, [25, 75])
    iqr = q3 - q1
    return int(np.count_nonzero((x < q1 - 1.5 * iqr) | (x > q3 + 1.5 * iqr)))


def test_texto_cenario_cobre_pergunta_hipoteses_e_erros() -> None:
    texto = texto_cenario()
    for termo in (
        "Pergunta",
        "H₀",
        "H₁",
        "t de Welch",
        "Mann-Whitney",
        "bicaudais",
        "5%",
        "tipo I",
        "tipo II",
        "docs/cenario.md",
    ):
        assert termo in texto
    assert "α = 1%" in texto_cenario(0.01)


def test_texto_dados_tem_de_2_a_4_frases_e_cita_o_essencial() -> None:
    texto = texto_dados()
    assert 2 <= _frases(texto) <= 4
    controle = PARAMETROS_REAIS[GRUPO_CONTROLE]
    for termo in (
        "assimétric",
        "outlier",
        "lognormal",
        "sem bot",
        f"μ={numero(controle.mu, 2)}",
        f"σ={numero(controle.sigma, 2)}",
        f"δ={numero(DELTA_MU_OBSERVADO, 2)}",
        f"{numero(RAZAO_GEOMETRICA_OBSERVADA, 2)}×",
        f"{N_POR_GRUPO} PRs",
        f"semente {SEED}",
    ):
        assert termo in texto


def test_texto_dados_usa_as_estatisticas_reais() -> None:
    com_bot, sem_bot = carregar_grupos()
    texto = texto_dados()
    assert f"Os {len(com_bot) + len(sem_bot)} PRs reais" in texto
    assert numero(float(np.median(com_bot)), 1) in texto
    assert numero(float(np.max(sem_bot)), 1) in texto
    assert (
        f"há {_outliers_iqr(com_bot)} outliers com bot e "
        f"{_outliers_iqr(sem_bot)} sem bot"
    ) in texto


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


# ---------------------------------------------------------------------------
# Seção 5: poder (issue #21)
# ---------------------------------------------------------------------------
GRADE_TESTE = (0.0, 0.5, 1.0, 1.5)


def _tabela_poder(curvas: dict[str, dict[str, tuple[float, ...]]], alpha: float = 0.05) -> pd.DataFrame:
    """Tabela no formato de dados_g4: taxas por situação e teste, uma por efeito da grade."""
    linhas = []
    for situacao, por_teste in curvas.items():
        for teste, taxas in por_teste.items():
            for delta, taxa in zip(GRADE_TESTE, taxas):
                proporcao = Proporcao(round(taxa * 10_000), 10_000)
                inferior, superior = proporcao.intervalo()
                linhas.append(
                    {
                        "situacao": situacao, "delta_mu": delta, "teste": teste,
                        "alpha": alpha, "repeticoes": 10_000,
                        "rejeicoes": proporcao.rejeicoes, "taxa": proporcao.taxa,
                        "ic95_inferior": inferior, "ic95_superior": superior,
                    }
                )
    return pd.DataFrame(linhas)


@pytest.fixture(scope="module")
def poder_real() -> dict[float, pd.DataFrame]:
    from src.grafico_g4 import dados_g4

    return {alpha: dados_g4(alpha=alpha) for alpha in (0.05, 0.01)}


def test_efeito_mais_perto_do_observado(poder_real) -> None:
    from src.textos import efeito_mais_perto_do_observado

    assert efeito_mais_perto_do_observado(poder_real[0.05]) == 1.0


def test_texto_poder_real_com_alpha_de_5_por_cento(poder_real) -> None:
    texto = texto_poder(poder_real[0.05])
    assert 2 <= _frases(texto) <= 4
    assert texto.startswith("Na situação realista, o **Mann-Whitney**")
    assert "em todos os tamanhos de efeito" in texto
    assert "δ = 1,00" in texto and "2,7 vezes" in texto
    assert "com grupos desbalanceados, onde o Welch rejeita H₀ demais" in texto
    assert "na escala log, onde o Welch fica até" in texto
    assert "com os tempos reais reamostrados, onde o Welch passa na frente a partir de δ = 1,25" in texto


def test_texto_poder_real_com_alpha_de_1_por_cento(poder_real) -> None:
    """Com α = 1% o cruzamento da reamostragem some e só a escala log muda de lado."""
    texto = texto_poder(poder_real[0.01])
    assert 2 <= _frases(texto) <= 4
    assert "passa na frente" not in texto
    assert "na escala log, onde o Welch fica até" in texto
    mantem = texto.split("A vantagem se mantém")[1].split(".")[0]
    assert "com os tempos reais reamostrados" in mantem


def test_texto_poder_sem_troca_de_lado() -> None:
    tabela = _tabela_poder(
        {
            "realista": {"welch": (0.05, 0.10, 0.20, 0.30), "mann_whitney": (0.05, 0.20, 0.50, 0.80)},
            "outliers": {"welch": (0.04, 0.06, 0.10, 0.15), "mann_whitney": (0.05, 0.18, 0.45, 0.75)},
        }
    )
    texto = texto_poder(tabela)
    assert 2 <= _frases(texto) <= 4
    assert "A vantagem se mantém com outliers." in texto
    assert "Em nenhuma situação a vantagem muda de lado." in texto


def test_texto_poder_com_welch_na_frente_e_cruzamento_no_meio() -> None:
    tabela = _tabela_poder(
        {
            "realista": {"welch": (0.05, 0.30, 0.60, 0.90), "mann_whitney": (0.05, 0.25, 0.50, 0.80)},
            "reamostragem": {"welch": (0.05, 0.20, 0.55, 0.95), "mann_whitney": (0.05, 0.10, 0.50, 0.85)},
            "outliers": {"welch": (0.05, 0.15, 0.20, 0.30), "mann_whitney": (0.05, 0.12, 0.40, 0.70)},
        }
    )
    texto = texto_poder(tabela)
    assert texto.startswith("Na situação realista, o **t de Welch**")
    assert "A vantagem se mantém com os tempos reais reamostrados." in texto
    assert "com outliers, onde o Mann-Whitney passa na frente a partir de δ = 1,00" in texto


def test_texto_poder_ignora_empates_e_a_vantagem_do_welch_inflado() -> None:
    tabela = _tabela_poder(
        {
            "realista": {"welch": (0.05, 0.10, 0.20, 0.30), "mann_whitney": (0.05, 0.20, 0.50, 0.80)},
            # Welch liberal sem efeito: a vantagem no menor efeito não é poder de verdade.
            "desbalanceado": {"welch": (0.13, 0.09, 0.03, 0.05), "mann_whitney": (0.05, 0.08, 0.30, 0.60)},
            # Diferenças de menos de meio ponto percentual contam como empate.
            "escala_log": {"welch": (0.05, 0.203, 0.502, 0.803), "mann_whitney": (0.05, 0.20, 0.50, 0.80)},
        }
    )
    texto = texto_poder(tabela)
    assert "Em nenhuma situação a vantagem muda de lado." in texto
    assert "com grupos desbalanceados, onde o Welch rejeita H₀ demais" in texto
    assert "A vantagem se mantém na escala log, e também" in texto
