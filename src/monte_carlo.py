"""Motor das simulações de Q1–Q3 e erro tipo I da situação realista (issue #14).

Para uma situação (tamanho dos grupos, outliers, escala) e um tamanho de efeito,
o motor gera os 10.000 conjuntos de uma vez, aplica os dois testes em todos e
guarda os p-valores. A proporção de p-valores abaixo de α é o erro tipo I quando
δ = 0 e o poder quando δ > 0.

Todas as situações usam a mesma semente. Assim os sorteios de base são os
mesmos em todas elas e a diferença entre duas situações vem só do que muda
nelas, e não do acaso.

Uso:
    python -m src.monte_carlo
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.config import ALPHA, N_SIMULACOES, SEED, make_rng
from src.simulacao import N_POR_GRUPO, gerar_grupos

RAIZ = Path(__file__).resolve().parent.parent
PASTA_RESULTADOS = RAIZ / "resultados"
SAIDA_Q1 = PASTA_RESULTADOS / "q1_erro_tipo_i.csv"

TESTES = ("welch", "mann_whitney")
Z_95 = 1.959963984540054  # quantil 97,5% da normal padrão


@dataclass(frozen=True)
class Situacao:
    """Como os dados de uma situação simulada são gerados."""

    chave: str
    nome: str
    descricao: str
    motivo: str
    n_com: int = N_POR_GRUPO
    n_sem: int = N_POR_GRUPO
    prob_outlier: float = 0.0
    atraso_outlier_horas: tuple[float, float] = (168.0, 672.0)  # de 1 a 4 semanas
    escala_log: bool = False


REALISTA = Situacao(
    chave="realista",
    nome="Realista",
    descricao="lognormal ajustada aos dados reais, 35 PRs por grupo",
    motivo="é a situação mais parecida com a amostra coletada",
)


def gerar_conjuntos(
    situacao: Situacao,
    delta_mu: float,
    repeticoes: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Gera `repeticoes` conjuntos da situação (matrizes com um conjunto por linha)."""
    com_bot, sem_bot = gerar_grupos(
        delta_mu, situacao.n_com, situacao.n_sem, repeticoes=repeticoes, rng=rng
    )
    if situacao.prob_outlier > 0:
        # Alguns PRs ficam esquecidos e levam de 1 a 4 semanas a mais, nos dois
        # grupos e com a mesma chance, então H₀ continua valendo quando δ = 0.
        com_bot = _adicionar_esquecidos(com_bot, situacao, rng)
        sem_bot = _adicionar_esquecidos(sem_bot, situacao, rng)
    if situacao.escala_log:
        com_bot, sem_bot = np.log(com_bot), np.log(sem_bot)
    return com_bot, sem_bot


def _adicionar_esquecidos(
    tempos: np.ndarray, situacao: Situacao, rng: np.random.Generator
) -> np.ndarray:
    esquecido = rng.random(tempos.shape) < situacao.prob_outlier
    atraso = rng.uniform(*situacao.atraso_outlier_horas, size=tempos.shape)
    return tempos + np.where(esquecido, atraso, 0.0)


def p_valores(com_bot: np.ndarray, sem_bot: np.ndarray) -> dict[str, np.ndarray]:
    """P-valores bicaudais dos dois testes em cada linha (um conjunto por linha).

    O Mann-Whitney usa a distribuição exata de U, como na issue #11; com dados
    contínuos não há empates.
    """
    welch = stats.ttest_ind(com_bot, sem_bot, axis=1, equal_var=False).pvalue
    mann_whitney = stats.mannwhitneyu(
        com_bot, sem_bot, axis=1, alternative="two-sided", method="exact"
    ).pvalue
    return {"welch": np.asarray(welch), "mann_whitney": np.asarray(mann_whitney)}


@dataclass(frozen=True)
class Proporcao:
    """Proporção de rejeições, com intervalo de confiança de Wilson."""

    rejeicoes: int
    repeticoes: int

    @property
    def taxa(self) -> float:
        return self.rejeicoes / self.repeticoes

    def intervalo(self, z: float = Z_95) -> tuple[float, float]:
        n, p = self.repeticoes, self.taxa
        centro = (p + z**2 / (2 * n)) / (1 + z**2 / n)
        meia = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
        return centro - meia, centro + meia


def margem_esperada(alpha: float = ALPHA, repeticoes: int = N_SIMULACOES) -> float:
    """Quanto a taxa varia só por acaso em torno de α (meia largura de 95%)."""
    return Z_95 * math.sqrt(alpha * (1 - alpha) / repeticoes)


@dataclass(frozen=True, eq=False)
class Simulacao:
    """P-valores dos dois testes em todos os conjuntos de uma situação e efeito."""

    situacao: Situacao
    delta_mu: float
    p: dict[str, np.ndarray] = field(repr=False)

    @property
    def repeticoes(self) -> int:
        return len(self.p["welch"])

    def proporcao(self, teste: str, alpha: float = ALPHA) -> Proporcao:
        return Proporcao(int((self.p[teste] < alpha).sum()), self.repeticoes)


def simular(
    situacao: Situacao,
    delta_mu: float = 0.0,
    repeticoes: int = N_SIMULACOES,
    semente: int = SEED,
) -> Simulacao:
    """Roda os dois testes em `repeticoes` conjuntos da situação."""
    com_bot, sem_bot = gerar_conjuntos(situacao, delta_mu, repeticoes, make_rng(semente))
    return Simulacao(situacao, delta_mu, p_valores(com_bot, sem_bot))


def tabela_rejeicoes(simulacoes: list[Simulacao], alpha: float = ALPHA) -> pd.DataFrame:
    """Uma linha por situação, efeito e teste, com a taxa de rejeição e o IC de 95%."""
    linhas = []
    for sim in simulacoes:
        for teste in TESTES:
            proporcao = sim.proporcao(teste, alpha)
            inferior, superior = proporcao.intervalo()
            linhas.append(
                {
                    "situacao": sim.situacao.chave,
                    "delta_mu": sim.delta_mu,
                    "teste": teste,
                    "alpha": alpha,
                    "repeticoes": proporcao.repeticoes,
                    "rejeicoes": proporcao.rejeicoes,
                    "taxa": proporcao.taxa,
                    "ic95_inferior": inferior,
                    "ic95_superior": superior,
                }
            )
    return pd.DataFrame(linhas)


def erro_tipo_i(
    situacoes: tuple[Situacao, ...] = (REALISTA,),
    repeticoes: int = N_SIMULACOES,
    semente: int = SEED,
    alpha: float = ALPHA,
) -> pd.DataFrame:
    """Q1: proporção de p-valores < α com H₀ verdadeira (δ = 0)."""
    simulacoes = [simular(s, 0.0, repeticoes, semente) for s in situacoes]
    return tabela_rejeicoes(simulacoes, alpha)


def salvar_csv(tabela: pd.DataFrame, destino: Path) -> Path:
    destino.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(destino, index=False, float_format="%.6f", lineterminator="\n")
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=SAIDA_Q1)
    args = parser.parse_args()

    tabela = erro_tipo_i()
    salvar_csv(tabela, args.saida)
    for linha in tabela.itertuples():
        print(
            f"{linha.teste:<13} erro tipo I = {100 * linha.taxa:.2f}% "
            f"(IC 95%: {100 * linha.ic95_inferior:.2f}% a {100 * linha.ic95_superior:.2f}%)"
        )
    print(f"Resultado salvo em {args.saida}")


if __name__ == "__main__":
    main()
