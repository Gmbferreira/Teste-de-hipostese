# Expectativa antes de simular

> Registrada em **05/11/2026**, antes de rodar qualquer simulação de Q1, Q2 ou
> Q3. Este arquivo foi commitado antes do código das simulações (issues #14,
> #15 e #16), para que a comparação da seção 7 do dashboard seja honesta: o que
> está escrito aqui não foi ajustado depois de ver os resultados.

## O que já sabíamos antes de simular

- Os tempos reais são muito assimétricos à direita. A assimetria é de 1,87 no
  grupo com bot e de 2,80 no grupo sem bot, e o Shapiro-Wilk rejeita a
  normalidade dos dois grupos na escala bruta (p < 0,0001).
- Há PRs muito mais lentos que o resto: 5 com bot e 2 sem bot passam de 90 h,
  enquanto as medianas são 17,6 h e 2,5 h.
- Na escala log os dados ficam bem mais perto da normal, e por isso o modelo da
  simulação é uma lognormal. O σ = 1,92 na escala log indica uma cauda muito
  pesada na escala de horas.
- O t de Welch não exige variâncias iguais, mas precisa que a média de cada
  grupo se comporte como uma normal. Com 35 PRs e uma cauda desse tamanho,
  achamos que isso não vale bem.
- O Mann-Whitney usa só a ordem dos tempos. Se os dois grupos vêm da mesma
  distribuição, a distribuição da estatística U é sempre a mesma, seja qual for
  a forma dos dados.

## Situações que vamos simular

| Situação | O que muda | Por que incluímos |
|---|---|---|
| Realista | lognormal ajustada, 35 PRs por grupo | é a situação mais parecida com os dados reais (Q1 e Q2) |
| Amostras pequenas | 10 PRs por grupo | com poucos dados o Welch depende mais da normalidade (Q3) |
| Grupos desbalanceados | 10 PRs com bot e 60 sem bot | é comum o bot estar em só uma parte dos PRs, e com grupos de tamanhos diferentes a assimetria das duas médias não se compensa (Q3) |
| Outliers | cerca de 5% dos PRs ficam esquecidos e levam de 1 a 4 semanas a mais | PRs abandonados e retomados depois aparecem em repositórios reais (Q3) |
| Escala log (referência) | mesmos dados da situação realista, com os testes aplicados ao log do tempo | é a situação boa para o Welch, porque o log dos tempos segue uma normal |

Em todas a decisão usa α = 0,05 bicaudal e 10.000 repetições por ponto.

## Erro tipo I (Q1 e Q3)

Esperamos que o **Mann-Whitney** fique perto de 5% em todas as situações,
porque com H₀ verdadeira a estatística U não depende da forma dos dados. Com 10
PRs por grupo ele pode ficar um pouco abaixo, já que U assume poucos valores e
o teste exato não consegue cortar exatamente em 5%.

Para o **t de Welch** esperamos um teste conservador na situação realista, com
algo entre 3% e 4,5% de rejeições. Quando um PR muito lento cai na amostra, ele
aumenta a diferença entre as médias, mas aumenta ainda mais o desvio-padrão, e
o t raramente fica grande. Com amostras pequenas e com outliers achamos que ele
fica ainda mais conservador. Com grupos desbalanceados esperamos o contrário:
o grupo pequeno passa a dominar a estatística, o t fica assimétrico e o Welch
pode passar de 5% (liberal). Na escala log esperamos os dois testes perto de 5%.

Vamos chamar de "perto de 5%" uma proporção entre 4,6% e 5,4%, que é a margem
de erro de cerca de ±0,4 ponto percentual das 10.000 repetições.

## Poder (Q2 e Q3)

Na situação realista esperamos que o **Mann-Whitney tenha mais poder** que o
Welch em qualquer efeito acima de zero, e com folga. O efeito do bot multiplica
os tempos, e o Welch compara médias que, nesses dados, são puxadas por poucos
PRs muito lentos. O Mann-Whitney só olha a ordem: um PR de 300 h pesa o mesmo
que pesaria se tivesse levado 40 h, desde que continue sendo o mais lento.

Com o efeito observado nos dados reais (δ ≈ 0,99, PRs com bot cerca de 2,7
vezes mais lentos) e 35 PRs por grupo, nosso palpite é um poder de 50% a 60%
para o Mann-Whitney e de 20% a 35% para o Welch.

Nas situações de Q3:

- **Amostras pequenas:** os dois perdem muito poder, e o Mann-Whitney continua
  na frente.
- **Grupos desbalanceados:** o poder cai em relação aos grupos de 35, porque o
  grupo de 10 limita o que dá para ver, e o Mann-Whitney continua na frente.
- **Outliers:** o Welch perde bastante poder, porque os PRs esquecidos inflam o
  desvio-padrão. O Mann-Whitney quase não muda.
- **Escala log:** aqui esperamos que a vantagem mude de lado. Com dados normais
  o Welch deve ter um pouco mais de poder, mas só alguns pontos percentuais. O
  Mann-Whitney deve ter exatamente o mesmo poder da situação realista, porque
  tirar o log não muda a ordem dos tempos.

## Resumo

| Situação | Erro tipo I do Welch | Erro tipo I do Mann-Whitney | Mais poder |
|---|---|---|---|
| Realista | abaixo de 5% (3% a 4,5%) | perto de 5% | Mann-Whitney, com folga |
| Amostras pequenas | abaixo de 5% | perto ou um pouco abaixo de 5% | Mann-Whitney |
| Grupos desbalanceados | pode passar de 5% | perto de 5% | Mann-Whitney |
| Outliers | abaixo de 5% | perto de 5% | Mann-Whitney, com mais folga |
| Escala log | perto de 5% | perto de 5% | Welch, por pouco |

Antes de simular, nossa aposta é que o **Mann-Whitney** é o teste mais indicado
para o tempo até o merge medido em horas. O Welch só deve ficar competitivo se
o tempo for analisado na escala log, e mesmo assim com uma vantagem pequena.
