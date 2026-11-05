"""Os dois testes aplicados a um conjunto de dados simulado (issue #11).

Gera um único conjunto com o gerador da #9, usando o efeito observado nos dados
reais, aplica o t de Welch e o Mann-Whitney e escreve a interpretação. Como o
conjunto é simulado, sabemos se H₀ é verdadeira e, portanto, se cada teste
acertou. O mesmo exemplo aparece no G2 e na seção 3 do dashboard.

Uso:
    python -m src.exemplo
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ALPHA, SEED, make_rng
from src.formatacao import numero, p_valor, porcentagem
from src.parametros import DELTA_MU_OBSERVADO
from src.simulacao import N_POR_GRUPO, gerar_grupos
from src.testes_estatisticos import (
    ResultadoMannWhitney,
    ResultadoWelch,
    aplicar_mann_whitney,
    aplicar_welch,
)

RAIZ = Path(__file__).resolve().parent.parent
SAIDA_PADRAO = RAIZ / "docs" / "exemplo_testes.md"


@dataclass(frozen=True, eq=False)  # eq=False: comparar vetores do NumPy com == não dá um bool
class Exemplo:
    """Um conjunto simulado e o resultado dos dois testes nele."""

    delta_mu: float
    com_bot: np.ndarray
    sem_bot: np.ndarray
    welch: ResultadoWelch
    mann_whitney: ResultadoMannWhitney
    semente: int = SEED

    @property
    def h0_verdadeira(self) -> bool:
        return self.delta_mu == 0

    def acertou(self, resultado: ResultadoWelch | ResultadoMannWhitney) -> bool:
        """O teste acerta se rejeita H₀ falsa ou se não rejeita H₀ verdadeira."""
        return resultado.rejeita_h0 != self.h0_verdadeira

    def tipo_de_erro(self, resultado: ResultadoWelch | ResultadoMannWhitney) -> str | None:
        if self.acertou(resultado):
            return None
        return "erro tipo I" if self.h0_verdadeira else "erro tipo II"


@dataclass(frozen=True)
class PrMaisLento:
    """O PR mais lento do exemplo e o que acontece com o Welch sem ele."""

    grupo: str  # "com bot" ou "sem bot"
    tempo: float
    maior_do_outro_grupo: float
    media_do_grupo_sem_ele: float
    welch_sem_ele: ResultadoWelch

    def mudou_a_decisao_do_welch(self, welch: ResultadoWelch) -> bool:
        return self.welch_sem_ele.rejeita_h0 != welch.rejeita_h0


def pr_mais_lento(exemplo: Exemplo) -> PrMaisLento:
    """Acha o PR mais lento dos 70 e refaz o Welch sem ele.

    Para o Mann-Whitney esse PR conta só como o mais lento; para o Welch ele
    pesa na média e no desvio-padrão do grupo, o que ajuda a explicar por que
    os dois testes podem discordar.
    """
    if exemplo.com_bot.max() >= exemplo.sem_bot.max():
        grupo, do_maior, do_outro = "com bot", exemplo.com_bot, exemplo.sem_bot
    else:
        grupo, do_maior, do_outro = "sem bot", exemplo.sem_bot, exemplo.com_bot
    sem_ele = np.delete(do_maior, do_maior.argmax())
    alpha = exemplo.welch.alpha
    if grupo == "com bot":
        welch_sem_ele = aplicar_welch(sem_ele, exemplo.sem_bot, alpha)
    else:
        welch_sem_ele = aplicar_welch(exemplo.com_bot, sem_ele, alpha)
    return PrMaisLento(
        grupo=grupo,
        tempo=float(do_maior.max()),
        maior_do_outro_grupo=float(do_outro.max()),
        media_do_grupo_sem_ele=float(sem_ele.mean()),
        welch_sem_ele=welch_sem_ele,
    )


def gerar_exemplo(
    delta_mu: float = DELTA_MU_OBSERVADO,
    n_por_grupo: int = N_POR_GRUPO,
    semente: int = SEED,
    alpha: float = ALPHA,
) -> Exemplo:
    """Sorteia o conjunto de exemplo e aplica os dois testes."""
    com_bot, sem_bot = gerar_grupos(
        delta_mu, n_por_grupo, n_por_grupo, rng=make_rng(semente)
    )
    return Exemplo(
        delta_mu=delta_mu,
        com_bot=com_bot,
        sem_bot=sem_bot,
        welch=aplicar_welch(com_bot, sem_bot, alpha),
        mann_whitney=aplicar_mann_whitney(com_bot, sem_bot, alpha),
        semente=semente,
    )


def _decisao(resultado: ResultadoWelch | ResultadoMannWhitney) -> str:
    return "rejeita H₀" if resultado.rejeita_h0 else "não rejeita H₀"


def _acerto(exemplo: Exemplo, resultado: ResultadoWelch | ResultadoMannWhitney) -> str:
    erro = exemplo.tipo_de_erro(resultado)
    return "sim" if erro is None else f"não ({erro})"


def tabela_resultados(exemplo: Exemplo) -> pd.DataFrame:
    """Resumo dos dois testes, no formato mostrado no dashboard."""
    w, m = exemplo.welch, exemplo.mann_whitney
    alpha = porcentagem(w.alpha, 0)
    return pd.DataFrame(
        [
            {
                "Teste": "t de Welch",
                "O que compara": "médias",
                "Estatística": f"t = {numero(w.t)} (gl = {numero(w.gl, 1)})",
                "p-valor": p_valor(w.p_valor),
                "Tamanho do efeito": (
                    f"diferença de médias = {numero(w.diferenca_medias, 1)} h "
                    f"(d = {numero(w.d_cohen)})"
                ),
                f"Decisão (α = {alpha})": _decisao(w),
                "Acertou?": _acerto(exemplo, w),
            },
            {
                "Teste": "Mann-Whitney",
                "O que compara": "postos",
                "Estatística": f"U = {numero(m.u, 0)} de {numero(m.n_pares, 0)} pares",
                "p-valor": p_valor(m.p_valor),
                "Tamanho do efeito": (
                    f"P(PR com bot demorar mais) = {numero(m.prob_superioridade)} "
                    f"(r = {numero(m.correlacao_bisserial)})"
                ),
                f"Decisão (α = {alpha})": _decisao(m),
                "Acertou?": _acerto(exemplo, m),
            },
        ]
    )


def _frase_p_valor(resultado: ResultadoWelch | ResultadoMannWhitney, estatistica: str) -> str:
    p = p_valor(resultado.p_valor)
    chance = porcentagem(resultado.p_valor)
    if resultado.rejeita_h0:
        return (
            f"p = {p} quer dizer que, se o bot não mudasse nada, só {chance} das "
            f"amostras dariam {estatistica}. Isso não é a chance de H₀ ser "
            "verdadeira, e também não diz se o efeito é grande."
        )
    return (
        f"p = {p} quer dizer que {chance} das amostras sem efeito dariam "
        f"{estatistica}. Não rejeitar H₀ também não prova que o bot não muda "
        "nada: pode faltar poder para ver o efeito."
    )


def interpretacao(exemplo: Exemplo) -> str:
    """Interpretação do exemplo em Markdown (usada no docs/ e no dashboard)."""
    w, m = exemplo.welch, exemplo.mann_whitney
    n = len(exemplo.com_bot)
    centro_u = m.n_pares / 2
    inferior, superior = m.regiao_rejeicao

    # O PR mais lento de todos mostra bem a diferença entre os dois testes.
    lento = pr_mais_lento(exemplo)
    if lento.mudou_a_decisao_do_welch(w):
        decisao_sem_ele = (
            "rejeitaria H₀" if lento.welch_sem_ele.rejeita_h0 else "deixaria de rejeitar H₀"
        )
        efeito_do_lento = (
            f"Sem ele, o Welch daria p = {p_valor(lento.welch_sem_ele.p_valor)} e "
            f"{decisao_sem_ele}: um único PR mudou a decisão."
        )
    else:
        efeito_do_lento = "Tirar esse PR não mudaria a decisão do Welch."

    if exemplo.h0_verdadeira:
        verdade = (
            "Sorteamos os dois grupos da mesma distribuição, então **H₀ é "
            "verdadeira** e o correto é não rejeitá-la."
        )
    else:
        razao = numero(np.exp(exemplo.delta_mu))
        verdade = (
            f"Usamos o efeito observado nos dados reais (δ = {numero(exemplo.delta_mu)}, "
            f"PRs com bot {razao} vezes mais lentos). Como fomos nós que geramos os "
            "dados, sabemos a resposta certa: **H₀ é falsa** e o correto é rejeitá-la."
        )

    if abs(w.t) > w.t_critico:
        posicao_t = f"acima do valor crítico de {numero(w.t_critico)} em módulo"
    else:
        posicao_t = f"abaixo do valor crítico de {numero(w.t_critico)} em módulo"

    def desfecho(resultado: ResultadoWelch | ResultadoMannWhitney) -> str:
        erro = exemplo.tipo_de_erro(resultado)
        decisao = "rejeitou H₀" if resultado.rejeita_h0 else "não rejeitou H₀"
        if erro is None:
            return f"o teste **{decisao}** e acertou"
        return f"o teste **{decisao}** e cometeu um **{erro}**"

    paragrafos = [
        "### O conjunto simulado",
        f"Sorteamos {n} PRs com bot e {n} sem bot com o gerador da #9. {verdade}",
        f"Neste conjunto, a mediana ficou em {numero(np.median(exemplo.com_bot), 1)} h "
        f"com bot e {numero(np.median(exemplo.sem_bot), 1)} h sem bot. O PR mais lento "
        f"de todos ficou no grupo {lento.grupo}, com {numero(lento.tempo, 1)} h.",
        "### O que cada teste fez",
        f"**t de Welch.** Comparou as médias: {numero(w.media_com, 1)} h com bot contra "
        f"{numero(w.media_sem, 1)} h sem bot, uma diferença de "
        f"{numero(w.diferenca_medias, 1)} h (IC de 95%: {numero(w.ic95[0], 1)} h a "
        f"{numero(w.ic95[1], 1)} h). Os desvios-padrão foram de {numero(w.dp_com, 1)} h "
        f"e {numero(w.dp_sem, 1)} h, puxados pelos PRs mais lentos: sem o PR de "
        f"{numero(lento.tempo, 1)} h, a média do grupo {lento.grupo} cairia para "
        f"{numero(lento.media_do_grupo_sem_ele, 1)} h. O t ficou em {numero(w.t)}, "
        f"{posicao_t}. Com p = {p_valor(w.p_valor)}, {desfecho(w)}. {efeito_do_lento}",
        f"**Mann-Whitney.** Comparou os postos. Dos {numero(m.n_pares, 0)} pares "
        f"possíveis (um PR com bot e um sem bot), o PR com bot demorou mais em "
        f"{numero(m.u, 0)}, ou {porcentagem(m.prob_superioridade)} dos pares. Se o bot "
        f"não mudasse nada, o esperado seria perto de {numero(centro_u, 1)} pares, e a "
        f"região de rejeição é U ≤ {numero(inferior, 0)} ou U ≥ {numero(superior, 0)}. "
        f"Para esse teste, o PR de {numero(lento.tempo, 1)} h conta só como o mais lento: "
        f"com qualquer tempo acima de {numero(lento.maior_do_outro_grupo, 1)} h, que é o "
        f"maior do outro grupo, U seria o mesmo. Com p = {p_valor(m.p_valor)}, "
        f"{desfecho(m)}.",
        "### O que o p-valor do exemplo quer dizer",
        "O p-valor é a probabilidade de, com H₀ verdadeira, sair uma estatística tão "
        "afastada do centro quanto a que observamos. No G2 ele aparece como a área "
        "pintada nas duas caudas.",
        "- No Mann-Whitney, "
        + _frase_p_valor(
            m, f"um U tão longe de {numero(centro_u, 1)} quanto {numero(m.u, 0)}"
        )
        + "\n- No Welch, "
        + _frase_p_valor(w, f"um |t| maior ou igual a {numero(abs(w.t))}"),
        "### Cuidado",
        "É um conjunto só. Com outra semente os dois testes poderiam concordar, ou "
        "trocar de papel. Quantas vezes cada teste acerta é o que as simulações de Q1 "
        "e Q2 (issues #14 e #15) vão medir.",
    ]
    return "\n\n".join(paragrafos) + "\n"


def documento(exemplo: Exemplo) -> str:
    """Conteúdo de docs/exemplo_testes.md."""
    tabela = tabela_resultados(exemplo)
    cabecalho = "| " + " | ".join(tabela.columns) + " |"
    separador = "|" + "---|" * len(tabela.columns)
    linhas = ["| " + " | ".join(map(str, linha)) + " |" for linha in tabela.to_numpy()]
    return f"""# Os dois testes em um conjunto simulado

> Gerado por `python -m src.exemplo` (issue #11). Semente {exemplo.semente},
> {len(exemplo.com_bot)} PRs por grupo, δ = {numero(exemplo.delta_mu)}, α = {numero(ALPHA)} bicaudal.
> O cenário e as hipóteses estão em [`cenario.md`](cenario.md).

### Resultado

{cabecalho}
{separador}
{chr(10).join(linhas)}

{interpretacao(exemplo)}"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    args = parser.parse_args()

    exemplo = gerar_exemplo()
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(documento(exemplo), encoding="utf-8")
    # Só ASCII no terminal: o console do Windows não imprime α nem H₀.
    w, m = exemplo.welch, exemplo.mann_whitney
    print(f"t de Welch:   t = {w.t:.3f}, gl = {w.gl:.1f}, p = {w.p_valor:.4f}")
    print(f"Mann-Whitney: U = {m.u:.0f}, p = {m.p_valor:.4f}")
    print(f"Interpretacao salva em {args.saida}")


if __name__ == "__main__":
    main()
