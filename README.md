# ELAS-TI

Estudo Longitudinal da Participação Feminina no Ingresso e na Conclusão dos Cursos de Tecnologia da Informação

O ELAS-TI é um software de apoio à pesquisa desenvolvido pelo grupo de pesquisa ANDSol/UEG, na Universidade Estadual de Goiás, Unidade Universitária de Goianésia. Seu objetivo é analisar a participação feminina entre ingressantes e concluintes de cursos de TI a partir de relatórios institucionais em PDF.

O processamento reúne extração e validação dos registros, identificação de repetições, análise estatística e acompanhamento de coortes. A inferência probabilística de gênero utiliza o [Genderize.io](https://genderize.io), com contexto brasileiro. As estimativas são baseadas nos nomes e não correspondem a gênero autodeclarado.

A extração e a análise funcionam localmente, pelo terminal. O projeto mantém os gráficos Matplotlib e inclui um painel interativo com Plotly.js, preparado para GitHub Pages. O painel recebe somente estatísticas agregadas em JSON e CSV; os PDFs e os registros individuais ficam no computador.

## Instalação

O projeto requer Python 3.11 ou superior. A preparação do ambiente e a instalação das dependências são feitas na pasta do repositório:

```sh
python -m venv .venv
```

A ativação do ambiente depende do sistema operacional:

```sh
# Linux e macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

```sh
pip install -r requirements.txt
```

A chave do Genderize.io é configurada na variável `GENDERIZE_API_KEY`, em um arquivo `.env` local baseado em `.env.example`. A modalidade com API envia os nomes consultados ao serviço; os PDFs permanecem no computador. O processamento sem API utiliza somente os resultados já armazenados no cache.

## Execução

Os documentos de entrada ficam em `pdfs/ingressantes/` e `pdfs/formandos/`. Curso, período e tipo de registro são identificados pelo conteúdo dos relatórios.

| Comando | Finalidade |
|---|---|
| `python main.py --dry-run` | Extração e validação dos PDFs, sem consulta à API. |
| `python main.py` | Análise completa, com consulta ao Genderize.io para nomes ausentes do cache. |
| `python main.py --no-api` | Análise com o cache local; registros sem inferência permanecem não identificados. |
| `python main.py --export-site` | Exportação da última análise para `site/data/resumo.json` e `resumo.csv`, sem consulta à API. |
| `python main.py --graphs` | Menu de seleção e exportação dos gráficos da última análise salva. |
| `python main.py --rebuild-reports` | Reconstrução dos relatórios a partir dos dados salvos localmente. |

A validação registra totais, duplicações e divergências em `output/reports/validacao_pdfs.txt`. Problemas estruturais de extração interrompem a análise. PDFs sem texto pesquisável ou com layouts não reconhecidos precisam de revisão; o programa não realiza OCR.

As configurações de cursos, inferência e acompanhamento ficam em `config.py`. As opções `--pdf-root` e `--output-dir` permitem alterar as pastas de entrada e saída. A lista completa está disponível em `python main.py --help`.

## Painel interativo

Os PDFs de ingresso ficam em **`pdfs/ingressantes/`** e os de conclusão em **`pdfs/formandos/`**. As pastas já fazem parte da estrutura do projeto; os PDFs são ignorados pelo Git.

A extração, a análise e a exportação pública são executadas na raiz do projeto:

```sh
python main.py && python main.py --export-site
```

Sem consulta ao Genderize.io, o processamento utiliza apenas o cache disponível:

```sh
python main.py --no-api && python main.py --export-site
```

Sem inferências no cache, o painel apresenta as contagens documentais e os registros não identificados. Os percentuais de gênero ficam indisponíveis. A exportação usa a última análise salva: novos PDFs precisam passar novamente pelo processamento.

A prévia local fica em `http://localhost:8000` após:

```sh
python -m http.server 8000 --bind 127.0.0.1 --directory site
```

O painel oferece filtros por curso, tipo de registro e período, com agrupamento anual ou semestral. Inclui contagens, barras feminina/masculina, linha da participação feminina com intervalo probabilístico, pizza, cobertura, tabela e downloads. O Plotly.js é carregado de um CDN; sem conexão, a tabela e os dados continuam disponíveis no servidor local.

Os arquivos `site/data/resumo.json` e `site/data/resumo.csv` contêm os mesmos agregados, incluindo grupos pequenos, sem nomes, identificadores individuais ou referências aos PDFs. Há linhas por curso e para todos os cursos, anuais e semestrais: esses recortes são alternativos e não devem ser somados entre si. Percentuais usam registros resolvidos; `null` no JSON e campo vazio no CSV significam indisponibilidade, não zero.

### GitHub Pages

A pasta `site/` é a única incluída na publicação. Em **Settings → Pages**, a origem é **GitHub Actions**. Após o commit e push do site e dos agregados, a execução manual de **Actions → Publicar painel ELAS-TI → Run workflow**, na `main`, valida os arquivos e publica a página. Atualizações seguem o mesmo fluxo. O workflow não executa a extração nem recebe PDFs ou chave de API.

O site é destinado a acesso público. Pages em repositórios privados depende do plano da conta; a configuração não altera a visibilidade do repositório. [Documentação do GitHub](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site).

## Gráficos e resultados locais

O menu oferece filtros de curso e período, com análises de ingresso e conclusão. Estão disponíveis gráficos de contagem, participação feminina, cobertura da inferência, comparação entre ingresso e conclusão, correspondências por coorte e tempo até conclusão.

A composição feminina e masculina pode ser apresentada em pizza, para o período selecionado, ou em barras comparativas por ano. Esses percentuais consideram apenas os registros com inferência disponível. A cobertura é indicada nos gráficos, e a ausência de informação não é interpretada como participação masculina. O gráfico de participação feminina também apresenta o intervalo probabilístico de incerteza; a pizza mostra somente as estimativas centrais.

| Pasta | Conteúdo |
|---|---|
| `output/csv/` | Resumos estatísticos, comparações e análises de coortes. |
| `output/reports/` | Relatório da análise e auditoria da extração. |
| `output/figures/` | Gráficos exportados. |

O menu utiliza a última análise salva e não faz consultas à API. Novos documentos ou novas inferências são incorporados após uma nova execução da análise.

## Método e métricas

As análises são calculadas separadamente para ingressantes e concluintes, por curso, ano e semestre. Na tabela abaixo, **N** representa o total de registros, **R** os registros com inferência e **U = N − R** os não identificados. A probabilidade feminina **q** corresponde a `p` quando a resposta da API é `female` e a `1 − p` quando é `male`.

| Métrica | Definição |
|---|---|
| Cobertura | `R / N`: proporção dos registros com inferência disponível. |
| Quantidades esperadas | Mulheres: `Σq`; homens: `R − Σq`. São estimativas e podem ser fracionárias. |
| Participação estimada | Quantidade esperada dividida por **R**, multiplicada por 100. |
| Variância e desvio padrão | `Σq(1 − q)` e sua raiz quadrada, para a contagem feminina. |
| Intervalo probabilístico de 95% | Quantis de 2,5% e 97,5% da distribuição Poisson-binomial exata, sob independência entre registros. |
| Limites com não identificados | Contagem: `[quantil inferior, quantil superior + U]`. Expectativa percentual no total: `[Σq/N, (Σq+U)/N] × 100`. |
| Variação temporal | Diferença em pontos percentuais entre períodos disponíveis, sem preencher períodos ausentes. |

Por exemplo, 40 registros, dos quais 30 têm inferência, com quantidade feminina esperada de 12, resultam em cobertura de 75% e participação feminina estimada de 40% entre os registros resolvidos.

O intervalo probabilístico depende das hipóteses do modelo e não é um intervalo de confiança amostral clássico. As probabilidades do Genderize.io estão sujeitas a vieses e erros de calibração; seu modelo binário não representa a diversidade das identidades de gênero.

As coortes são definidas pelo curso e período de ingresso. Uma correspondência exige nome normalizado e curso iguais, conclusão posterior e vínculo único nos dois sentidos. A proporção resultante expressa ingressantes reencontrados nas listas de conclusão disponíveis, não uma taxa oficial de conclusão. Documentos ausentes, homônimos e mudanças de nome ou curso limitam essa interpretação.

## Tratamento dos dados

As saídas não incluem CSVs individuais nem nomes de estudantes. O snapshot local preserva os dados necessários à reconstrução das análises com identificadores aleatórios, sem nomes ou números de sequência. O cache armazena índices HMAC e respostas sem nomes em texto claro. Esses arquivos são pseudonimizados e continuam sendo dados de acesso restrito.

Por padrão, gráficos e resumos **locais** suprimem grupos menores que cinco e estimativas com poucos registros resolvidos. A auditoria local mantém as contagens necessárias à validação. Essas medidas reduzem a exposição, mas não garantem anonimato, sobretudo em grupos pequenos ou no cruzamento de resultados.

PDFs, credenciais, cache, chaves e a pasta `output/` são ignorados pelo Git. A exportação pública é separada: publica números agregados sem supressão por tamanho de grupo, conforme o escopo do projeto. Isso remove a identificação nominal, mas não garante anonimato absoluto. O único CSV permitido no versionamento é `site/data/resumo.csv`, validado junto ao JSON.

## Desenvolvimento

O código está em `src/elas_ti/` e os testes em `tests/`.

```sh
pytest
python scripts/check_publication.py --history
python scripts/validate_public_data.py
```

A suíte bloqueia chamadas reais à API. Os testes de integração com documentos institucionais são executados apenas quando os PDFs estão disponíveis localmente. O GitHub Actions executa os testes e a verificação preventiva de arquivos privados e possíveis credenciais no histórico. Essa verificação não substitui a revisão dos materiais antes da publicação.

## Autoria

Vitória Maria Diniz e Natan S. Rodrigues. Projeto desenvolvido pelo grupo de pesquisa **ANDSol/UEG**.

## Licença

O ELAS-TI é distribuído sob os termos da GNU General Public License, versão 3 ou posterior (`GPL-3.0-or-later`). O texto completo está em [LICENSE](LICENSE).

Copyright (C) 2026 Vitória Maria Diniz e Natan S. Rodrigues.
