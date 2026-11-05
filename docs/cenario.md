# Cenário

Par de testes escolhido: **t de Welch × Mann-Whitney** (par P1 do enunciado).

## Pergunta

A revisão feita por um bot muda o tempo que um pull request leva da abertura
até o merge?

## Hipóteses

Em palavras simples:

- **H₀:** a revisão do bot não muda o tempo até o merge. PRs com e sem bot têm
  a mesma distribuição de tempo.
- **H₁:** a revisão do bot muda o tempo até o merge. Os PRs de um dos grupos
  tendem a demorar mais que os do outro.

De forma mais formal, sejam $T_{bot}$ e $T_{sem}$ o tempo até o merge (em
horas) de um PR com e sem revisão de bot, com distribuições $F_{bot}$ e
$F_{sem}$:

| | t de Welch | Mann-Whitney |
|---|---|---|
| **H₀** | $E[T_{bot}] = E[T_{sem}]$ | $P(T_{bot} > T_{sem}) = 1/2$ |
| **H₁** | $E[T_{bot}] \neq E[T_{sem}]$ | $P(T_{bot} > T_{sem}) \neq 1/2$ |

Aqui $E[T]$ é o tempo médio da população. O Welch olha para as médias; o
Mann-Whitney olha para a chance de um PR com bot, sorteado ao acaso, demorar
mais que um PR sem bot. Se $F_{bot} = F_{sem}$, as duas hipóteses nulas valem
ao mesmo tempo. Na simulação o efeito multiplica todos
os tempos do grupo com bot pelo mesmo fator, então, quando existe efeito, as
duas H₁ também valem juntas. Assim os dois testes respondem à mesma pergunta e
a comparação entre eles é justa.

## Unicaudal ou bicaudal

Usamos teste **bicaudal**, com α = 0,05 (2,5% em cada cauda), nos dois testes.

Antes de olhar os dados, as duas direções eram plausíveis. O bot pode
acelerar o merge, porque aponta problemas simples antes da revisão humana. Ele
também pode atrasar, porque deixa comentários que o autor precisa responder e
costuma ser acionado em PRs maiores. As duas direções interessam ao time: um
atraso é custo a ser pesado e uma aceleração é ganho.

A primeira versão da pergunta, no README, falava só em o bot deixar o merge
mais rápido. Trocamos para uma pergunta sem direção porque não tínhamos motivo
forte para esperar um lado só, e porque a amostra real já tinha sido coletada
quando formalizamos as hipóteses. Escolher a cauda depois de ver que os PRs com
bot demoraram mais na amostra cortaria o p-valor pela metade sem justificativa.

## Erro tipo I e erro tipo II no cenário

- **Erro tipo I:** concluir que o bot muda o tempo até o merge quando ele não
  muda. O time poderia desligar o bot achando que ele atrasa os PRs, por causa
  de uma diferença que era só variação da amostra.
- **Erro tipo II:** não detectar uma diferença que existe. O time continuaria
  achando que o bot não interfere no tempo de merge e deixaria de considerar
  esse atraso (ou ganho) na hora de decidir como usar a ferramenta.

Para nós o erro tipo I é o mais grave. Ele leva a uma mudança de processo, como
desligar ou reconfigurar uma ferramenta que existe para melhorar a revisão, sem
motivo real. O erro tipo II também custa, mas é um custo que o time já tem hoje
e que pode ser revisto com mais dados. Isso mudaria se o atraso causado pelo
bot fosse de dias em cada PR, porque aí deixar de percebê-lo sairia caro.

## Dados reais

Coletamos 70 pull requests mergeados do repositório
[`supabase/supabase`](https://github.com/supabase/supabase): **35 com review do
CodeRabbit** (`coderabbitai[bot]`) e **35 sem review de bot**. A coleta foi
feita pela API do GitHub em 05/11/2026 e cobre PRs mergeados entre 28/10 e
05/11/2026. A metodologia, os filtros e as limitações estão em
[`data/README.md`](https://github.com/Gmbferreira/Teste-de-hipostese/blob/main/data/README.md).

## Como os dados simulados são gerados

Os tempos reais são muito assimétricos: sem bot, a mediana é 2,5 h, a média é
14,7 h e o maior tempo passa de 100 h. Por isso usamos uma **lognormal**
ajustada ao grupo sem bot, com μ = 1,33 e σ = 1,92 na escala log (mediana do
modelo de 3,8 h). Os detalhes do ajuste estão em
[`analise_exploratoria.md`](https://github.com/Gmbferreira/Teste-de-hipostese/blob/main/docs/analise_exploratoria.md).

- **Com H₀ verdadeira**, os dois grupos são sorteados dessa mesma lognormal.
- **Com efeito**, o grupo com bot usa μ + δ e o mesmo σ. Isso multiplica os
  tempos por $e^{\delta}$: com δ = 0,5 os PRs com bot demoram 1,65 vez mais.
- O efeito observado nos dados reais é δ ≈ 0,99, ou seja, PRs com bot cerca de
  2,7 vezes mais lentos.
- Cada conjunto simulado tem 35 PRs por grupo, como a amostra real.

O código está em [`src/simulacao.py`](https://github.com/Gmbferreira/Teste-de-hipostese/blob/main/src/simulacao.py) (issue #9).

## Os dois testes

- **t de Welch:** compara as médias dos dois grupos sem supor variâncias
  iguais. Pressupõe que as médias amostrais sigam aproximadamente uma normal, o
  que vale com dados normais ou com amostras grandes.
- **Mann-Whitney:** junta os 70 tempos, ordena do menor para o maior e verifica
  se os postos de um grupo ficam sistematicamente acima dos do outro. Usa só a
  ordem dos valores, então trocar o PR mais lento de 100 h por um de 1.000 h
  não muda o resultado. Com H₀ verdadeira, a distribuição da sua estatística não
  depende da forma dos dados.

O que o grupo esperava de cada teste antes de rodar as simulações está em
[`expectativa.md`](https://github.com/Gmbferreira/Teste-de-hipostese/blob/main/docs/expectativa.md) (issue #10).
