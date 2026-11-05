# Os dois testes em um conjunto simulado

> Gerado por `python -m src.exemplo` (issue #11). Semente 42,
> 35 PRs por grupo, δ = 0,99, α = 0,05 bicaudal.
> O cenário e as hipóteses estão em [`cenario.md`](cenario.md).

### Resultado

| Teste | O que compara | Estatística | p-valor | Tamanho do efeito | Decisão (α = 5%) | Acertou? |
|---|---|---|---|---|---|---|
| t de Welch | médias | t = 1,28 (gl = 67,0) | 0,204 | diferença de médias = 11,2 h (d = 0,31) | não rejeita H₀ | não (erro tipo II) |
| Mann-Whitney | postos | U = 850 de 1.225 pares | 0,005 | P(PR com bot demorar mais) = 0,69 (r = 0,39) | rejeita H₀ | sim |

### O conjunto simulado

Sorteamos 35 PRs com bot e 35 sem bot com o gerador da #9. Usamos o efeito observado nos dados reais (δ = 0,99, PRs com bot 2,69 vezes mais lentos). Como fomos nós que geramos os dados, sabemos a resposta certa: **H₀ é falsa** e o correto é rejeitá-la.

Neste conjunto, a mediana ficou em 13,9 h com bot e 4,3 h sem bot. O PR mais lento de todos ficou no grupo sem bot, com 229,2 h.

### O que cada teste fez

**t de Welch.** Comparou as médias: 25,6 h com bot contra 14,4 h sem bot, uma diferença de 11,2 h (IC de 95%: −6,2 h a 28,5 h). Os desvios-padrão foram de 34,2 h e 38,6 h, puxados pelos PRs mais lentos: sem o PR de 229,2 h, a média do grupo sem bot cairia para 8,1 h. O t ficou em 1,28, abaixo do valor crítico de 2,00 em módulo. Com p = 0,204, o teste **não rejeitou H₀** e cometeu um **erro tipo II**. Sem ele, o Welch daria p = 0,006 e rejeitaria H₀: um único PR mudou a decisão.

**Mann-Whitney.** Comparou os postos. Dos 1.225 pares possíveis (um PR com bot e um sem bot), o PR com bot demorou mais em 850, ou 69,4% dos pares. Se o bot não mudasse nada, o esperado seria perto de 612,5 pares, e a região de rejeição é U ≤ 445 ou U ≥ 780. Para esse teste, o PR de 229,2 h conta só como o mais lento: com qualquer tempo acima de 178,4 h, que é o maior do outro grupo, U seria o mesmo. Com p = 0,005, o teste **rejeitou H₀** e acertou.

### O que o p-valor do exemplo quer dizer

O p-valor é a probabilidade de, com H₀ verdadeira, sair uma estatística tão afastada do centro quanto a que observamos. No G2 ele aparece como a área pintada nas duas caudas.

- No Mann-Whitney, p = 0,005 quer dizer que, se o bot não mudasse nada, só 0,5% das amostras dariam um U tão longe de 612,5 quanto 850. Isso não é a chance de H₀ ser verdadeira, e também não diz se o efeito é grande.
- No Welch, p = 0,204 quer dizer que 20,4% das amostras sem efeito dariam um |t| maior ou igual a 1,28. Não rejeitar H₀ também não prova que o bot não muda nada: pode faltar poder para ver o efeito.

### Cuidado

É um conjunto só. Com outra semente os dois testes poderiam concordar, ou trocar de papel. Quantas vezes cada teste acerta é o que as simulações de Q1 e Q2 (issues #14 e #15) vão medir.
