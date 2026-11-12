"""Conclusão do dashboard: expectativa × resultados e recomendação (issue #23).

Cada previsão registrada em docs/expectativa.md antes de simular (issue #10)
vira uma regra que olha os resultados e decide se ela se confirmou. Assim a
coluna "Resultado" da seção 7 sai das simulações, e não de uma avaliação feita
depois de ver os números.

A conclusão usa sempre α = 5%, que é o α da expectativa.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.dados_reais import DADOS, ResultadoDadosReais
from src.formatacao import numero, p_valor, porcentagem
from src.monte_carlo import margem_esperada
from src.parametros import DELTA_MU_OBSERVADO
from src.situacoes import SITUACOES_Q3
from src.textos import EMPATE_PODER, efeito_mais_perto_do_observado

CONFIRMADO = "✓ Confirmado"
EM_PARTE = "◐ Em parte"
NAO_CONFIRMADO = "✗ Não confirmado"

# "Perto de 5%" como definido na expectativa: a margem de ±0,4 p.p. das 10.000 repetições.
PERTO_DE_5 = (0.046, 0.054)
# Faixas e limites que a expectativa registrou.
WELCH_REALISTA_ESPERADO = (0.03, 0.045)
PODER_MW_ESPERADO = (0.50, 0.60)
PODER_WELCH_ESPERADO = (0.20, 0.35)
QUEDA_RELATIVA_BASTANTE = 0.25  # "o Welch perde bastante poder": ao menos 25% a menos
QUASE_NAO_MUDA = 0.02  # "o Mann-Whitney quase não muda": no máximo 2 p.p. de diferença
ALGUNS_PONTOS = 0.05  # "só alguns pontos percentuais": no máximo 5 p.p.

# Situações que estavam na expectativa (a reamostragem entrou depois).
CHAVES_ESPERADAS = ("realista", *(s.chave for s in SITUACOES_Q3))

# Pequena folga para comparar taxas que caem exatamente na borda de uma faixa.
_EPS = 1e-9


@dataclass(frozen=True)
class Previsao:
    """Uma linha da tabela esperado × encontrado."""

    grandeza: str  # "Erro tipo I" ou "Poder"
    esperado: str
    encontrado: str
    resultado: str


class Resultados:
    """Acesso às taxas da tabela de dados_g4 (α = 5%) e ao poder por tamanho de amostra."""

    def __init__(self, poder: pd.DataFrame, poder_por_n: pd.DataFrame) -> None:
        self.poder = poder
        self.alpha = float(poder["alpha"].iloc[0])
        self.margem = margem_esperada(self.alpha, int(poder["repeticoes"].iloc[0]))
        self.delta = efeito_mais_perto_do_observado(poder)
        self.poder_por_n = poder_por_n

    def taxa(self, chave: str, teste: str, delta: float = 0.0) -> float:
        linha = self.poder[
            (self.poder["situacao"] == chave)
            & (self.poder["teste"] == teste)
            & np.isclose(self.poder["delta_mu"], delta)
        ]
        return float(linha["taxa"].iloc[0])

    def curva(self, chave: str, teste: str) -> pd.Series:
        do_caso = self.poder[(self.poder["situacao"] == chave) & (self.poder["teste"] == teste)]
        return do_caso.set_index("delta_mu")["taxa"].sort_index()

    def poder_no_observado(self, teste: str, modelo: str = "lognormal") -> float:
        """Poder no efeito observado (δ = 0,99) com 35 PRs por grupo."""
        return _poder_n35(self.poder_por_n, modelo, teste)


def _dentro(taxa: float, faixa: tuple[float, float]) -> bool:
    return faixa[0] - _EPS <= taxa <= faixa[1] + _EPS


def _pct(valor: float) -> str:
    """Porcentagem com uma casa, sem o ",0" dos valores inteiros (3% e 4,5%)."""
    return porcentagem(valor, 1).replace(",0%", "%")


def _faixa(faixa: tuple[float, float], conector: str = "a") -> str:
    return f"{_pct(faixa[0])} {conector} {_pct(faixa[1])}"


def _pp(valor: float) -> str:
    return f"{numero(100 * valor, 1)} p.p."


def _contagem(acertos: int, total: int) -> str:
    if acertos == total:
        return CONFIRMADO
    return EM_PARTE if acertos > 0 else NAO_CONFIRMADO


# ---------------------------------------------------------------------------
# Erro tipo I
# ---------------------------------------------------------------------------
def _mw_perto_de_5(r: Resultados) -> Previsao:
    taxas = [r.taxa(c, "mann_whitney") for c in CHAVES_ESPERADAS]
    perto = sum(_dentro(t, PERTO_DE_5) for t in taxas)
    return Previsao(
        "Erro tipo I",
        f"Mann-Whitney perto de 5% ({_faixa(PERTO_DE_5)}) em todas as situações",
        f"de {porcentagem(min(taxas), 1)} a {porcentagem(max(taxas), 1)}",
        CONFIRMADO if perto == len(taxas) else (EM_PARTE if perto >= len(taxas) / 2 else NAO_CONFIRMADO),
    )


def _welch_conservador_na_realista(r: Resultados) -> Previsao:
    taxa = r.taxa("realista", "welch")
    if _dentro(taxa, WELCH_REALISTA_ESPERADO):
        resultado, nota = CONFIRMADO, ""
    elif taxa < r.alpha - r.margem:
        resultado = EM_PARTE
        nota = (
            ": mais conservador do que prevíamos"
            if taxa < WELCH_REALISTA_ESPERADO[0]
            else ": conservador, mas menos do que prevíamos"
        )
    else:
        resultado, nota = NAO_CONFIRMADO, ": não ficou abaixo de 5%"
    return Previsao(
        "Erro tipo I",
        f"Welch conservador na situação realista, entre {_faixa(WELCH_REALISTA_ESPERADO, 'e')}",
        f"{porcentagem(taxa, 1)}{nota}",
        resultado,
    )


def _welch_mais_conservador(r: Resultados, chave: str, nome: str) -> Previsao:
    taxa, realista = r.taxa(chave, "welch"), r.taxa("realista", "welch")
    mais = taxa < realista
    return Previsao(
        "Erro tipo I",
        f"Welch ainda mais conservador {nome}",
        f"{porcentagem(taxa, 1)}, {'mais' if mais else 'menos'} conservador que na realista "
        f"({porcentagem(realista, 1)})",
        CONFIRMADO if mais else NAO_CONFIRMADO,
    )


def _welch_liberal_desbalanceado(r: Resultados) -> Previsao:
    taxa = r.taxa("desbalanceado", "welch")
    liberal = taxa > r.alpha + r.margem
    return Previsao(
        "Erro tipo I",
        "Welch liberal (acima de 5%) com grupos desbalanceados",
        f"{porcentagem(taxa, 1)}, {numero(taxa / r.alpha, 1)} vezes α",
        CONFIRMADO if liberal else NAO_CONFIRMADO,
    )


def _escala_log_perto_de_5(r: Resultados) -> Previsao:
    taxas = [r.taxa("escala_log", t) for t in ("welch", "mann_whitney")]
    perto = sum(_dentro(t, PERTO_DE_5) for t in taxas)
    return Previsao(
        "Erro tipo I",
        "Os dois testes perto de 5% na escala log",
        f"Welch {porcentagem(taxas[0], 1)} e Mann-Whitney {porcentagem(taxas[1], 1)}",
        _contagem(perto, 2),
    )


# ---------------------------------------------------------------------------
# Poder
# ---------------------------------------------------------------------------
def _mw_mais_poder_na_realista(r: Resultados) -> Previsao:
    mw, welch = r.curva("realista", "mann_whitney"), r.curva("realista", "welch")
    com_efeito = mw.index > 0
    sempre = bool((mw[com_efeito] > welch[com_efeito]).all())
    vantagem = mw.loc[r.delta] - welch.loc[r.delta]
    return Previsao(
        "Poder",
        "Mann-Whitney com mais poder que o Welch em todo efeito na situação realista, com folga",
        (
            f"{'sim, em todos os efeitos' if sempre else 'não em todos os efeitos'}; "
            f"{_pp(vantagem)} a mais com δ = {numero(r.delta)}"
        ),
        CONFIRMADO if sempre else (EM_PARTE if vantagem > 0 else NAO_CONFIRMADO),
    )


def _poder_no_observado(r: Resultados, teste: str, nome: str, faixa: tuple[float, float]) -> Previsao:
    taxa = r.poder_no_observado(teste)
    return Previsao(
        "Poder",
        f"No efeito observado (δ = {numero(DELTA_MU_OBSERVADO)}, 35 PRs por grupo): {nome} "
        f"com {_faixa(faixa)} de poder",
        porcentagem(taxa, 1),
        CONFIRMADO if _dentro(taxa, faixa) else NAO_CONFIRMADO,
    )


def _pequenas_e_desbalanceado(r: Resultados) -> Previsao:
    """Os dois testes perdem poder em relação à realista e o Mann-Whitney continua na frente."""
    partes, acertos = [], 0
    for chave, rotulo in (("amostras_pequenas", "amostras pequenas"), ("desbalanceado", "desbalanceado")):
        mw, welch = r.taxa(chave, "mann_whitney", r.delta), r.taxa(chave, "welch", r.delta)
        caiu = mw < r.taxa("realista", "mann_whitney", r.delta) and welch < r.taxa(
            "realista", "welch", r.delta
        )
        acertos += caiu and mw > welch
        partes.append(f"{rotulo}: {porcentagem(mw, 1)} contra {porcentagem(welch, 1)}")
    return Previsao(
        "Poder",
        "Amostras pequenas e grupos desbalanceados: os dois perdem poder e o Mann-Whitney "
        "continua na frente",
        f"com δ = {numero(r.delta)}, Mann-Whitney contra Welch, " + "; ".join(partes),
        _contagem(acertos, 2),
    )


def _outliers(r: Resultados) -> Previsao:
    welch_real, welch_out = (r.taxa(c, "welch", r.delta) for c in ("realista", "outliers"))
    mw_real, mw_out = (r.taxa(c, "mann_whitney", r.delta) for c in ("realista", "outliers"))
    welch_perde = welch_out <= (1 - QUEDA_RELATIVA_BASTANTE) * welch_real
    mw_estavel = abs(mw_out - mw_real) <= QUASE_NAO_MUDA + _EPS
    return Previsao(
        "Poder",
        "Outliers: o Welch perde bastante poder e o Mann-Whitney quase não muda",
        (
            f"com δ = {numero(r.delta)}, Welch de {porcentagem(welch_real, 1)} para "
            f"{porcentagem(welch_out, 1)} e Mann-Whitney de {porcentagem(mw_real, 1)} para "
            f"{porcentagem(mw_out, 1)}"
        ),
        _contagem(welch_perde + mw_estavel, 2),
    )


def _escala_log_poder(r: Resultados) -> Previsao:
    welch, mw = r.curva("escala_log", "welch"), r.curva("escala_log", "mann_whitney")
    com_efeito = welch.index > 0
    diferenca = welch[com_efeito] - mw[com_efeito]
    welch_um_pouco_na_frente = bool(
        (diferenca > -EMPATE_PODER).all() and 0 < diferenca.max() <= ALGUNS_PONTOS + _EPS
    )
    mw_igual = bool(np.allclose(mw, r.curva("realista", "mann_whitney")))
    return Previsao(
        "Poder",
        "Escala log: o Welch um pouco na frente e o Mann-Whitney com o mesmo poder da realista",
        (
            f"Welch até {_pp(diferenca.max())} à frente; Mann-Whitney "
            f"{'idêntico ao da realista' if mw_igual else 'diferente do da realista'}"
        ),
        _contagem(welch_um_pouco_na_frente + mw_igual, 2),
    )


def previsoes(poder: pd.DataFrame, poder_por_n: pd.DataFrame) -> list[Previsao]:
    """As previsões de docs/expectativa.md, na ordem do arquivo, com o resultado de cada uma."""
    r = Resultados(poder, poder_por_n)
    return [
        _mw_perto_de_5(r),
        _welch_conservador_na_realista(r),
        _welch_mais_conservador(r, "amostras_pequenas", "com amostras pequenas"),
        _welch_mais_conservador(r, "outliers", "com outliers"),
        _welch_liberal_desbalanceado(r),
        _escala_log_perto_de_5(r),
        _mw_mais_poder_na_realista(r),
        _poder_no_observado(r, "mann_whitney", "Mann-Whitney", PODER_MW_ESPERADO),
        _poder_no_observado(r, "welch", "Welch", PODER_WELCH_ESPERADO),
        _pequenas_e_desbalanceado(r),
        _outliers(r),
        _escala_log_poder(r),
    ]


def tabela_esperado_encontrado(poder: pd.DataFrame, poder_por_n: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "": p.grandeza,
                "O que esperávamos": p.esperado,
                "O que encontramos": p.encontrado,
                "Resultado": p.resultado,
            }
            for p in previsoes(poder, poder_por_n)
        ]
    )


# ---------------------------------------------------------------------------
# Textos
# ---------------------------------------------------------------------------
def texto_balanco(poder: pd.DataFrame, poder_por_n: pd.DataFrame) -> str:
    """Abertura da seção 7: quantas previsões se confirmaram."""
    resultados = [p.resultado for p in previsoes(poder, poder_por_n)]
    contagem = {r: resultados.count(r) for r in (CONFIRMADO, EM_PARTE, NAO_CONFIRMADO)}
    return (
        "Antes de simular, registramos em `docs/expectativa.md` o que esperávamos de cada "
        f"teste (issue #10). Das {len(resultados)} previsões, {contagem[CONFIRMADO]} se "
        f"confirmaram, {contagem[EM_PARTE]} em parte e {contagem[NAO_CONFIRMADO]} não. Acertamos "
        "a direção de quase tudo: o Mann-Whitney perto de 5% e com mais poder, e o Welch "
        "conservador com a lognormal e liberal com grupos desbalanceados. Erramos no tamanho: "
        "o Welch ficou mais conservador e com menos poder do que prevíamos, e os outliers "
        "deixaram o Welch menos conservador, e não mais, e também tiraram poder do "
        "Mann-Whitney."
    )


def _cruzamento(r: Resultados, chave: str) -> float | None:
    """Primeiro δ a partir do qual o Welch fica na frente do Mann-Whitney até o fim da grade."""
    diferenca = r.curva(chave, "welch") - r.curva(chave, "mann_whitney")
    diferenca = diferenca[diferenca.index > 0]
    for delta in diferenca.index:
        if (diferenca[diferenca.index >= delta] > EMPATE_PODER).all():
            return float(delta)
    return None


def texto_recomendacao(
    poder: pd.DataFrame, poder_por_n: pd.DataFrame, real: ResultadoDadosReais
) -> str:
    """Qual teste usar no cenário e quando a escolha mudaria."""
    r = Resultados(poder, poder_por_n)
    mw_tipo_i = [r.taxa(c, "mann_whitney") for c in CHAVES_ESPERADAS]
    log = r.curva("escala_log", "welch") - r.curva("escala_log", "mann_whitney")
    cruzamento = _cruzamento(r, "reamostragem")
    w, m = real.welch, real.mann_whitney

    recomendacao = (
        "**Recomendação.** Para comparar o tempo até o merge em horas, recomendamos o "
        f"**Mann-Whitney**. Ele ficou entre {porcentagem(min(mw_tipo_i), 1)} e "
        f"{porcentagem(max(mw_tipo_i), 1)} de erro tipo I em todas as situações, inclusive com "
        "grupos desbalanceados, em que o Welch chegou a "
        f"{porcentagem(r.taxa('desbalanceado', 'welch'), 1)}; esse é o erro mais grave no "
        "nosso cenário, porque levaria a desligar o bot sem motivo. Ele também teve mais poder "
        f"com a lognormal ({porcentagem(r.poder_no_observado('mann_whitney'), 0)} contra "
        f"{porcentagem(r.poder_no_observado('welch'), 0)} no efeito observado) e, nos dados "
        f"reais, {'foi o único a rejeitar' if m.rejeita_h0 and not w.rejeita_h0 else 'chegou à mesma conclusão sobre'} "
        f"H₀ (p = {p_valor(m.p_valor)} contra {p_valor(w.p_valor)} do Welch)."
    )
    mudaria = (
        "**Quando a escolha mudaria.** A escolha mudaria se o tempo fosse analisado na escala "
        "log, em que o Welch fica perto de 5%, tem poder igual ou um pouco maior (até "
        f"{_pp(log[log.index > 0].max())} a mais) e ainda dá o efeito como razão (PRs com bot "
        f"{numero(real.razao_geometrica, 1)} vezes mais lentos)."
    )
    if cruzamento is not None:
        mudaria += (
            " Também mudaria se a cauda real fosse como a da amostra e o efeito procurado fosse "
            "grande: com os tempos reamostrados, o Welch passa na frente a partir de "
            f"δ = {numero(cruzamento)}."
        )
    mudaria += (
        " E, se a pergunta fosse sobre a média de horas (por exemplo, o custo total de "
        "espera), o Welch responderia a ela diretamente; o Mann-Whitney fala da tendência de "
        "um PR demorar mais que outro."
    )
    return recomendacao + "\n\n" + mudaria


def texto_limitacao(poder_por_n: pd.DataFrame) -> str:
    """A principal limitação do estudo."""
    lognormal = {t: _poder_n35(poder_por_n, "lognormal", t) for t in ("welch", "mann_whitney")}
    cauda_real = {t: _poder_n35(poder_por_n, "reamostragem", t) for t in ("welch", "mann_whitney")}
    dados = pd.read_csv(DADOS)
    datas = pd.to_datetime(dados["mergeado_em"])
    dias = round((datas.max() - datas.min()).total_seconds() / 86_400)
    repositorios = dados["repo"].nunique()
    return (
        "**Principal limitação.** As conclusões sobre poder dependem do modelo dos dados. A "
        "lognormal ajustada gera PRs bem mais lentos que os reais: no efeito observado, com 35 "
        f"PRs por grupo, ela dá {porcentagem(lognormal['welch'], 0)} de poder ao Welch e "
        f"{porcentagem(lognormal['mann_whitney'], 0)} ao Mann-Whitney, mas com a cauda da "
        f"própria amostra os dois quase empatam ({porcentagem(cauda_real['welch'], 0)} e "
        f"{porcentagem(cauda_real['mann_whitney'], 0)}). Além disso, o estudo é observacional, "
        f"com {'um repositório' if repositorios == 1 else f'{repositorios} repositórios'}, um "
        f"bot e {dias} dias de PRs, e os PRs com bot também são maiores; por isso a diferença "
        "nos dados reais não pode ser atribuída só ao bot."
    )


def _poder_n35(tabela: pd.DataFrame, modelo: str, teste: str) -> float:
    linha = tabela[
        (tabela["modelo"] == modelo) & (tabela["n_por_grupo"] == 35) & (tabela["teste"] == teste)
    ]
    return float(linha["taxa"].iloc[0])
