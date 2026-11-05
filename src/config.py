"""Configurações compartilhadas do projeto.

A semente fica definida em um único lugar para que todos os resultados
(geração dos dados simulados e simulações de Q1–Q3) sejam reproduzíveis.
"""

from __future__ import annotations

import numpy as np

# Semente fixa usada em todo o projeto.
SEED: int = 42

# Nível de significância adotado nos testes.
ALPHA: float = 0.05

# Número de repetições das simulações de Q1–Q3.
N_SIMULACOES: int = 10_000


def make_rng(seed: int = SEED) -> np.random.Generator:
    """Cria um gerador de números aleatórios reproduzível."""
    return np.random.default_rng(seed)
