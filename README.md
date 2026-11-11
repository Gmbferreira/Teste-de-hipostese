# Teste de Hipótese — Tempo até o merge de PRs

Laboratório 04 da disciplina **Laboratório de Experimentação de Software**.
O projeto compara dois testes estatísticos que respondem à mesma pergunta,
usando dados reais e dados simulados.

## Cenário

**Pergunta:** a revisão feita por um bot muda o tempo que um pull request leva
da abertura até o merge?

**Par de testes:** teste t de Welch × teste de Mann-Whitney (par P1 do enunciado).

**Grupos comparados:**

- PRs com revisão de bot
- PRs sem revisão de bot

A formulação formal de H₀ e H₁, o tipo de teste (unicaudal ou bicaudal) e a
definição dos erros tipo I e II estão em [`docs/cenario.md`](docs/cenario.md)
(issue #8).

## Estrutura do repositório

```
.
├── .streamlit/       # tema do dashboard (cores, fonte e tamanho para projetor)
├── dashboard/        # dashboard Streamlit (app.py e o visual em layout.py)
├── data/             # amostra de dados reais (CSV) e sua documentação
├── docs/             # cenário, expectativa, análise exploratória e interpretações
├── resultados/       # taxas de rejeição das simulações de Q1–Q3 (CSV)
├── src/              # código reutilizável (configuração, simulação, testes, gráficos)
├── requirements.txt
└── README.md
```

## Requisitos

- Python 3.11 ou superior (testado com 3.12)
- Dependências em `requirements.txt`

## Instalação

Com `pip`:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Com [`uv`](https://docs.astral.sh/uv/):

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
```

## Como executar

Um único comando, a partir da raiz do repositório:

```bash
streamlit run dashboard/app.py
```

O dashboard abre em <http://localhost:8501>. Rode da raiz mesmo, porque é de
lá que o Streamlit lê o tema em `.streamlit/config.toml`. O topo traz a pergunta,
os links e os principais números do estudo, e a barra lateral leva a cada seção
e mostra quais perguntas da apresentação ela responde.

Para regenerar a análise exploratória e os parâmetros da simulação:

```bash
python -m src.analise_exploratoria
```

O comando atualiza [`docs/analise_exploratoria.md`](docs/analise_exploratoria.md)
e as figuras em `docs/figuras/`.

Para regenerar o exemplo da seção 3 (os dois testes aplicados a um conjunto
simulado) e o gráfico G2:

```bash
python -m src.exemplo
python -m src.grafico_g2
```

Eles atualizam [`docs/exemplo_testes.md`](docs/exemplo_testes.md) e
`docs/figuras/g2_estatistica_sob_h0.png`. O dashboard não lê esses arquivos:
ele refaz o exemplo e o G2 na hora, com a mesma semente, então os números são
os mesmos.

Para regenerar o gráfico G1 (dados reais × dados simulados):

```bash
python -m src.grafico_g1
```

Ele atualiza `docs/figuras/g1_dados_reais_simulados.png`. Os dados simulados
usam o efeito observado, 35 PRs por grupo e a mesma semente do exemplo.

Para regenerar as simulações de erro tipo I, de poder e de Q3 (10.000
repetições por ponto) e o gráfico G3:

```bash
python -m src.monte_carlo
python -m src.situacoes
python -m src.grafico_g3
```

O primeiro grava a Q1 em `resultados/q1_erro_tipo_i.csv` e a Q2 (poder na
situação realista, com δ de 0 a 2) em `resultados/q2_poder.csv`. O segundo grava o
erro tipo I e o poder das situações de Q3 em `resultados/` e a descrição delas
em [`docs/situacoes_q3.md`](docs/situacoes_q3.md). O dashboard também roda essas
simulações sozinho na primeira vez que abre (leva alguns segundos) e guarda o
resultado em cache.

Além das quatro situações de Q3 registradas na expectativa, o segundo comando
roda uma análise de sensibilidade incluída depois: a reamostragem dos tempos
reais. A lognormal ajustada gera PRs bem mais lentos que os da amostra, e essa
situação mostra o que muda quando a cauda é a dos dados coletados.

Para regenerar o gráfico G4 (curvas de poder dos dois testes, um painel por
situação):

```bash
python -m src.grafico_g4
```

Ele atualiza `docs/figuras/g4_curvas_de_poder.png` com os mesmos resultados de
`resultados/q2_poder.csv` e `resultados/q3_poder.csv`.

Para regenerar o poder de cada teste no efeito observado, por tamanho de grupo
(usado na discussão da seção 6):

```bash
python -m src.dados_reais
```

Ele grava `resultados/poder_tamanho_amostra.csv` e leva perto de um minuto, por
causa dos grupos de até 400 PRs. O dashboard lê esse arquivo.

O rascunho da divisão das perguntas da apresentação está em
[`docs/apresentacao.md`](docs/apresentacao.md).

## Testes

```bash
pytest -q
```

## Reprodutibilidade

Toda a aleatoriedade do projeto usa a semente fixa definida em
[`src/config.py`](src/config.py):

```python
SEED = 42
```

Os módulos devem criar o gerador com `make_rng()` em vez de chamar
`numpy.random` diretamente, para que os resultados possam ser reproduzidos.

## Links

- Repositório: <https://github.com/Gmbferreira/Teste-de-hipostese>
- GitHub Projects: <https://github.com/users/Gmbferreira/projects/4>
- Dashboard publicado: _a preencher_

## Andamento

Sprint 1:

- [x] #2 — Estrutura do repositório, ambiente e README
- [x] #6 — Esqueleto do dashboard (7 seções)
- [x] #8 — Cenário: pergunta, H₀ e H₁
- [x] #3 — Coleta dos dados reais
- [x] #4 — Análise exploratória e parâmetros da simulação
- [x] #9 — Gerador de dados simulados
- [x] #10 — Expectativa registrada antes de simular
- [x] #11 — Aplicação dos dois testes e interpretação
- [x] #5 — Gráfico G1
- [x] #12 — Gráfico G2
- [x] #7 — Integração do G1 no dashboard
- [x] #13 — Integração do G2 no dashboard

Sprint 2:

- [x] #14 — Erro tipo I com H₀ verdadeira (Q1)
- [x] #15 — Poder dos testes (Q2)
- [x] #16 — Situações que violam os pressupostos (Q3)
- [x] #18 — Gráfico G3
- [x] #19 — Integração do G3 no dashboard
- [x] #20 — Gráfico G4
- [ ] #21 — Integração do G4 no dashboard

Entrega final:

- [x] #22 — Testes nos dados reais (seção 6)
- [ ] #23 — Conclusão (seção 7)
- [ ] #24 — Publicação do dashboard
- [ ] #25 — Apresentação oral
- [x] #26 — Visual do dashboard para a apresentação
