# Apresentação oral: divisão e rascunho das respostas

Rascunho da issue #25. A apresentação tem até 7 minutos para as 15 perguntas,
então cada resposta precisa caber em uns 30 segundos (umas 70 palavras). A
divisão segue quem fez cada parte do dashboard. As respostas do Gabriel já estão
escritas; nas do Guilherme ficam só a seção do dashboard e os números que
ajudam, para ele montar a resposta do jeito dele.

| Pergunta | Quem responde | Onde está no dashboard |
|---|---|---|
| 1. Cenário, H₀ e H₁ | Guilherme | Seção 1 |
| 2. Unicaudal ou bicaudal | Gabriel | Seção 1 |
| 3. Coleta e forma dos dados reais | Guilherme | Seção 2 (G1) |
| 4. Parâmetros da simulação | Guilherme | Seção 2 (G1) |
| 5. O que cada teste compara | Gabriel | Seção 3 |
| 6. Distribuição sob H₀ e região de rejeição | Gabriel | Seção 3 (G2) |
| 7. O que o p-valor significa e o que não significa | Gabriel | Seção 3 (G2) |
| 8. Erro tipo I e tipo II no cenário | Guilherme | Seção 1 |
| 9. Algum teste se afastou de 5% | Gabriel | Seção 4 (G3) |
| 10. Qual teste tem mais poder | Guilherme | Seção 5 (G4) |
| 11. Violação de pressuposto simulada | Gabriel | Seção 4 (G3 e "Como cada situação foi simulada") |
| 12. O que muda com α = 1% | Gabriel | Seção 4 (seletor de α) e seção 5 |
| 13. A simulação confirmou a expectativa | Guilherme | Seção 7 |
| 14. Dados reais e importância prática | Gabriel | Seção 6 |
| 15. Recomendação e principal limitação | Guilherme | Seção 7 |

Gabriel fica com 8 perguntas e Guilherme com 7, as duas acima do mínimo de 4.
O professor pode pedir qualquer pergunta a qualquer um, então vale os dois lerem
tudo.

## Respostas do Gabriel

**2. Unicaudal ou bicaudal?** Bicaudal. Antes de olhar os dados, as duas
direções eram plausíveis: o bot pode acelerar o merge, porque aponta problemas
simples antes da revisão humana, ou atrasar, porque deixa comentários que o
autor precisa responder. As duas interessam ao time. E como a amostra já estava
coletada quando fechamos as hipóteses, escolher a cauda depois de ver que os PRs
com bot demoraram mais cortaria o p-valor pela metade sem justificativa.

**5. O que cada teste compara?** O t de Welch compara as médias dos dois grupos,
sem supor variâncias iguais: é a diferença de médias dividida pelo erro-padrão.
O Mann-Whitney compara postos: junta os 70 tempos, ordena e conta em quantos dos
1.225 pares (um PR com bot e um sem) o PR com bot demorou mais. Por isso um PR de
200 h pesa muito no Welch e no Mann-Whitney conta só como o mais lento.

**6. No G2, o que é a distribuição sob H₀ e por que a região de rejeição fica
onde fica?** É a distribuição que a estatística teria se o bot não mudasse nada.
No Welch é uma t com 67 graus de liberdade; no Mann-Whitney é a distribuição
exata de U, centrada em 612,5 pares. A região fica nas duas pontas porque o teste
é bicaudal: valores muito longe do centro, para qualquer lado, são os raros sem
efeito, e juntos somam no máximo 5%. As barras mostram que, com os nossos dados,
a do Mann-Whitney é exatamente essa, mas a do Welch tem dois picos perto de ±1.

**7. O que significa o p-valor do exemplo, e o que ele não significa?** O
Mann-Whitney deu p = 0,005: se o bot não mudasse nada, só 0,5% das amostras dariam
um U tão longe do centro quanto 850. Ele não é a chance de H₀ ser verdadeira, nem
a chance de termos errado, e também não diz se o efeito é grande. O Welch deu
p = 0,204, e isso também não prova que não há efeito: o conjunto foi gerado com
efeito, e o Welch não viu por causa de um único PR de 229 h.

**9. No G3, algum teste se afastou de 5%?** O Mann-Whitney ficou perto de 5% em
todas as situações. O Welch foi conservador com a lognormal: 2,3% na situação
realista, 1,3% com amostras pequenas e 3,3% com outliers. O motivo aparece no
G2: um PR muito lento infla a média e o desvio-padrão juntos, e o t quase nunca
passa de 2. Com a cauda real, reamostrando os tempos, ele sobe para 4,1%. Com
grupos desbalanceados foi o contrário: liberal, com 12,8%.

**11. Que violação vocês simularam e por que ela afeta mais um teste?**
Simulamos amostras pequenas (10 por grupo), grupos desbalanceados (10 e 60) e
outliers (5% dos PRs esquecidos por semanas), além da escala log como
referência. Elas pesam mais no Welch porque ele depende da média e do
desvio-padrão, que são sensíveis a valores extremos e à assimetria. O
Mann-Whitney só usa a ordem dos tempos, e com H₀ verdadeira a distribuição de U
não muda com a forma dos dados.

**12. E com α = 1%?** É só trocar o seletor da seção 4. A região de rejeição
encolhe e a referência do G3 vai para 1%, mas o desenho se mantém: o
Mann-Whitney fica perto de 1% (com 10 PRs por grupo cai para 0,8%, porque U é
discreto), o Welch continua conservador com a lognormal (0,2% na realista) e,
com grupos desbalanceados, rejeita 4,0%, quatro vezes α. No G4 as curvas de poder
descem para os dois testes, porque fica mais difícil rejeitar.

**14. Nos dados reais os testes concordaram? O efeito importa na prática?** Não
concordaram: o Mann-Whitney rejeitou H₀ (p = 0,023) e o Welch não (p = 0,055).
Pela escala de Vargha e Delaney o efeito é médio, já que em 66% dos pares o PR
com bot demorou mais, mas na prática pesa: a mediana passa de 2,5 h para 17,6 h
e, pelo log do tempo, os PRs com bot são 2,7 vezes mais lentos. Como o estudo é
observacional e os PRs com bot são maiores, não dá para culpar só o bot.

## Apoio para as respostas do Guilherme

- **1.** Seção 1: pergunta, H₀ e H₁ em palavras simples, e a tabela formal.
- **3.** Seção 2 e `data/README.md`: 70 PRs do `supabase/supabase` pela API do
  GitHub (35 com review do CodeRabbit e 35 sem), muito assimétricos à direita,
  com 5 e 2 outliers pelo critério de 1,5 × IQR.
- **4.** Seção 2: lognormal ajustada ao grupo sem bot (μ = 1,33 e σ = 1,92), 35
  PRs por grupo e o efeito observado δ = 0,99 (PRs com bot 2,7 vezes mais lentos).
- **8.** Seção 1 e `docs/cenario.md`: erro tipo I é concluir que o bot muda o
  tempo quando não muda, e é o mais grave, porque leva a desligar a ferramenta sem
  motivo; erro tipo II é não ver uma mudança que existe.
- **10.** Seção 5 (G4) e `docs/situacoes_q3.md`: na lognormal o Mann-Whitney tem
  mais poder; na escala log o Welch passa por até 2,3 pontos percentuais; com a
  cauda real o Welch passa na frente a partir de δ = 1,25.
- **13.** Seção 7 e `docs/expectativa.md`: acertamos o Mann-Whitney perto de 5%,
  o Welch conservador e liberal com grupos desbalanceados, e o Mann-Whitney com
  mais poder na lognormal. Erramos o tamanho do conservadorismo do Welch (2,3%
  contra 3% a 4,5%), o caso dos outliers (3,3%, menos conservador, e não mais) e o
  poder do Welch no efeito observado (17%, abaixo dos 20% a 35% do palpite).
- **15.** Seção 7 e seção 6: a recomendação depende da cauda. Com a lognormal o
  Mann-Whitney ganha em tudo; com a cauda real os dois empatam perto do efeito
  observado e o Welch ganha nos efeitos grandes. A principal limitação é o modelo
  de dados (a lognormal tem PRs bem mais lentos que os reais), além de o estudo
  ser observacional, com um repositório, um bot e 8 dias de PRs.

## Ensaio

Falta ensaiar juntos com o dashboard aberto, cronometrando as 15 respostas.
Abrir o dashboard antes da aula deixa as simulações em cache, e aí as seções
abrem na hora.
