"""Parâmetros das distribuições usadas na simulação.

Estimativas de máxima verossimilhança de uma lognormal (loc fixo em zero)
ajustada ao tempo até o merge de cada grupo. Este módulo é a fonte única
consumida pelo gerador de dados simulados (issue #9).

Ver docs/analise_exploratoria.md para a justificativa e as estatísticas.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist


@dataclass(frozen=True)
class ParametrosLognormal:
    """Parâmetros de uma lognormal: X ~ LogNormal(mu, sigma)."""

    grupo: str
    mu: float
    sigma: float
    n_real: int
    mediana_amostral: float

    @property
    def mediana(self) -> float:
        """Mediana teórica: exp(mu)."""
        return math.exp(self.mu)

    @property
    def media(self) -> float:
        """Média teórica: exp(mu + sigma^2 / 2)."""
        return math.exp(self.mu + self.sigma**2 / 2)

    @property
    def variancia(self) -> float:
        """Variância teórica da lognormal."""
        return (math.exp(self.sigma**2) - 1) * math.exp(2 * self.mu + self.sigma**2)

    @property
    def desvio(self) -> float:
        """Desvio-padrão teórico da lognormal."""
        return math.sqrt(self.variancia)

    def quantil(self, p: float) -> float:
        """Quantil p (0 < p < 1) da lognormal."""
        return math.exp(self.mu + self.sigma * NormalDist().inv_cdf(p))


# Ajuste por máxima verossimilhança em data/prs_merge_time.csv (2026-11-05).
PARAMETROS_REAIS: dict[str, ParametrosLognormal] = {
    "com_bot": ParametrosLognormal(
        grupo="com_bot",
        mu=2.3188266066687886,
        sigma=1.774269157515637,
        n_real=35,
        mediana_amostral=17.5569,
    ),
    "sem_bot": ParametrosLognormal(
        grupo="sem_bot",
        mu=1.3296811485667324,
        sigma=1.916634476410899,
        n_real=35,
        mediana_amostral=2.5181,
    ),
}

# Grupo de referência: em H0 os dois grupos vêm desta distribuição.
GRUPO_CONTROLE = "sem_bot"

# Diferença observada entre os grupos na escala log.
DELTA_MU_OBSERVADO = (
    PARAMETROS_REAIS["com_bot"].mu - PARAMETROS_REAIS["sem_bot"].mu
)
RAZAO_GEOMETRICA_OBSERVADA = math.exp(DELTA_MU_OBSERVADO)
RAZAO_MEDIANAS_AMOSTRAIS = (
    PARAMETROS_REAIS["com_bot"].mediana_amostral
    / PARAMETROS_REAIS["sem_bot"].mediana_amostral
)

# Grade sugerida para as simulações de poder (Q2). O zero representa H0.
GRADE_DELTA_MU_SUGERIDA: tuple[float, ...] = (
    0.0,
    0.25,
    0.5,
    0.75,
    1.0,
    1.25,
    1.5,
    2.0,
)
