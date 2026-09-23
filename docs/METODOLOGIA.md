# Método e resultados

## Dados analisados

Relatórios institucionais do curso de Sistemas de Informação, fornecidos pela Secretaria Acadêmica da Universidade Estadual de Goiás, Unidade Universitária de Goianésia (UEG/UnU Goianésia). A execução de 23/09/2026 processou 40 PDFs: 584 registros de ingresso (2006–2020) e 204 de conclusão (2009/1–2026/1).

São registros documentais, não necessariamente pessoas distintas em toda a série. O processamento identifica repetições dentro dos relatórios, ignora cópias idênticas de PDFs nos compactados e interrompe a análise quando detecta sobreposição documental não resolvida. PDFs sem texto pesquisável, arquivos 7z com senha, corrompidos ou sem PDFs exigem revisão. O limite de descompactação é de 1 GiB por arquivo; compactados internos não são abertos.

## Modelo probabilístico

O Genderize.io retorna `gender`, `probability` e `count`. A execução utiliza nomes completos (`GENDERIZE_NAME_MODE = "full"`) e contexto brasileiro (`COUNTRY_ID = "BR"`). A probabilidade retornada pelo serviço não foi calibrada ou validada contra gênero autodeclarado nesta pesquisa. O campo `count` se refere à base usada pelo serviço; não é uma contagem de estudantes da UEG.

O modelo atribui a cada registro com inferência uma probabilidade feminina `q`: `q = p` para a resposta `female` e `q = 1 − p` para `male`. Para uma variável binária de classificação modelada `X_i`, assume-se `P(X_i = 1) = q_i`. Essa representação estatística não define a identidade de gênero da pessoa.

Para `N` registros, `R` com inferência e `U = N − R` sem inferência:

| Medida | Fórmula |
|---|---|
| Quantidade feminina esperada | `E[F] = Σq_i` |
| Quantidade masculina esperada | `E[M] = R − E[F]` |
| Participação feminina | `100 × E[F] / R` |
| Participação masculina | `100 × E[M] / R` |
| Cobertura | `100 × R / N` |
| Variância feminina, sob independência | `Var(F) = Σq_i(1 − q_i)` |
| Desvio padrão | `√Var(F)` |

Não se conta cada resposta `female` como uma mulher confirmada. Todos os registros com probabilidade válida contribuem com seu peso, inclusive aqueles de baixa confiança. As classes de confiança são descritivas; não excluem registros desses cálculos.

Exemplo: em 40 registros, 30 têm inferência e `Σq = 12`. A participação feminina estimada é de 40% entre os 30 registros com inferência, e a cobertura é de 75%. O percentual de um conjunto de períodos é calculado pelas somas das quantidades esperadas e dos registros com inferência; não pela média simples dos percentuais de cada período.

Se `R = 0`, os percentuais e o intervalo entre resolvidos ficam indisponíveis. Os registros sem inferência não recebem probabilidade 0,5 e não são considerados masculinos. Uma cobertura de 100% indica disponibilidade de respostas, não acurácia de 100%.

## Intervalos e limitações

Sob independência entre registros com inferência, a soma das variáveis binárias segue uma distribuição Poisson-binomial. O software calcula sua distribuição por recorrência exata, sem simulação, e obtém os quantis de 2,5% e 97,5%. No gráfico percentual, esses quantis são divididos por `R` e multiplicados por 100.

O intervalo de 95% é condicional às probabilidades fornecidas e à hipótese de independência. Não é um intervalo de confiança amostral nem incorpora integralmente erros de extração, vieses culturais ou erros de calibração da API. Registros com nomes iguais ou da mesma pessoa podem violar a independência assumida. O modelo binário não representa a diversidade das identidades de gênero. Sem referência autodeclarada, não se estima acurácia, precisão, recall ou F1.

Nos relatórios locais, os não identificados também permitem limites extremos: o intervalo de contagem vai de `quantil inferior` a `quantil superior + U`; a expectativa feminina no total fica entre `E[F]/N` e `(E[F]+U)/N`. Esses limites têm interpretações diferentes e não substituem o intervalo entre registros com inferência.

## Resultados da execução

| Grupo | Total | Com inferência | Feminina esperada | Masculina esperada | Feminina (%) | Masculina (%) |
|---|---:|---:|---:|---:|---:|---:|
| Ingressantes | 584 | 584 | 189,81 | 394,19 | 32,50 | 67,50 |
| Concluintes | 204 | 204 | 72,16 | 131,84 | 35,37 | 64,63 |

A cobertura foi de 100% nos dois grupos, sem registros não identificados nesta execução. As quantidades fracionárias são valores esperados, não contagens de pessoas confirmadas. Os percentuais foram arredondados somente para apresentação.

A diferença feminina entre concluintes e ingressantes, calculada antes do arredondamento, é de **2,87 pontos percentuais**. Os grupos abrangem períodos distintos e não correspondem necessariamente às mesmas coortes. A diferença é descritiva: não demonstra maior probabilidade de conclusão para mulheres, redução de evasão ou significância estatística.

Houve predominância masculina no conjunto dos registros, mas não em todos os períodos. Entre os ingressantes de 2013, a participação feminina estimada foi de 58,07%; entre concluintes de 2009, de 58,47%. As séries apresentam oscilações. Não foi realizado teste formal de tendência; portanto, não se afirma ausência de tendência estatística apenas pela inspeção dos gráficos.

Os valores desta execução substituem, para sua descrição, as estimativas preliminares de 35,1% feminina e 64,9% masculina entre concluintes. Não foi estabelecida a causa da diferença em relação ao resumo anterior.

## Coortes, dados públicos e reprodução

A análise opcional de coortes requer nome normalizado e curso iguais, conclusão posterior e correspondência única nos dois sentidos. A proporção de ingressantes reencontrados nas listas disponíveis não constitui taxa oficial de conclusão. Documentos ausentes, homônimos, mudanças de nome ou curso e coortes recentes limitam a análise.

Os nomes consultados são enviados ao Genderize.io. Os documentos originais, a chave e os arquivos locais não são publicados. O snapshot mantém identificadores aleatórios; o cache utiliza índices HMAC e respostas sem nomes em texto claro. São dados locais pseudonimizados, ainda de acesso restrito.

Os relatórios locais suprimem grupos menores que cinco por padrão (`MIN_GROUP_SIZE`). A exportação pública é independente dessa supressão e contém os agregados completos, conforme o escopo do projeto. Não inclui nomes ou registros individuais; grupos pequenos e cruzamentos podem permitir inferências sobre pessoas.

O [painel público](https://natansr.github.io/elas-ti/) e os arquivos em `site/data/` permitem consultar os agregados sem os PDFs. Reconstruir a extração exige acesso autorizado aos documentos. Novas consultas ao serviço podem produzir resultados diferentes; o cache e o snapshot locais preservam as respostas e os parâmetros utilizados.
