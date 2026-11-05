"""Gerador dos dados simulados (issue #9).

O tempo até o merge segue uma lognormal ajustada aos dados reais
(src/parametros.py). Com H₀ verdadeira, os dois grupos são sorteados da
lognormal do grupo de controle (sem bot). Com efeito, o grupo com bot usa
mu + delta_mu e o mesmo sigma, o que multiplica os tempos por exp(delta_mu).

Exemplo:
    from src.simulacao import gerar_grupos
    com_bot, sem_bot = gerar_grupos(delta_mu=0.5)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.config import make_rng
from src.parametros import DELTA_MU_OBSERVADO, GRUPO_CONTROLE, PARAMETROS_REAIS

# Mesmo tamanho da amostra real, para a simulação ficar comparável a ela.
N_POR_GRUPO: int = PARAMETROS_REAIS[GRUPO_CONTROLE].n_real

# Parâmetros da lognormal do grupo de controle (sem bot), na escala log.
MU_CONTROLE: float = PARAMETROS_REAIS[GRUPO_CONTROLE].mu
SIGMA_CONTROLE: float = PARAMETROS_REAIS[GRUPO_CONTROLE].sigma


def gerar_grupos(
    delta_mu: float = 0.0,
    n_com: int = N_POR_GRUPO,
    n_sem: int = N_POR_GRUPO,
    *,
    repeticoes: int | None = None,
    mu: float = MU_CONTROLE,
    sigma: float = SIGMA_CONTROLE,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Sorteia os tempos até o merge (horas) dos grupos com bot e sem bot.

    Args:
        delta_mu: tamanho do efeito na escala log. Zero deixa H₀ verdadeira;
            com valor positivo os PRs com bot demoram exp(delta_mu) vezes mais.
        n_com: quantidade de PRs no grupo com bot.
        n_sem: quantidade de PRs no grupo sem bot.
        repeticoes: None gera um único conjunto de dados (dois vetores). Com
            um inteiro k, gera k conjuntos de uma vez (duas matrizes k × n,
            uma linha por conjunto), que é o formato usado em Q1–Q3.
        mu, sigma: parâmetros da lognormal do grupo sem bot.
        rng: gerador aleatório. Sem ele, usa make_rng() com a semente fixa.

    Returns:
        Tupla (com_bot, sem_bot) com os tempos em horas.
    """
    if n_com < 1 or n_sem < 1:
        raise ValueError("cada grupo precisa de pelo menos uma observação")
    if sigma <= 0:
        raise ValueError("sigma precisa ser positivo")
    if repeticoes is not None and repeticoes < 1:
        raise ValueError("repeticoes precisa ser positivo")

    if rng is None:
        rng = make_rng()

    forma_sem = (n_sem,) if repeticoes is None else (repeticoes, n_sem)
    forma_com = (n_com,) if repeticoes is None else (repeticoes, n_com)

    # O grupo sem bot é sorteado primeiro para que, com a mesma semente, ele
    # seja igual em qualquer tamanho de efeito.
    sem_bot = rng.lognormal(mean=mu, sigma=sigma, size=forma_sem)
    com_bot = rng.lognormal(mean=mu + delta_mu, sigma=sigma, size=forma_com)
    return com_bot, sem_bot


def gerar_dataframe(
    delta_mu: float = DELTA_MU_OBSERVADO,
    n_com: int = N_POR_GRUPO,
    n_sem: int = N_POR_GRUPO,
    *,
    rng: np.random.Generator | None = None,
) -> pd.DataFrame:
    """Gera um conjunto simulado no mesmo formato de data/prs_merge_time.csv.

    Por padrão usa o efeito observado nos dados reais, que é o cenário mais
    parecido com a amostra coletada (útil para comparar com ela no G1).
    """
    com_bot, sem_bot = gerar_grupos(delta_mu, n_com, n_sem, rng=rng)
    return pd.DataFrame(
        {
            "grupo": ["com_bot"] * n_com + ["sem_bot"] * n_sem,
            "tempo_merge_horas": np.concatenate([com_bot, sem_bot]),
        }
    )
