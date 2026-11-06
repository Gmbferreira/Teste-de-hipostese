"""Os dois testes do par P1: t de Welch e Mann-Whitney (issue #11).

Os dois testes são bicaudais (ver docs/cenario.md) e recebem os tempos até o
merge, em horas, na ordem (com_bot, sem_bot). Além da estatística e do p-valor,
cada resultado traz o tamanho do efeito e o que é preciso para desenhar a
distribuição da estatística sob H₀ no G2.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy import stats

from src.config import ALPHA


@dataclass(frozen=True)
class ResultadoWelch:
    """Resultado do t de Welch (compara as médias sem supor variâncias iguais)."""

    t: float
    gl: float
    p_valor: float
    media_com: float
    media_sem: float
    dp_com: float
    dp_sem: float
    ic95: tuple[float, float]
    alpha: float = ALPHA

    @property
    def diferenca_medias(self) -> float:
        """Média com bot menos média sem bot, em horas."""
        return self.media_com - self.media_sem

    @property
    def d_cohen(self) -> float:
        """Diferença de médias em desvios-padrão (média das duas variâncias)."""
        return self.diferenca_medias / math.sqrt((self.dp_com**2 + self.dp_sem**2) / 2)

    @property
    def t_critico(self) -> float:
        """Limite da região de rejeição: rejeita H₀ se |t| > t_critico."""
        return float(stats.t.ppf(1 - self.alpha / 2, self.gl))

    @property
    def rejeita_h0(self) -> bool:
        return self.p_valor < self.alpha


@dataclass(frozen=True)
class ResultadoMannWhitney:
    """Resultado do Mann-Whitney (compara os postos dos dois grupos)."""

    u: float
    p_valor: float
    n_com: int
    n_sem: int
    hodges_lehmann: float
    metodo: str
    alpha: float = ALPHA

    @property
    def n_pares(self) -> int:
        """Quantidade de pares (PR com bot, PR sem bot) comparados por U."""
        return self.n_com * self.n_sem

    @property
    def prob_superioridade(self) -> float:
        """Estimativa de P(T_bot > T_sem): fração dos pares em que o PR com bot demorou mais."""
        return self.u / self.n_pares

    @property
    def correlacao_bisserial(self) -> float:
        """Correlação bisserial de postos, entre -1 e 1 (zero quando não há efeito)."""
        return 2 * self.prob_superioridade - 1

    @property
    def magnitude(self) -> str:
        """Tamanho do efeito pela escala de Vargha e Delaney para o A (= P(T_bot > T_sem))."""
        return magnitude_vargha_delaney(self.prob_superioridade)

    @property
    def regiao_rejeicao(self) -> tuple[int, int]:
        """Rejeita H₀ se U <= primeiro valor ou U >= segundo valor."""
        return limites_rejeicao_u(self.n_com, self.n_sem, self.alpha)

    @property
    def rejeita_h0(self) -> bool:
        return self.p_valor < self.alpha


def magnitude_vargha_delaney(a: float) -> str:
    """Classifica o A de Vargha e Delaney (2000): pequeno a partir de 0,56, médio a
    partir de 0,64 e grande a partir de 0,71, contando a distância até 0,5 nos dois
    sentidos."""
    distancia = abs(a - 0.5) + 1e-12  # 0,71 - 0,5 dá 0,20999... em ponto flutuante
    if distancia < 0.06:
        return "desprezível"
    if distancia < 0.14:
        return "pequeno"
    if distancia < 0.21:
        return "médio"
    return "grande"


def _validar(com_bot: np.ndarray, sem_bot: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    com_bot = np.asarray(com_bot, dtype=float)
    sem_bot = np.asarray(sem_bot, dtype=float)
    if com_bot.ndim != 1 or sem_bot.ndim != 1:
        raise ValueError("cada grupo precisa ser um vetor de tempos")
    if len(com_bot) < 2 or len(sem_bot) < 2:
        raise ValueError("cada grupo precisa de pelo menos duas observações")
    return com_bot, sem_bot


def aplicar_welch(
    com_bot: np.ndarray, sem_bot: np.ndarray, alpha: float = ALPHA
) -> ResultadoWelch:
    """Aplica o t de Welch bicaudal (H₀: médias iguais)."""
    com_bot, sem_bot = _validar(com_bot, sem_bot)
    resultado = stats.ttest_ind(com_bot, sem_bot, equal_var=False)
    ic = resultado.confidence_interval(confidence_level=0.95)
    return ResultadoWelch(
        t=float(resultado.statistic),
        gl=float(resultado.df),
        p_valor=float(resultado.pvalue),
        media_com=float(com_bot.mean()),
        media_sem=float(sem_bot.mean()),
        dp_com=float(com_bot.std(ddof=1)),
        dp_sem=float(sem_bot.std(ddof=1)),
        ic95=(float(ic.low), float(ic.high)),
        alpha=alpha,
    )


def aplicar_mann_whitney(
    com_bot: np.ndarray, sem_bot: np.ndarray, alpha: float = ALPHA
) -> ResultadoMannWhitney:
    """Aplica o Mann-Whitney bicaudal (H₀: P(T_bot > T_sem) = 1/2).

    Sem empates usamos a distribuição exata de U, a mesma desenhada no G2.
    Com empates o SciPy só tem a aproximação normal, então ela é usada.
    """
    com_bot, sem_bot = _validar(com_bot, sem_bot)
    todos = np.concatenate([com_bot, sem_bot])
    metodo = "exact" if np.unique(todos).size == todos.size else "asymptotic"
    resultado = stats.mannwhitneyu(
        com_bot, sem_bot, alternative="two-sided", method=metodo
    )
    return ResultadoMannWhitney(
        u=float(resultado.statistic),
        p_valor=float(resultado.pvalue),
        n_com=len(com_bot),
        n_sem=len(sem_bot),
        hodges_lehmann=float(np.median(np.subtract.outer(com_bot, sem_bot))),
        metodo=metodo,
        alpha=alpha,
    )


@lru_cache(maxsize=32)
def _pmf_u(n1: int, n2: int) -> tuple[float, ...]:
    # Recursão clássica: olhando o maior dos n1 + n2 valores, ele é do grupo 1
    # com probabilidade n1 / (n1 + n2) e, nesse caso, ganha de todos os n2
    # valores do grupo 2 (soma n2 a U); senão não soma nada.
    anterior = [np.ones(1) for _ in range(n2 + 1)]  # n1 = 0: U é sempre 0
    for i in range(1, n1 + 1):
        atual = [np.ones(1)]  # n2 = 0: U é sempre 0
        for j in range(1, n2 + 1):
            pmf = np.zeros(i * j + 1)
            maior_do_grupo_1 = anterior[j]
            pmf[j : j + maior_do_grupo_1.size] += i / (i + j) * maior_do_grupo_1
            maior_do_grupo_2 = atual[j - 1]
            pmf[: maior_do_grupo_2.size] += j / (i + j) * maior_do_grupo_2
            atual.append(pmf)
        anterior = atual
    return tuple(anterior[n2])


def distribuicao_nula_u(n_com: int, n_sem: int) -> np.ndarray:
    """Probabilidade exata de cada valor de U = 0, 1, ..., n_com * n_sem sob H₀.

    Vale quando os dois grupos vêm da mesma distribuição contínua (sem empates).
    """
    if n_com < 1 or n_sem < 1:
        raise ValueError("cada grupo precisa de pelo menos uma observação")
    return np.array(_pmf_u(n_com, n_sem))


def p_valor_exato_u(u: float, n_com: int, n_sem: int) -> float:
    """P-valor bicaudal: probabilidade, sob H₀, de um U tão ou mais afastado do centro."""
    pmf = distribuicao_nula_u(n_com, n_sem)
    total = n_com * n_sem
    maior = math.ceil(max(u, total - u))
    menor = math.floor(min(u, total - u))
    return float(min(1.0, pmf[maior:].sum() + pmf[: menor + 1].sum()))


def limites_rejeicao_u(n_com: int, n_sem: int, alpha: float = ALPHA) -> tuple[int, int]:
    """Valores de U que já levam à rejeição de H₀ com p < alpha (bicaudal).

    Rejeita se U <= inferior ou U >= superior. Por causa da simetria,
    inferior + superior = n_com * n_sem.
    """
    pmf = distribuicao_nula_u(n_com, n_sem)
    total = n_com * n_sem
    cauda_superior = np.cumsum(pmf[::-1])[::-1]  # P(U >= k)
    candidatos = np.nonzero(2 * cauda_superior < alpha)[0]
    candidatos = candidatos[candidatos > total / 2]
    if candidatos.size == 0:  # amostra pequena demais para rejeitar
        return -1, total + 1
    superior = int(candidatos[0])
    return total - superior, superior


def tamanho_exato_mann_whitney(n_com: int, n_sem: int, alpha: float = ALPHA) -> float:
    """Chance de o Mann-Whitney exato rejeitar H₀ quando ela é verdadeira.

    Como U só assume valores inteiros, a região de rejeição não soma exatamente
    alpha: com grupos pequenos ela fica abaixo, e o teste rejeita menos que 5%.
    """
    inferior, superior = limites_rejeicao_u(n_com, n_sem, alpha)
    pmf = distribuicao_nula_u(n_com, n_sem)
    return float(pmf[: max(inferior + 1, 0)].sum() + pmf[min(superior, pmf.size) :].sum())


def aplicar_testes(
    com_bot: np.ndarray, sem_bot: np.ndarray, alpha: float = ALPHA
) -> dict[str, ResultadoWelch | ResultadoMannWhitney]:
    """Aplica os dois testes ao mesmo conjunto de dados."""
    return {
        "welch": aplicar_welch(com_bot, sem_bot, alpha),
        "mann_whitney": aplicar_mann_whitney(com_bot, sem_bot, alpha),
    }
