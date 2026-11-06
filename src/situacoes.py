"""Situações em que os dados não se comportam bem para o t de Welch (Q3, issue #16).

As quatro situações de Q3 são as registradas em docs/expectativa.md antes de
simular. Em cada uma medimos o erro tipo I (δ = 0) e o poder (δ > 0) dos dois
testes, com 10.000 repetições por ponto. A situação realista (Q1 e Q2) fica em
src/monte_carlo.py.

Depois de simular incluímos uma análise de sensibilidade, que não estava na
expectativa: a reamostragem dos tempos reais. A lognormal ajustada gera PRs bem
mais lentos que os da amostra, e essa situação mostra o que muda quando a cauda
é a dos dados coletados.

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
from src.estilo import ROTULOS_TESTE
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
from src.parametros import GRADE_DELTA_MU_SUGERIDA, GRUPO_CONTROLE

RAIZ = Path(__file__).resolve().parent.parent
DADOS_REAIS = RAIZ / "data" / "prs_merge_time.csv"
SAIDA_ERRO_TIPO_I = PASTA_RESULTADOS / "q3_erro_tipo_i.csv"
SAIDA_PODER = PASTA_RESULTADOS / "q3_poder.csv"
SAIDA_DOCS = RAIZ / "docs" / "situacoes_q3.md"

# Desvio do ruído somado ao log de cada tempo reamostrado: só o bastante para
# não haver valores repetidos, sem mudar a forma da amostra (cerca de 25%).
RUIDO_REAMOSTRAGEM = 0.25

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


def _log_dos_tempos_reais(grupo: str = GRUPO_CONTROLE) -> tuple[float, ...]:
    dados = pd.read_csv(DADOS_REAIS)
    return tuple(np.log(dados.loc[dados["grupo"] == grupo, "tempo_merge_horas"]))


REAMOSTRAGEM = replace(
    REALISTA,
    chave="reamostragem",
    nome="Tempos reais reamostrados (sensibilidade)",
    descricao=(
        "sorteia com reposição os tempos dos 35 PRs reais sem bot, com uma variação de "
        "cerca de 25% em cada tempo para não haver empates"
    ),
    motivo=(
        "a lognormal ajustada gera PRs bem mais lentos que os reais; aqui a cauda é a "
        "da própria amostra (incluída depois de simular, não estava na expectativa)"
    ),
    base_log=_log_dos_tempos_reais(),
    ruido_log=RUIDO_REAMOSTRAGEM,
)

SITUACOES_Q3: tuple[Situacao, ...] = (AMOSTRAS_PEQUENAS, DESBALANCEADO, OUTLIERS, ESCALA_LOG)
SENSIBILIDADE: tuple[Situacao, ...] = (REAMOSTRAGEM,)
SITUACOES_SIMULADAS: tuple[Situacao, ...] = (*SITUACOES_Q3, *SENSIBILIDADE)
TODAS_AS_SITUACOES: tuple[Situacao, ...] = (REALISTA, *SITUACOES_SIMULADAS)
POR_CHAVE: dict[str, Situacao] = {s.chave: s for s in TODAS_AS_SITUACOES}


def erro_tipo_i_q3(
    repeticoes: int = N_SIMULACOES, semente: int = SEED, alpha: float = ALPHA
) -> pd.DataFrame:
    """Repete a Q1 (δ = 0) em cada situação de Q3 e na de sensibilidade."""
    return erro_tipo_i(SITUACOES_SIMULADAS, repeticoes, semente, alpha)


def poder_q3(
    grade: tuple[float, ...] = GRADE_DELTA_MU_SUGERIDA,
    repeticoes: int = N_SIMULACOES,
    semente: int = SEED,
    alpha: float = ALPHA,
) -> pd.DataFrame:
    """Repete a Q2 (efeitos crescentes, começando em zero) nas mesmas situações."""
    simulacoes = [
        simular(situacao, delta, repeticoes, semente)
        for situacao in SITUACOES_SIMULADAS
        for delta in grade
    ]
    return tabela_rejeicoes(simulacoes, alpha)


def _celula(linha: pd.Series) -> str:
    return (
        f"{porcentagem(linha.taxa, 2)} "
        f"({porcentagem(linha.ic95_inferior, 2)} a {porcentagem(linha.ic95_superior, 2)})"
    )


def _taxas(poder: pd.DataFrame, chave: str, teste: str) -> pd.Series:
    do_caso = poder[(poder["situacao"] == chave) & (poder["teste"] == teste)]
    return do_caso.set_index("delta_mu")["taxa"].sort_index()


def observacoes(poder: pd.DataFrame) -> list[str]:
    """O que chama atenção nos resultados, em frases curtas e com os números."""
    frases = []

    welch = _taxas(poder, "desbalanceado", "welch")
    if not welch.empty and (welch.iloc[1:] < welch.iloc[0]).any():
        delta_min = float(welch.iloc[1:].idxmin())
        frases.append(
            f"Com grupos desbalanceados o Welch fica viesado: com efeito δ = "
            f"{numero(delta_min)} ele rejeita H₀ em {porcentagem(welch.loc[delta_min], 1)} "
            f"dos casos, menos do que sem efeito nenhum ({porcentagem(welch.iloc[0], 1)})."
        )

    welch, mw = _taxas(poder, "reamostragem", "welch"), _taxas(poder, "reamostragem", "mann_whitney")
    if not welch.empty:
        frase = (
            f"Com os tempos reais reamostrados o erro tipo I do Welch sobe para "
            f"{porcentagem(welch.iloc[0], 1)}, mais perto de 5% do que na lognormal."
        )
        na_frente = [d for d in welch.index if d > 0 and welch.loc[d] > mw.loc[d]]
        if na_frente:
            primeiro = na_frente[0]
            frase += (
                f" O Mann-Whitney continua com mais poder nos efeitos pequenos, mas a "
                f"partir de δ = {numero(primeiro)} o Welch passa na frente "
                f"({porcentagem(welch.loc[primeiro], 1)} contra "
                f"{porcentagem(mw.loc[primeiro], 1)}): com a cauda da amostra a vantagem "
                "muda de lado nos efeitos grandes."
            )
        frases.append(frase)

    welch, mw = _taxas(poder, "escala_log", "welch"), _taxas(poder, "escala_log", "mann_whitney")
    if not welch.empty and (welch.iloc[1:] >= mw.iloc[1:]).all():
        maior = 100 * float((welch.iloc[1:] - mw.iloc[1:]).max())
        unidade = "pontos percentuais" if round(maior, 1) >= 2 else "ponto percentual"
        frases.append(
            "Na escala log o Welch tem poder igual ou um pouco maior que o do Mann-Whitney "
            f"(no máximo {numero(maior, 1)} {unidade} a mais), e o Mann-Whitney "
            "repete exatamente o poder da situação realista, porque tirar o log não muda a "
            "ordem dos tempos."
        )
    return frases


def documento(tipo_i: pd.DataFrame, poder: pd.DataFrame) -> str:
    """Conteúdo de docs/situacoes_q3.md: as situações, o motivo e os resultados."""
    linhas_situacoes = [
        f"| {s.nome} | {s.descricao} | {s.motivo} |" for s in SITUACOES_SIMULADAS
    ]

    linhas_tipo_i = []
    for s in SITUACOES_SIMULADAS:
        do_caso = tipo_i[tipo_i["situacao"] == s.chave].set_index("teste")
        linhas_tipo_i.append(
            f"| {s.nome} | " + " | ".join(_celula(do_caso.loc[t]) for t in TESTES) + " |"
        )

    blocos_poder = []
    for s in SITUACOES_SIMULADAS:
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
    lista_observacoes = "\n".join(f"- {frase}" for frase in observacoes(poder))
    return f"""# Situações de Q3

> Gerado por `python -m src.situacoes` (issue #16). {numero(N_SIMULACOES, 0)} repetições
> por ponto, semente {SEED}, α = {numero(ALPHA)} bicaudal. As quatro situações de Q3
> são as que registramos em [`expectativa.md`](expectativa.md) antes de simular; a
> reamostragem dos tempos reais foi incluída depois, como análise de sensibilidade.

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

## O que chama atenção

{lista_observacoes}
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
