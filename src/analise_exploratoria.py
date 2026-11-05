"""Análise exploratória dos dados reais e parâmetros da simulação (issue #4).

Lê data/prs_merge_time.csv, calcula estatísticas descritivas, verifica
assimetria/outliers/normalidade, compara distribuições candidatas e gera:

- docs/analise_exploratoria.md
- docs/figuras/eda_boxplot.png
- docs/figuras/eda_qq_log.png

Uso:
    python -m src.analise_exploratoria
"""

from __future__ import annotations

import argparse
import math
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

from src.estilo import CORES_GRUPO, ROTULOS_GRUPO
from src.parametros import (
    DELTA_MU_OBSERVADO,
    GRADE_DELTA_MU_SUGERIDA,
    GRUPO_CONTROLE,
    PARAMETROS_REAIS,
    RAZAO_GEOMETRICA_OBSERVADA,
    RAZAO_MEDIANAS_AMOSTRAIS,
)

RAIZ = Path(__file__).resolve().parent.parent
DADOS_PADRAO = RAIZ / "data" / "prs_merge_time.csv"
SAIDA_PADRAO = RAIZ / "docs" / "analise_exploratoria.md"
FIGURAS_PADRAO = RAIZ / "docs" / "figuras"

GRUPOS = ("com_bot", "sem_bot")
DISTRIBUICOES = {
    "lognormal": stats.lognorm,
    "gamma": stats.gamma,
    "weibull": stats.weibull_min,
}


def fmt(valor: float, casas: int = 2) -> str:
    """Formata número no padrão brasileiro."""
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_p(p: float) -> str:
    """Formata p-valor, usando notação científica quando muito pequeno."""
    if p < 1e-4:
        return f"{p:.1e}".replace(".", ",")
    return fmt(p, 4)


def descritivas(x: np.ndarray) -> dict[str, float]:
    q1, q3 = np.percentile(x, [25, 75])
    return {
        "n": len(x),
        "media": float(np.mean(x)),
        "mediana": float(np.median(x)),
        "dp": float(np.std(x, ddof=1)),
        "min": float(np.min(x)),
        "q1": float(q1),
        "q3": float(q3),
        "max": float(np.max(x)),
        "cv": float(np.std(x, ddof=1) / np.mean(x)),
        "assimetria": float(stats.skew(x, bias=False)),
        "curtose": float(stats.kurtosis(x, bias=False)),
        "iqr": float(q3 - q1),
    }


def outliers(df: pd.DataFrame, grupo: str) -> list[dict]:
    dados = df[df["grupo"] == grupo]
    x = dados["tempo_merge_horas"].to_numpy()
    q1, q3 = np.percentile(x, [25, 75])
    iqr = q3 - q1
    limite_inferior = q1 - 1.5 * iqr
    limite_superior = q3 + 1.5 * iqr
    mascara = (dados["tempo_merge_horas"] < limite_inferior) | (
        dados["tempo_merge_horas"] > limite_superior
    )
    return (
        dados.loc[mascara, ["pr_number", "tempo_merge_horas"]]
        .sort_values("tempo_merge_horas", ascending=False)
        .to_dict("records")
    )


def testes_forma(a: np.ndarray, b: np.ndarray) -> dict:
    resultado = {}
    for nome, x in (("com_bot", a), ("sem_bot", b)):
        log_x = np.log(x)
        resultado[nome] = {
            "shapiro_bruto": stats.shapiro(x).pvalue,
            "shapiro_log": stats.shapiro(log_x).pvalue,
            "dagostino_log": stats.normaltest(log_x).pvalue,
        }
    resultado["levene_bruto"] = stats.levene(a, b).pvalue
    resultado["levene_log"] = stats.levene(np.log(a), np.log(b)).pvalue
    return resultado


def ajustar_distribuicoes(x: np.ndarray) -> dict[str, dict]:
    ajustes = {}
    for nome, distribuicao in DISTRIBUICOES.items():
        par = distribuicao.fit(x, floc=0)
        log_verossimilhanca = float(np.sum(distribuicao.logpdf(x, *par)))
        n_parametros = len(par) - 1  # loc foi fixado em zero
        ajustes[nome] = {
            "params": par,
            "aic": 2 * n_parametros - 2 * log_verossimilhanca,
            "ks_p": stats.kstest(x, distribuicao.cdf, args=par).pvalue,
        }
    return ajustes


def descrever_params(nome: str, par: tuple) -> str:
    if nome == "lognormal":
        return f"μ={fmt(math.log(par[2]))}, σ={fmt(par[0])}"
    if nome == "gamma":
        return f"k={fmt(par[0])}, θ={fmt(par[2])}"
    return f"k={fmt(par[0])}, λ={fmt(par[2])}"


def validar_parametros(df: pd.DataFrame, ajustes: dict[str, dict]) -> None:
    """Garante que src/parametros.py continua coerente com os dados."""
    for grupo in GRUPOS:
        parametros = PARAMETROS_REAIS[grupo]
        sigma, _, scale = ajustes[grupo]["lognormal"]["params"]
        mu = math.log(scale)
        n = int((df["grupo"] == grupo).sum())
        if parametros.n_real != n:
            raise ValueError(
                f"{grupo}: n_real={parametros.n_real} no módulo, mas {n} nos dados"
            )
        if not math.isclose(parametros.mu, mu, rel_tol=1e-9) or not math.isclose(
            parametros.sigma, sigma, rel_tol=1e-9
        ):
            raise ValueError(
                f"{grupo}: parâmetros de src/parametros.py não batem com o ajuste "
                f"atual (mu={mu!r}, sigma={sigma!r}). Rode o ajuste e atualize o módulo."
            )


def cohen_d_log(a: np.ndarray, b: np.ndarray) -> float:
    la, lb = np.log(a), np.log(b)
    n1, n2 = len(la), len(lb)
    pooled = math.sqrt(
        ((n1 - 1) * np.var(la, ddof=1) + (n2 - 1) * np.var(lb, ddof=1))
        / (n1 + n2 - 2)
    )
    return float((la.mean() - lb.mean()) / pooled)


def salvar_figuras(df: pd.DataFrame, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    dados = [df.loc[df["grupo"] == g, "tempo_merge_horas"].to_numpy() for g in GRUPOS]
    box = ax.boxplot(dados, patch_artist=True, widths=0.5)
    for caixa, grupo in zip(box["boxes"], GRUPOS):
        caixa.set_facecolor(CORES_GRUPO[grupo])
        caixa.set_alpha(0.75)
    ax.set_xticks([1, 2])
    ax.set_xticklabels([ROTULOS_GRUPO[g] for g in GRUPOS])
    ax.set_yscale("log")
    ax.set_ylabel("Tempo até o merge (horas, escala log)")
    ax.set_title("Distribuição do tempo até o merge por grupo")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(destino / "eda_boxplot.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, eixos = plt.subplots(1, 2, figsize=(11, 4.5))
    for eixo, grupo in zip(eixos, GRUPOS):
        log_x = np.log(df.loc[df["grupo"] == grupo, "tempo_merge_horas"].to_numpy())
        stats.probplot(log_x, dist="norm", plot=eixo)
        eixo.set_title(ROTULOS_GRUPO[grupo])
        eixo.set_xlabel("Quantis teóricos da normal")
        eixo.set_ylabel("log(tempo até o merge)")
        eixo.grid(alpha=0.3)
    fig.suptitle("Q-Q do log(tempo) contra a normal")
    fig.tight_layout()
    fig.savefig(destino / "eda_qq_log.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def gerar_relatorio(df: pd.DataFrame) -> str:
    a = df.loc[df["grupo"] == "com_bot", "tempo_merge_horas"].to_numpy()
    b = df.loc[df["grupo"] == "sem_bot", "tempo_merge_horas"].to_numpy()
    desc = {
        g: descritivas(df.loc[df["grupo"] == g, "tempo_merge_horas"].to_numpy())
        for g in GRUPOS
    }
    outs = {g: outliers(df, g) for g in GRUPOS}
    forma = testes_forma(a, b)
    ajustes = {
        g: ajustar_distribuicoes(
            df.loc[df["grupo"] == g, "tempo_merge_horas"].to_numpy()
        )
        for g in GRUPOS
    }
    validar_parametros(df, ajustes)
    d = cohen_d_log(a, b)

    linhas_desc = []
    for g in GRUPOS:
        v = desc[g]
        linhas_desc.append(
            f"| `{g}` | {v['n']} | {fmt(v['media'])} | {fmt(v['mediana'])} | "
            f"{fmt(v['dp'])} | {fmt(v['min'])} | {fmt(v['q1'])} | {fmt(v['q3'])} | "
            f"{fmt(v['max'])} | {fmt(v['cv'])} | {fmt(v['assimetria'])} | {fmt(v['curtose'])} |"
        )

    linhas_forma = []
    for g in GRUPOS:
        v = forma[g]
        linhas_forma.append(
            f"| `{g}` | {fmt_p(v['shapiro_bruto'])} | {fmt_p(v['shapiro_log'])} | "
            f"{fmt_p(v['dagostino_log'])} |"
        )

    linhas_ajuste = []
    for g in GRUPOS:
        for nome, info in ajustes[g].items():
            linhas_ajuste.append(
                f"| `{g}` | {nome} | {fmt(info['aic'], 1)} | {fmt_p(info['ks_p'])} | "
                f"{descrever_params(nome, info['params'])} |"
            )

    linhas_params = []
    for g in GRUPOS:
        p = PARAMETROS_REAIS[g]
        linhas_params.append(
            f"| `{g}` | {fmt(p.mu, 4)} | {fmt(p.sigma, 4)} | {fmt(p.mediana)} | "
            f"{fmt(p.mediana_amostral)} | {fmt(p.media)} | {fmt(p.desvio)} | {p.n_real} |"
        )

    lista_outliers = []
    for g in GRUPOS:
        if outs[g]:
            itens = ", ".join(
                f"PR #{o['pr_number']} ({fmt(o['tempo_merge_horas'])} h)" for o in outs[g]
            )
            lista_outliers.append(f"- `{g}` ({len(outs[g])}): {itens}")
        else:
            lista_outliers.append(f"- `{g}`: nenhum outlier pelo critério IQR 1,5")

    rapidos = {
        g: int((df.loc[df["grupo"] == g, "tempo_merge_horas"] < 3).sum())
        for g in GRUPOS
    }
    lentos = {
        g: int((df.loc[df["grupo"] == g, "tempo_merge_horas"] > 10).sum())
        for g in GRUPOS
    }

    q99_obs = {
        g: float(np.percentile(df.loc[df["grupo"] == g, "tempo_merge_horas"], 99))
        for g in GRUPOS
    }
    q99_ajustado = {
        g: float(
            stats.lognorm.ppf(
                0.99,
                PARAMETROS_REAIS[g].sigma,
                scale=math.exp(PARAMETROS_REAIS[g].mu),
            )
        )
        for g in GRUPOS
    }

    tamanho = df["adicoes"] + df["delecoes"]
    tamanho_mediana = {g: float(tamanho[df["grupo"] == g].median()) for g in GRUPOS}
    revisoes_humanas = {
        g: float(df.loc[df["grupo"] == g, "revisoes_humanas"].median())
        for g in GRUPOS
    }

    data_geracao = datetime.now().strftime("%d/%m/%Y %H:%M")

    return f"""# Análise exploratória dos dados reais

> Relatório gerado por `python -m src.analise_exploratoria` em {data_geracao}.
> Amostra: [`data/prs_merge_time.csv`](../data/prs_merge_time.csv) — {desc['com_bot']['n']} PRs com review de bot e {desc['sem_bot']['n']} sem.
> Metodologia da coleta: [`data/README.md`](../data/README.md).

## 1. Amostra

A amostra tem {len(df)} pull requests mergeados do repositório
`supabase/supabase`, coletados em 2026-11-05: {desc['com_bot']['n']} no grupo
`com_bot` e {desc['sem_bot']['n']} no grupo `sem_bot`. O tempo até o merge é
medido em horas, de `created_at` até `merged_at`.

## 2. Estatísticas descritivas

| Grupo | n | Média (h) | Mediana (h) | DP (h) | Mín. (h) | Q1 (h) | Q3 (h) | Máx. (h) | CV | Assimetria | Curtose |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(linhas_desc)}

Os dois grupos são fortemente assimétricos à direita: a média fica bem acima
da mediana e o máximo é muito maior que o Q3. O grupo `com_bot` tem mediana e
média maiores que o `sem_bot`.

## 3. Assimetria e outliers

Outliers pelo critério de 1,5 × IQR:

{chr(10).join(lista_outliers)}

A distribuição não é um bloco único: em `com_bot`, {rapidos['com_bot']} dos
{desc['com_bot']['n']} PRs mergearam em menos de 3 h e {lentos['com_bot']}
levaram mais de 10 h. Em `sem_bot`, {rapidos['sem_bot']} dos
{desc['sem_bot']['n']} mergearam em menos de 3 h e {lentos['sem_bot']} levaram
mais de 10 h. Ou seja, há um grupo de merges rápidos e outro de merges
lentos, o que uma distribuição unimodal só consegue aproximar.

## 4. Normalidade e homocedasticidade

| Grupo | Shapiro bruto (p) | Shapiro no log (p) | D'Agostino no log (p) |
|---|---:|---:|---:|
{chr(10).join(linhas_forma)}

A normalidade é rejeitada na escala bruta nos dois grupos. A transformação log
melhora muito o ajuste, mas `sem_bot` ainda é rejeitado por Shapiro e por
D'Agostino no nível de 5%. Levene entre os grupos: p = {fmt_p(forma['levene_bruto'])}
na escala bruta e p = {fmt_p(forma['levene_log'])} no log — não há evidência
forte de variâncias desiguais.

## 5. Comparação de distribuições

| Grupo | Distribuição | AIC | KS (p) | Parâmetros |
|---|---|---|---:|---|
{chr(10).join(linhas_ajuste)}

As três distribuições têm AIC próximo e nenhuma é rejeitada pelo KS em
qualquer um dos grupos. Em `sem_bot`, lognormal e Weibull são equivalentes na
prática.
Optamos pela **lognormal** por ter interpretação direta (mediana e σ), ser a
distribuição sugerida no enunciado e permitir representar o efeito como um
deslocamento em `mu`. Gamma e Weibull ficam registradas como sensibilidade.

## 6. Parâmetros da simulação

Ajuste por máxima verossimilhança de uma lognormal com loc fixo em zero.
`mediana = exp(mu)` e `média = exp(mu + sigma²/2)`.

| Grupo | μ | σ | Mediana ajustada (h) | Mediana amostral (h) | Média ajustada (h) | DP ajustado (h) | n |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(linhas_params)}

Os parâmetros estão em [`src/parametros.py`](../src/parametros.py). A mediana
ajustada não coincide com a mediana amostral: em `com_bot` fica abaixo
(10,16 h contra 17,56 h) e em `sem_bot` fica acima (3,78 h contra 2,52 h). A
mediana ajustada é `exp(mu)`, isto é, a média geométrica, que não é o mesmo
estimador da mediana amostral; com n = 35 e cauda longa, os dois podem divergir
bastante. O modelo deve ser lido como uma aproximação da distribuição, não como
uma réplica exata das estatísticas amostrais.

## 7. Tamanho do efeito observado

- `delta_mu = mu_com_bot - mu_sem_bot = {fmt(DELTA_MU_OBSERVADO, 4)}`
- razão das médias geométricas: **{fmt(RAZAO_GEOMETRICA_OBSERVADA)}×**
- razão das medianas amostrais: **{fmt(RAZAO_MEDIANAS_AMOSTRAIS)}×**
- d de Cohen na escala log: **{fmt(d)}**

A razão das medianas amostrais é maior que a razão das médias geométricas
porque as medianas de amostras pequenas e muito assimétricas são instáveis.
O valor `delta_mu` é o parâmetro mais adequado para alimentar a simulação.

## 8. Como a simulação vai usar esses parâmetros

- **H₀ (sem efeito):** os dois grupos são gerados com os parâmetros do grupo
  de controle `{GRUPO_CONTROLE}`.
- **H₁ (com efeito):** o grupo tratado usa `mu + delta_mu`, mantendo σ; assim
  a mediana e a média são multiplicadas por `exp(delta_mu)`.
- **Grade sugerida:** `{GRADE_DELTA_MU_SUGERIDA}`.
- O tamanho amostral principal deve ser `n = 35` por grupo, igual ao estudo
  real; a #9 pode variar `n` nas simulações de violação de pressupostos.

## 9. Justificativa

1. O tempo até o merge é positivo e contínuo, com cauda à direita — a
   lognormal é uma escolha natural e é a distribuição exemplificada no
   enunciado.
2. O teste KS não rejeita a lognormal em nenhum dos grupos, embora o ajuste
   não seja perfeito.
3. A mediana é uma medida central robusta para dados assimétricos; σ captura
   a dispersão na escala log.
4. Usamos o grupo `sem_bot` como controle porque a pergunta é se a review de
   bot muda o tempo de merge; em H₀, ambos os grupos vêm dessa distribuição.
5. Mantivemos os outliers no ajuste para que a simulação preserve a
   assimetria observada; a #9/Q3 explora cenários com violações mais severas.

## 10. Limitações

- **Bimodalidade:** os dados têm um bloco de merges rápidos e outro de lentos;
  uma lognormal unimodal é uma aproximação.
- **Cauda simulada:** o q99 ajustado é {fmt(q99_ajustado['com_bot'])} h em
  `com_bot` e {fmt(q99_ajustado['sem_bot'])} h em `sem_bot`, contra
  {fmt(q99_obs['com_bot'])} h e {fmt(q99_obs['sem_bot'])} h observados. A
  simulação pode produzir outliers mais extremos que os reais.
- **Confundidor de tamanho:** a mediana de linhas alteradas é
  {fmt(tamanho_mediana['com_bot'], 0)} em `com_bot` contra
  {fmt(tamanho_mediana['sem_bot'], 0)} em `sem_bot`, e a mediana de reviews
  humanas é {fmt(revisoes_humanas['com_bot'], 0)} contra
  {fmt(revisoes_humanas['sem_bot'], 0)}. Parte da diferença de tempo pode vir
  do tamanho e do processo de revisão, não do bot.
- **Amostra pequena e de um único repositório/bot**, sem atribuição aleatória
  da review. Os resultados não são generalizáveis.
- **Apenas PRs mergeados** entram na amostra (viés de sobrevivência).

## 11. Figuras diagnósticas

![Boxplot do tempo até o merge por grupo](figuras/eda_boxplot.png)

![Q-Q do log do tempo até o merge](figuras/eda_qq_log.png)
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dados", type=Path, default=DADOS_PADRAO)
    parser.add_argument("--saida", type=Path, default=SAIDA_PADRAO)
    parser.add_argument("--figuras", type=Path, default=FIGURAS_PADRAO)
    args = parser.parse_args()

    df = pd.read_csv(args.dados)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    salvar_figuras(df, args.figuras)
    args.saida.write_text(gerar_relatorio(df), encoding="utf-8")
    print(f"Relatório salvo em {args.saida}")
    print(f"Figuras salvas em {args.figuras}")


if __name__ == "__main__":
    main()
