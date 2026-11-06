# Situações de Q3

> Gerado por `python -m src.situacoes` (issue #16). 10.000 repetições
> por ponto, semente 42, α = 0,05 bicaudal. As quatro situações de Q3
> são as que registramos em [`expectativa.md`](expectativa.md) antes de simular; a
> reamostragem dos tempos reais foi incluída depois, como análise de sensibilidade.

A situação realista (lognormal ajustada aos dados reais, 35 PRs por grupo) é a
base de Q1 e Q2. Em Q3 repetimos as duas perguntas mudando uma coisa de cada
vez. Todas as situações usam a mesma semente, então os sorteios de base são os
mesmos e a diferença entre elas vem só do que foi alterado.

## As situações

| Situação | O que muda | Por que incluímos |
|---|---|---|
| Amostras pequenas | mesma lognormal, 10 PRs por grupo | com poucos dados o Welch depende mais da normalidade |
| Grupos desbalanceados | 10 PRs com bot e 60 sem bot | é comum o bot estar em só uma parte dos PRs, e com grupos de tamanhos diferentes a assimetria das duas médias não se compensa |
| Outliers | cerca de 5% dos PRs ficam esquecidos e levam de 1 a 4 semanas a mais | PRs abandonados e retomados depois aparecem em repositórios reais |
| Escala log (referência) | mesmos dados da situação realista, com os testes aplicados ao log do tempo | é a situação boa para o Welch, porque o log dos tempos segue uma normal |
| Tempos reais reamostrados (sensibilidade) | sorteia com reposição os tempos dos 35 PRs reais sem bot, com uma variação de cerca de 25% em cada tempo para não haver empates | a lognormal ajustada gera PRs bem mais lentos que os reais; aqui a cauda é a da própria amostra (incluída depois de simular, não estava na expectativa) |

## Erro tipo I (δ = 0)

Proporção de p-valores abaixo de 5% com H₀ verdadeira, com o intervalo de 95%
entre parênteses.

| Situação | t de Welch | Mann-Whitney |
|---|---:|---:|
| Amostras pequenas | 1,31% (1,11% a 1,55%) | 4,60% (4,21% a 5,03%) |
| Grupos desbalanceados | 12,81% (12,17% a 13,48%) | 4,94% (4,53% a 5,38%) |
| Outliers | 3,30% (2,97% a 3,67%) | 4,97% (4,56% a 5,41%) |
| Escala log (referência) | 4,76% (4,36% a 5,19%) | 4,76% (4,36% a 5,19%) |
| Tempos reais reamostrados (sensibilidade) | 4,10% (3,73% a 4,51%) | 4,81% (4,41% a 5,25%) |

## Poder

Proporção de rejeições para cada tamanho de efeito. Com δ = 0 o valor é o
próprio erro tipo I.

### Amostras pequenas

| δ | PRs com bot mais lentos | t de Welch | Mann-Whitney |
|---:|---:|---:|---:|
| 0,00 | 1,00× | 1,3% | 4,6% |
| 0,25 | 1,28× | 1,4% | 5,3% |
| 0,50 | 1,65× | 1,8% | 7,7% |
| 0,75 | 2,12× | 2,8% | 11,3% |
| 1,00 | 2,72× | 4,0% | 17,6% |
| 1,25 | 3,49× | 5,6% | 25,2% |
| 1,50 | 4,48× | 7,6% | 34,0% |
| 2,00 | 7,39× | 12,6% | 54,8% |
### Grupos desbalanceados

| δ | PRs com bot mais lentos | t de Welch | Mann-Whitney |
|---:|---:|---:|---:|
| 0,00 | 1,00× | 12,8% | 4,9% |
| 0,25 | 1,28× | 8,3% | 6,2% |
| 0,50 | 1,65× | 4,9% | 10,9% |
| 0,75 | 2,12× | 3,0% | 19,0% |
| 1,00 | 2,72× | 2,2% | 30,9% |
| 1,25 | 3,49× | 2,3% | 44,9% |
| 1,50 | 4,48× | 3,3% | 59,4% |
| 2,00 | 7,39× | 7,8% | 82,8% |
### Outliers

| δ | PRs com bot mais lentos | t de Welch | Mann-Whitney |
|---:|---:|---:|---:|
| 0,00 | 1,00× | 3,3% | 5,0% |
| 0,25 | 1,28× | 3,7% | 7,5% |
| 0,50 | 1,65× | 4,7% | 15,4% |
| 0,75 | 2,12× | 7,1% | 29,0% |
| 1,00 | 2,72× | 10,6% | 47,1% |
| 1,25 | 3,49× | 15,8% | 65,6% |
| 1,50 | 4,48× | 22,3% | 80,8% |
| 2,00 | 7,39× | 39,1% | 96,8% |
### Escala log (referência)

| δ | PRs com bot mais lentos | t de Welch | Mann-Whitney |
|---:|---:|---:|---:|
| 0,00 | 1,00× | 4,8% | 4,8% |
| 0,25 | 1,28× | 8,2% | 8,1% |
| 0,50 | 1,65× | 18,5% | 17,9% |
| 0,75 | 2,12× | 35,9% | 34,4% |
| 1,00 | 2,72× | 56,6% | 54,6% |
| 1,25 | 3,49× | 76,6% | 74,3% |
| 1,50 | 4,48× | 90,1% | 88,5% |
| 2,00 | 7,39× | 98,8% | 98,8% |
### Tempos reais reamostrados (sensibilidade)

| δ | PRs com bot mais lentos | t de Welch | Mann-Whitney |
|---:|---:|---:|---:|
| 0,00 | 1,00× | 4,1% | 4,8% |
| 0,25 | 1,28× | 7,7% | 11,6% |
| 0,50 | 1,65× | 19,4% | 28,6% |
| 0,75 | 2,12× | 38,6% | 47,2% |
| 1,00 | 2,72× | 61,0% | 63,3% |
| 1,25 | 3,49× | 80,4% | 75,6% |
| 1,50 | 4,48× | 92,0% | 85,1% |
| 2,00 | 7,39× | 99,1% | 96,4% |

## O que chama atenção

- Com grupos desbalanceados o Welch fica viesado: com efeito δ = 1,00 ele rejeita H₀ em 2,2% dos casos, menos do que sem efeito nenhum (12,8%).
- Com os tempos reais reamostrados o erro tipo I do Welch sobe para 4,1%, mais perto de 5% do que na lognormal. O Mann-Whitney continua com mais poder nos efeitos pequenos, mas a partir de δ = 1,25 o Welch passa na frente (80,4% contra 75,6%): com a cauda da amostra a vantagem muda de lado nos efeitos grandes.
- Na escala log o Welch tem poder igual ou um pouco maior que o do Mann-Whitney (no máximo 2,3 pontos percentuais a mais), e o Mann-Whitney repete exatamente o poder da situação realista, porque tirar o log não muda a ordem dos tempos.
