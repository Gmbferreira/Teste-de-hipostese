"""Situações em que os dados não se comportam bem para o t de Welch (Q3, issue #16).

As situações são as mesmas registradas em docs/expectativa.md antes de
simular. Em cada uma medimos o erro tipo I (δ = 0) e o poder (δ > 0) dos dois
testes, com 10.000 repetições por ponto. A situação realista (Q1 e Q2) fica em
src/monte_carlo.py; aqui estão só as variações de Q3 e a referência na escala log.

Uso:
    python -m src.situacoes
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import ALPHA, N_SIMULACOES, SEED
from src.formatacao import numero, porcentagem
from src.monte_carlo import (
    PASTA_RESULTADOS,
    REALISTA,
    TESTES,
    Situacao,
    erro_tipo_i,
    salvar_csv,
    simular,
    tabela_rejeicoes,
)
from src.parametros import GRADE_DELTA_MU_SUGERIDA
from src.estilo import ROTULOS_TESTE

RAIZ = Path(__file__).resolve().parent.parent
SAIDA_ERRO_TIPO_I = PASTA_RESULTADOS / "q3_erro_tipo_i.csv"
SAIDA_PODER = PASTA_RESULTADOS / "q3_poder.csv"
SAIDA_DOCS = RAIZ / "docs" / "situacoes_q3.md"

AMOSTRAS_PEQUENAS = replace(
    REALISTA,
    chave="amostras_pequenas",
    nome="Amostras pequenas",
    descricao="mesma lognormal, 10 PRs por grupo",
    motivo="com poucos dados o Welch depende mais da normalidade",
    n_com=10,
    n_sem=10,
)
DESBALANCEADO = replace(
    REALISTA,
    chave="desbalanceado",
    nome="Grupos desbalanceados",
    descricao="10 PRs com bot e 60 sem bot",
    motivo=(
        "é comum o bot estar em só uma parte dos PRs, e com grupos de tamanhos "
        "diferentes a assimetria das duas médias não se compensa"
    ),
    n_com=10,
    n_sem=60,
)
OUTLIERS = replace(
    REALISTA,
    chave="outliers",
    nome="Outliers",
    descricao="cerca de 5% dos PRs ficam esquecidos e levam de 1 a 4 semanas a mais",
    motivo="PRs abandonados e retomados depois aparecem em repositórios reais",
    prob_outlier=0.05,
)
ESCALA_LOG = replace(
    REALISTA,
    chave="escala_log",
    nome="Escala log (referência)",
    descricao="mesmos dados da situação realista, com os testes aplicados ao log do tempo",
    motivo="é a situação boa para o Welch, porque o log dos tempos segue uma normal",
    escala_log=True,
)

SITUACOES_Q3: tuple[Situacao, ...] = (AMOSTRAS_PEQUENAS, DESBALANCEADO, OUTLIERS, ESCALA_LOG)
TODAS_AS_SITUACOES: tuple[Situacao, ...] = (REALISTA, *SITUACOES_Q3)
POR_CHAVE: dict[str, Situacao] = {s.chave: s for s in TODAS_AS_SITUACOES}


def erro_tipo_i_q3(
    repeticoes: int = N_SIMULACOES, semente: int = SEED, alpha: float = ALPHA
) -> pd.DataFrame:
    """Repete a Q1 (δ = 0) em cada situação de Q3."""
    return erro_tipo_i(SITUACOES_Q3, repeticoes, semente, alpha)


def poder_q3(
    grade: tuple[float, ...] = GRADE_DELTA_MU_SUGERIDA,
    repeticoes: int = N_SIMULACOES,
    semente: int = SEED,
    alpha: float = ALPHA,
) -> pd.DataFrame:
    """Repete a Q2 (efeitos crescentes, começando em zero) em cada situação de Q3."""
    simulacoes = [
        simular(situacao, delta, repeticoes, semente)
        for situacao in SITUACOES_Q3
        for delta in grade
    ]
    return tabela_rejeicoes(simulacoes, alpha)


def _celula(linha: pd.Series) -> str:
    return (
        f"{porcentagem(linha.taxa, 2)} "
        f"({porcentagem(linha.ic95_inferior, 2)} a {porcentagem(linha.ic95_superior, 2)})"
    )


def documento(tipo_i: pd.DataFrame, poder: pd.DataFrame) -> str:
    """Conteúdo de docs/situacoes_q3.md: as situações, o motivo e os resultados."""
    linhas_situacoes = [
        f"| {s.nome} | {s.descricao} | {s.motivo} |" for s in SITUACOES_Q3
    ]

    linhas_tipo_i = []
    for s in SITUACOES_Q3:
        do_caso = tipo_i[tipo_i["situacao"] == s.chave].set_index("teste")
        linhas_tipo_i.append(
            f"| {s.nome} | " + " | ".join(_celula(do_caso.loc[t]) for t in TESTES) + " |"
        )

    blocos_poder = []
    for s in SITUACOES_Q3:
        do_caso = poder[poder["situacao"] == s.chave]
        linhas = []
        for delta, grupo in do_caso.groupby("delta_mu", sort=True):
            por_teste = grupo.set_index("teste")
            linhas.append(
                f"| {numero(delta)} | {numero(np.exp(delta))}× | "
                + " | ".join(porcentagem(por_teste.loc[t, "taxa"], 1) for t in TESTES)
                + " |"
            )
        blocos_poder.append(
            f"### {s.nome}\n\n"
            f"| δ | PRs com bot mais lentos | {ROTULOS_TESTE['welch']} | "
            f"{ROTULOS_TESTE['mann_whitney']} |\n|---:|---:|---:|---:|\n" + "\n".join(linhas)
        )

    cabecalho_testes = " | ".join(ROTULOS_TESTE[t] for t in TESTES)
    return f"""# Situações de Q3

> Gerado por `python -m src.situacoes` (issue #16). {numero(N_SIMULACOES, 0)} repetições
> por ponto, semente {SEED}, α = {numero(ALPHA)} bicaudal. As situações são as que
> registramos em [`expectativa.md`](expectativa.md) antes de simular.

A situação realista (lognormal ajustada aos dados reais, 35 PRs por grupo) é a
base de Q1 e Q2. Em Q3 repetimos as duas perguntas mudando uma coisa de cada
vez. Todas as situações usam a mesma semente, então os sorteios de base são os
mesmos e a diferença entre elas vem só do que foi alterado.

## As situações

| Situação | O que muda | Por que incluímos |
|---|---|---|
{chr(10).join(linhas_situacoes)}

## Erro tipo I (δ = 0)

Proporção de p-valores abaixo de 5% com H₀ verdadeira, com o intervalo de 95%
entre parênteses.

| Situação | {cabecalho_testes} |
|---|---:|---:|
{chr(10).join(linhas_tipo_i)}

## Poder

Proporção de rejeições para cada tamanho de efeito. Com δ = 0 o valor é o
próprio erro tipo I.

{chr(10).join(blocos_poder)}
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    tipo_i = erro_tipo_i_q3()
    poder = poder_q3()
    salvar_csv(tipo_i, SAIDA_ERRO_TIPO_I)
    salvar_csv(poder, SAIDA_PODER)
    SAIDA_DOCS.write_text(documento(tipo_i, poder), encoding="utf-8")

    for linha in tipo_i.itertuples():
        print(f"{linha.situacao:<18} {linha.teste:<13} erro tipo I = {100 * linha.taxa:.2f}%")
    print(f"Resultados salvos em {PASTA_RESULTADOS} e {SAIDA_DOCS}")


if __name__ == "__main__":
    main()
