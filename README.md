# Teste de Hipótese — Tempo até o merge de PRs

Laboratório 04 da disciplina **Laboratório de Experimentação de Software**.
O projeto compara dois testes estatísticos que respondem à mesma pergunta,
usando dados reais e dados simulados.

## Cenário

**Pergunta:** pull requests revisados por um bot levam menos tempo até o merge
do que pull requests sem revisão de bot?

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
├── dashboard/        # dashboard Streamlit
├── data/             # amostra de dados reais (CSV) e sua documentação
├── docs/             # cenário, expectativa, análise exploratória e interpretações
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

O dashboard abre em <http://localhost:8501>.

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

- [x] #2 — Estrutura do repositório, ambiente e README
- [x] #6 — Esqueleto do dashboard (7 seções)
- [ ] #8 — Cenário: pergunta, H₀ e H₁
- [ ] #3 — Coleta dos dados reais
- [ ] #4 — Análise exploratória e parâmetros da simulação
- [ ] #9 — Gerador de dados simulados
- [ ] #10 — Expectativa registrada antes de simular
- [ ] #11 — Aplicação dos dois testes e interpretação
- [ ] #5 — Gráfico G1
- [ ] #12 — Gráfico G2
- [ ] #7 — Integração do G1 no dashboard
- [ ] #13 — Integração do G2 no dashboard
