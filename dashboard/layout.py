"""Visual do dashboard para a apresentação (issue #26).

Junta o CSS e os blocos de layout (abertura, números do estudo, navegação e
cartão de cada seção). O conteúdo das seções continua no app.py; aqui fica só
a forma, para não misturar visual com análise.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from html import escape

import streamlit as st

from src.estilo import CORES_TESTE, ROTULOS_TESTE

CSS = """
<style>
:root {
  --tinta: #0f172a;
  --tinta-2: #334155;
  --tinta-3: #64748b;
  --borda: #e3e7ee;
  --cartao: #ffffff;
  --destaque: #0f766e;
  --destaque-fundo: #e6f6f3;
}

/* Largura confortável para ler e projetar. */
[data-testid="stMainBlockContainer"] {
  max-width: 1240px;
  padding-top: 1.25rem;
  padding-bottom: 4rem;
}

/* Cada seção é um cartão branco. */
[class*="st-key-secao-"] {
  background: var(--cartao);
  border: 1px solid var(--borda);
  border-radius: 18px;
  padding: 1.7rem 2rem 1.9rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 10px 28px rgba(15, 23, 42, 0.06);
  margin-top: 1.4rem;
}
[class*="st-key-secao-"] h2 {
  scroll-margin-top: 5rem;
  padding-top: 0;
  padding-bottom: 0.15rem;
  letter-spacing: -0.01em;
}
.secao-perguntas {
  color: var(--destaque);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: -0.35rem;
}
.secao-resumo {
  color: var(--tinta-3);
  font-size: 1.02rem;
  margin: 0 0 0.6rem;
  padding-bottom: 0.9rem;
  border-bottom: 1px solid var(--borda);
}

/* Abertura. */
.abertura {
  background: linear-gradient(120deg, #0f172a 0%, #12324a 55%, #0f766e 100%);
  color: #f8fafc;
  border-radius: 22px;
  padding: 2.3rem 2.5rem 2.1rem;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.18);
}
.abertura-chapeu {
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #99f6e4;
}
.abertura-titulo {
  font-size: 2.6rem;
  font-weight: 800;
  line-height: 1.12;
  text-wrap: balance;
  letter-spacing: -0.02em;
  margin: 0.45rem 0 0.7rem;
  color: #ffffff;
}
.abertura-texto {
  font-size: 1.08rem;
  line-height: 1.55;
  color: #dbe4ee;
  max-width: 54rem;
  margin: 0 0 1.1rem;
}
@media (max-width: 900px) {
  .abertura { padding: 1.6rem 1.5rem; }
  .abertura-titulo { font-size: 2rem; }
  [class*="st-key-secao-"] { padding: 1.3rem 1.2rem 1.5rem; }
}
.abertura-etiquetas, .abertura-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.abertura-links { margin-top: 1.1rem; }
.etiqueta {
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #f1f5f9;
  border-radius: 999px;
  padding: 0.28rem 0.8rem;
  font-size: 0.86rem;
  font-weight: 500;
}
a.botao, a.botao:visited {
  background: #ffffff;
  color: var(--tinta) !important;
  border-radius: 10px;
  padding: 0.5rem 1rem;
  font-size: 0.92rem;
  font-weight: 600;
  text-decoration: none;
}
a.botao:hover { background: #ccfbf1; }
.botao-desligado {
  border: 1px dashed rgba(255, 255, 255, 0.45);
  color: #cbd5e1;
  border-radius: 10px;
  padding: 0.5rem 1rem;
  font-size: 0.92rem;
}

/* Números do estudo. */
.numeros-titulo {
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--tinta-3);
  margin: 1.5rem 0 0.6rem;
}
/* Dois cartões de contexto em cima e três de resultado embaixo. */
.numeros {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 0.9rem;
}
.numero.contexto { grid-column: span 3; }
.numero.resultado { grid-column: span 2; }
@media (max-width: 900px) {
  .numeros { grid-template-columns: 1fr; }
  .numero.contexto, .numero.resultado { grid-column: auto; }
}
.numero {
  background: var(--cartao);
  border: 1px solid var(--borda);
  border-radius: 16px;
  padding: 1rem 1.15rem 1.05rem;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.numero-rotulo {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--tinta-3);
}
.numero-valor {
  font-size: 2.05rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--tinta);
  margin: 0.25rem 0 0.15rem;
}
.numero-testes {
  list-style: none;
  padding: 0;
  margin: 0.55rem 0 0.35rem;
}
.numero-testes li {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  margin: 0.22rem 0;
  font-size: 0.95rem;
  color: var(--tinta-2);
}
.numero-testes span { white-space: nowrap; }
.numero-testes .valor {
  margin-left: auto;
  font-weight: 800;
  font-size: 1.3rem;
  color: var(--tinta);
}
.ponto {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 50%;
  display: inline-block;
  flex: none;
}
.numero-nota {
  font-size: 0.86rem;
  color: var(--tinta-3);
  line-height: 1.4;
}

/* Navegação lateral. */
.nav-titulo {
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #94a3b8;
  margin: 0.4rem 0 0.5rem;
}
a.nav-item, a.nav-item:visited {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  padding: 0.5rem 0.6rem;
  border-radius: 10px;
  color: #e2e8f0 !important;
  text-decoration: none;
}
a.nav-item:hover { background: #1e293b; }
.nav-numero {
  width: 1.7rem;
  height: 1.7rem;
  border-radius: 8px;
  background: #134e4a;
  color: #99f6e4;
  font-weight: 800;
  font-size: 0.9rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
}
.nav-nome { font-weight: 600; font-size: 0.95rem; line-height: 1.2; }
.nav-perguntas { display: block; font-size: 0.75rem; color: #94a3b8; font-weight: 500; }
.nav-rodape {
  font-size: 0.8rem;
  color: #94a3b8;
  line-height: 1.5;
  margin-top: 1rem;
}

/* Rodapé da página. */
.rodape {
  text-align: center;
  color: var(--tinta-3);
  font-size: 0.85rem;
  margin-top: 2.2rem;
}
</style>
"""


@dataclass(frozen=True)
class Secao:
    numero: int
    titulo: str
    resumo: str
    perguntas: tuple[int, ...]


@dataclass(frozen=True)
class Numero:
    """Um cartão dos números do estudo: um valor só ou um valor por teste."""

    rotulo: str
    nota: str
    valor: str | None = None
    por_teste: tuple[tuple[str, str], ...] = ()  # (chave do teste, valor)


def _juntar(itens: list[str]) -> str:
    if len(itens) <= 1:
        return "".join(itens)
    return ", ".join(itens[:-1]) + " e " + itens[-1]


def aplicar_estilo() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def abertura(
    chapeu: str,
    titulo: str,
    texto: str,
    etiquetas: list[str],
    links: list[tuple[str, str | None]],
) -> None:
    """Bloco de abertura com a pergunta, o contexto e os links do topo."""
    html_etiquetas = "".join(f'<span class="etiqueta">{escape(e)}</span>' for e in etiquetas)
    html_links = "".join(
        f'<a class="botao" href="{escape(url)}" target="_blank">{escape(nome)}</a>'
        if url
        else f'<span class="botao-desligado">{escape(nome)}: em breve</span>'
        for nome, url in links
    )
    st.markdown(
        f"""
<div class="abertura">
  <div class="abertura-chapeu">{escape(chapeu)}</div>
  <div class="abertura-titulo" role="heading" aria-level="1">{escape(titulo)}</div>
  <p class="abertura-texto">{escape(texto)}</p>
  <div class="abertura-etiquetas">{html_etiquetas}</div>
  <div class="abertura-links">{html_links}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def numeros_do_estudo(titulo: str, numeros: list[Numero]) -> None:
    """Cartões com os principais números, lado a lado."""
    cartoes = []
    for n in numeros:
        if n.por_teste:
            linhas = "".join(
                f'<li><span class="ponto" style="background:{CORES_TESTE[teste]}"></span>'
                f"<span>{escape(ROTULOS_TESTE[teste])}</span>"
                f'<span class="valor">{escape(valor)}</span></li>'
                for teste, valor in n.por_teste
            )
            corpo = f'<ul class="numero-testes">{linhas}</ul>'
        else:
            corpo = f'<div class="numero-valor">{escape(n.valor or "")}</div>'
        tipo = "resultado" if n.por_teste else "contexto"
        cartoes.append(
            f'<div class="numero {tipo}"><div class="numero-rotulo">{escape(n.rotulo)}</div>'
            f'{corpo}<div class="numero-nota">{escape(n.nota)}</div></div>'
        )
    st.markdown(
        f'<div class="numeros-titulo">{escape(titulo)}</div>'
        f'<div class="numeros">{"".join(cartoes)}</div>',
        unsafe_allow_html=True,
    )


def _perguntas_em_texto(perguntas: tuple[int, ...]) -> str:
    rotulo = "Pergunta" if len(perguntas) == 1 else "Perguntas"
    return f"{rotulo} {_juntar([str(p) for p in perguntas])} da apresentação"


def navegacao(secoes: list[Secao], rodape: str) -> None:
    """Índice da barra lateral, com as perguntas que cada seção responde."""
    itens = "".join(
        f'<a class="nav-item" href="#secao-{s.numero}">'
        f'<span class="nav-numero">{s.numero}</span>'
        f'<span><span class="nav-nome">{escape(s.titulo)}</span>'
        f'<span class="nav-perguntas">{escape(_perguntas_em_texto(s.perguntas))}</span>'
        "</span></a>"
        for s in secoes
    )
    st.sidebar.markdown(
        f'<div class="nav-titulo">Seções</div>{itens}'
        f'<div class="nav-rodape">{escape(rodape)}</div>',
        unsafe_allow_html=True,
    )


@contextmanager
def secao(s: Secao) -> Iterator[None]:
    """Cartão de uma seção: perguntas que ela responde, título e resumo."""
    with st.container(border=False, key=f"secao-{s.numero}"):
        st.markdown(
            f'<div class="secao-perguntas">{escape(_perguntas_em_texto(s.perguntas))}</div>',
            unsafe_allow_html=True,
        )
        st.header(f"{s.numero}. {s.titulo}", anchor=f"secao-{s.numero}")
        st.markdown(f'<p class="secao-resumo">{escape(s.resumo)}</p>', unsafe_allow_html=True)
        yield


def rodape(texto: str) -> None:
    st.markdown(f'<div class="rodape">{escape(texto)}</div>', unsafe_allow_html=True)
