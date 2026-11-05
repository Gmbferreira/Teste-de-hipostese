# Dados reais — tempo até o merge de PRs

Amostra usada no cenário P1 do laboratório: tempo entre a abertura e o merge
de pull requests, comparando PRs **com** e **sem** review de um bot de revisão
de código.

## Origem

| Item | Valor |
|---|---|
| Repositório | [`supabase/supabase`](https://github.com/supabase/supabase) |
| Fonte | GitHub REST API v3 |
| Data da coleta | 2026-11-05 (UTC) |
| Universo | 160 PRs mergeados mais recentes, com `created_at` até 2026-11-05 |
| Janela dos PRs na amostra final | 2026-10-28 a 2026-11-05 (o repositório tem volume alto, então o limite de 160 PRs foi atingido antes dos 12 meses) |
| Script | [`src/coleta.py`](../src/coleta.py) |
| Seed da amostragem | `42` (`src/config.py`) |
| Observações finais | **35 com bot + 35 sem bot = 70** |

## Definição dos grupos

- **`com_bot`**: o PR recebeu pelo menos uma review de um bot de revisão de
  código da lista abaixo.
- **`sem_bot`**: o PR não recebeu nenhuma review desses bots.

Bots considerados como revisão de código:

```
coderabbitai[bot], copilot-pull-request-reviewer[bot], cubic-dev-ai[bot],
greptile-apps[bot], chatgpt-codex-connector[bot], cursor[bot],
qodo-merge-pro[bot], sourcery-ai[bot], gemini-code-assist[bot],
devin-ai-integration[bot], open-swe[bot]
```

Reviews de bots de CI, deploy ou segurança (`github-actions[bot]`,
`supabase-vercel-tedd[bot]`, `github-advanced-security[bot]` etc.) **não**
classificam o PR como `com_bot`; quando presentes, ficam registradas na coluna
`outros_bots`.

Nesta amostra, o único bot de revisão observado foi o **CodeRabbit**
(`coderabbitai[bot]`), presente nos 35 PRs do grupo `com_bot`.

## Filtros aplicados

1. Apenas PRs **mergeados** (`merged_at` preenchido).
2. Apenas PRs **abertos por pessoas** — PRs de autoria de bots (Dependabot,
   Vercel, release bots) foram descartados por serem outra população.
3. Tempo até o merge de pelo menos **5 minutos**, para descartar merge
   automático/ruído operacional.
4. Coleta dos 160 PRs mergeados mais recentes; depois, amostragem aleatória de
   35 por grupo com `numpy.random.default_rng(42)`.

## Como os dados foram coletados

Para cada página de PRs fechados (`GET /repos/supabase/supabase/pulls`), foram
mantidos apenas os mergeados. Para cada PR elegível foi consultado
`GET /repos/supabase/supabase/pulls/{numero}/reviews`, e as reviews foram
classificadas pelo login do autor. O tamanho dos PRs amostrados foi completado
com `GET /repos/supabase/supabase/pulls/{numero}`.

O tempo até o merge é calculado como:

```
tempo_merge_horas = (merged_at - created_at) / 3600
```

Todas as datas estão em UTC.

## Dicionário de colunas

| Coluna | Descrição |
|---|---|
| `repo` | Repositório de origem (`supabase/supabase`) |
| `pr_number` | Número do pull request |
| `grupo` | `com_bot` ou `sem_bot` |
| `tempo_merge_horas` | Horas entre a abertura e o merge |
| `aberto_em` / `mergeado_em` | Timestamps UTC da abertura e do merge |
| `autor` / `tipo_autor` | Login e tipo do autor do PR (todos `User` após o filtro) |
| `revisoes_bot` | Quantidade de bots de revisão distintos que revisaram o PR |
| `revisoes_humanas` | Quantidade de reviews feitas por pessoas |
| `bots_revisores` | Logins dos bots de revisão (separados por `;`) |
| `outros_bots` | Logins de outros bots que deixaram review (CI, deploy, segurança) |
| `adicoes` / `delecoes` | Linhas adicionadas e removidas no PR |
| `arquivos_alterados` | Quantidade de arquivos alterados |

## Estatísticas descritivas

| Grupo | n | Mediana (h) | Média (h) | Desvio-padrão (h) | Mín. (h) | Máx. (h) | Assimetria | Outliers (IQR 1,5) | Mediana de linhas alteradas | Mediana de reviews humanas |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `com_bot` | 35 | 17,56 | 29,53 | 37,88 | 0,23 | 162,93 | 1,87 | 5 | 111 | 2 |
| `sem_bot` | 35 | 2,52 | 14,75 | 23,52 | 0,16 | 102,16 | 2,80 | 2 | 31 | 1 |

As duas distribuições são fortemente assimétricas à direita, com outliers
acima de 100 horas. Isso justifica modelar o tempo de merge com uma
**lognormal** na simulação (issue #4).

## Limitações

- **Estudo observacional**: a atribuição de review de bot não é aleatória.
  O CodeRabbit pode revisar PRs conforme configuração do repositório, tamanho
  ou tipo de mudança.
- **Confundidores**: os PRs `com_bot` são maiores (mediana de 111 linhas contra
  31) e recebem mais reviews humanas (mediana 2 contra 1). Parte da diferença
  no tempo de merge pode vir do tamanho e do processo de revisão, não do bot.
- **Um único repositório e um único bot**: os resultados não são generalizáveis
  para outros projetos nem para outros revisores automáticos.
- **Viés de sobrevivência**: apenas PRs mergeados entram na amostra; PRs
  fechados sem merge ou ainda abertos ficam de fora.
- **Janela curta**: a amostra cobre cerca de 8 dias (2026-10-28 a 2026-11-05),
  sujeita a efeitos sazonais e a mudanças recentes no processo do projeto.
- **Tempo de merge não é tempo de review**: o intervalo inclui espera por
  revisão, CI, resposta do autor e merge.
- **Snapshot**: o CSV é um retrato da coleta em 2026-11-05. Rodar o script
  novamente pode produzir outro conjunto, pois o GitHub muda.
