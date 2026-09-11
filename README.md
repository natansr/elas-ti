# ELAS-TI

Estudo Longitudinal da Participação Feminina no Ingresso e na Conclusão dos Cursos de Tecnologia da Informação

Universidade Estadual de Goiás — Unidade Universitária de Goianésia.

O projeto processa relatórios institucionais locais de ingresso e conclusão,
produz auditoria da extração e estima a participação feminina por inferência
probabilística a partir dos nomes. Também acompanha correspondências entre
listas de ingresso e conclusão posteriores, no mesmo curso.

## Instalação

Python 3.11 ou superior:

```sh
python -m venv .venv
```

Linux/macOS:

```sh
source .venv/bin/activate
```

Windows:

```bat
.venv\Scripts\activate
```

```sh
pip install -r requirements.txt
```

Crie localmente `.env` a partir de `.env.example`:

```dotenv
GENDERIZE_API_KEY=sua_chave
```

Não publique esse arquivo. Coloque os PDFs em `pdfs/ingressantes/` e
`pdfs/formandos/`. O conteúdo, e não o nome do arquivo, determina o tipo,
curso e período. Comece sempre pela auditoria:

```sh
python main.py --dry-run
pytest
```

## Extração e validação

O parser suporta os cabeçalhos e as linhas tabulares dos relatórios descritos
no estudo. Usa PyMuPDF, sem OCR automático. Páginas sem texto, linhas sem
fronteiras reconhecidas, totais divergentes e homônimos geram avisos.
Layout diferente exige inspeção e adaptação; nunca se completam registros
por suposição. O motivo de entrada fica vazio quando não há delimitação segura;
as cotas não são extraídas.

Repetições internas são removidas pela combinação de tipo, documento, curso,
período, sequência e chave do nome. Sequências distintas com o mesmo nome
permanecem como registros distintos e são encaminhadas à revisão.

Os testes usam exclusivamente nomes sintéticos. Testes marcados `integration`
verificam os totais locais conhecidos (44, 30, 3 e 2), se os documentos
correspondentes estiverem presentes. Sem PDFs eles são ignorados. Um PDF
presente mas não validado provoca falha, evitando um sucesso enganoso.

## Privacidade

PDFs, `.env`, cache SQLite, CSVs e toda a pasta `output/` são ignorados pelo Git.
Os relatórios agregados não listam nomes. CSVs detalhados e cache contêm dados
pessoais e devem ficar em armazenamento local com acesso restrito. Não há
upload de PDFs. Apenas nomes consultados são enviados ao Genderize quando
se executa a modalidade com API. O dry-run não chama a API.

Não há licença definida. O repositório deve permanecer privado.

## Estrutura

- `src/elas_ti/`: parsers, modelos, inferência, estatística, coortes e saídas.
- `tests/`: testes sintéticos e integração local opcional.
- `config.py`: configurações científicas e operacionais.
- `pdfs/`: documentos institucionais locais, não versionados.
- `cache/`: resultados persistentes locais do Genderize.
- `output/`: CSVs, relatórios e figuras locais.
- `.github/workflows/tests.yml`: testes sem API, chave ou PDFs privados.

## Execução completa

Após revisar a auditoria:

```sh
python main.py
python main.py --verbose
python main.py --validate
python main.py --no-api
python main.py --rebuild-reports
python main.py --match-cohorts
python main.py --dry-run --pdf-root caminho --output-dir caminho
```

| Opção | Comportamento |
|---|---|
| `--dry-run`, `--validate` | Somente extração e auditoria; não criam cache nem consultam API |
| sem opção | Valida, consulta nomes ausentes do cache e produz todas as análises |
| `--no-api` | Usa cache; nomes ausentes continuam não identificados |
| `--rebuild-reports` | Recria saídas do snapshot local, com os parâmetros originais, sem PDFs ou API |
| `--match-cohorts` | Executa análise incluindo coortes, usando somente cache |
| `--verbose` | Habilita log do projeto, sem log HTTP de URLs ou nomes |

Saída 0 indica execução concluída; 1 indica problemas de validação; 2 indica
falha operacional/configuração/API. Na ausência de PDFs, a auditoria informa
zero documentos. A execução completa gera saídas vazias explicitamente, sem
inventar resultados. Avisos de validação bloqueiam a análise completa até a
revisão dos PDFs. O dry-run só atualiza a auditoria; resultados de uma execução
anterior, se existirem, continuam correspondendo ao snapshot anterior.

`config.py` permite aliases de cursos, cursos de interesse, limiares de confiança,
país, modo `full`/`first`, tamanho de lote e acompanhamento mínimo. Sem filtro
mínimo nenhuma coorte é excluída. O acompanhamento usa o último período de
conclusão disponível **do curso**, além de informar o último período global;
sem relatório do curso fica vazio, e ingressos posteriores têm acompanhamento 0.
O filtro de cursos é aplicado depois da auditoria de todos os documentos.

## Inferência e cache

O cliente usa `country_id=BR` e lotes de até 100 nomes, conforme a
[referência oficial do Genderize](https://genderize.io/documentation/api/reference).
A chave vem de `GENDERIZE_API_KEY`, carregada do `.env` na raiz do projeto.
Timeout, conexão, JSON inválido e HTTP 429/500/502/503 têm até quatro tentativas,
com esperas de 1, 2 e 4 segundos. HTTP 401/402 interrompem imediatamente.
Redirecionamentos não são seguidos e corpos de erro não são impressos.

O cache `cache/genderize.sqlite` guarda resposta, nome consultado, país, modo e
instante UTC. A chave utiliza o nome consultado normalizado (maiúsculas com
acentos), país e modo. Em `first`, nomes completos com o mesmo primeiro nome
compartilham a consulta. Uma resposta nula válida também é armazenada. Não há
expiração automática; preserve o cache para reproduzir a análise e remova-o
localmente apenas se desejar novas consultas, que podem consumir cota.
O cache não é usado como identificador de pessoas.

## Metodologia estatística

Para resposta `female` com probabilidade `p`, `p_female=p`. Para `male`,
`p_female=1-p`. Nulos permanecem desconhecidos. A classificação auxiliar usa
alta confiança ≥0,90, moderada ≥0,75 e baixa abaixo de 0,75.

A estimativa principal usa `E[F]=Σq`, `E[M]=Σ(1-q)`,
`Var(F)=Σq(1-q)` e `SD(F)=√Var(F)`. Os percentuais principais são calculados
**entre os resolvidos**, com total, número não identificado e cobertura
separados. As expectativas também se referem apenas aos resolvidos.

A distribuição Poisson-binomial é calculada exatamente por programação dinâmica,
com tempo O(n²), memória O(n), sem SciPy. Os quantis discretos de 2,5% e 97,5%
formam o **intervalo probabilístico de incerteza de 95%**, sob independência dos
registros e condicionado às probabilidades do modelo. Não é intervalo de
confiança amostral clássico. Para os não identificados são fornecidos dois
conjuntos distintos de limites:

- Contagem: `[quantil inferior, quantil superior + não identificados]`.
- Expectativa percentual no total: `[E[F]/N, (E[F]+não identificados)/N] × 100`.

`monte_carlo_difference` em `elas_ti.statistics` é um recurso opcional para
comparar grupos independentes de probabilidades resolvidas. Usa 100.000
iterações e semente 42 por padrão e retorna percentis 2,5/50/97,5 da diferença
B−A em pontos percentuais: **intervalo de incerteza baseado no modelo**. Não é
executado automaticamente nas séries com possíveis pessoas compartilhadas,
nem deve ser aplicado a coortes sobrepostas sem modelar essa dependência.

As análises são separadas por tipo de registro, nos níveis global, curso, ano,
período, curso+ano e curso+período. A variação em pontos percentuais usa períodos
sucessivos disponíveis, sem preencher semestres ausentes. A comparação descritiva
no mesmo semestre não vincula ingresso e conclusão como uma coorte.

## Matching e limites de interpretação

Matching usa mesmo curso, chave normalizada do nome e conclusão posterior.
`exact_unique` exige unicidade nos dois sentidos: um ingressante com um candidato
e esse candidato com apenas um ingresso possível. Vários candidatos ou reingressos
concorrentes são `ambiguous`; sem candidatos, `not_found`. Nenhuma correspondência
fuzzy é contada; sugestões fuzzy não fazem parte desta versão.

O tempo é a diferença dos índices `2×ano + semestre−1`. Coortes são curso+período
de ingresso. A medida é a **proporção de ingressantes reencontrados posteriormente
nas listas de conclusão disponíveis**, e não taxa oficial de conclusão.

Gênero inferido a partir do nome não é gênero autodeclarado. Probabilidades não
são ground truth; não se calculam accuracy, precision, recall ou F1. O modelo
binário, vieses culturais, calibração desconhecida e dependência entre nomes
limitam as estimativas. PDFs ausentes, homônimos, reingressos, transferências,
mudanças de nome/curso e coortes em andamento limitam o matching. Mesmo
`exact_unique` não constitui verificação externa de identidade.

## Saídas e reprodutibilidade

`output/csv/` contém registros classificados (com `record_id` usado no matching),
auditoria, casos para revisão, resumos em todos os agrupamentos, comparação,
coortes e tempo até conclusão. Os nomes de arquivo principais seguem:

- `registros_classificados.csv`, `documentos_processados.csv`, `casos_para_revisao.csv`;
- `resumo_ingressantes_periodo.csv`, `resumo_concluintes_periodo.csv`;
- `resumo_ingressantes_curso_periodo.csv`, `resumo_concluintes_curso_periodo.csv`;
- `comparacao_ingressantes_concluintes.csv`, `cohort_matches.csv`, `resumo_coortes.csv`.

`output/reports/` guarda `validacao_pdfs.txt` e `relatorio_elas_ti.txt` (dez seções).
`output/figures/` guarda três PNGs acadêmicos, sem dados pessoais. O eixo X mantém
as distâncias cronológicas; linhas só conectam observações disponíveis.

`output/registros_snapshot.json` guarda registros, auditoria, configurações,
hashes SHA-256 dos PDFs e data da execução. **Contém nomes e é exclusivamente
local**. `--rebuild-reports` usa esse snapshot. Um `.gitignore` também é criado
no diretório de saída personalizado. Não direcione saídas para a raiz do código.
Os dados locais não são criptografados pelo programa: proteja o armazenamento
e as cópias de segurança com os controles institucionais de acesso.

Os parsers suportam nomes em maiúsculas e linhas tabulares com campos na mesma
linha de texto extraída. Layouts com quebras de linha/células não reconhecidas
são sinalizados para adaptação. Não houve validação dos PDFs institucionais
originais no desenvolvimento inicial: eles não estavam no diretório local.

```sh
pytest                 # Suíte normal e integração, quando houver PDFs
pytest -m integration  # Somente documentos institucionais locais
```

Os testes bloqueiam HTTP real automaticamente e geram PDFs sintéticos temporários.
O GitHub Actions testa Python 3.11 e 3.13 sem secrets. As dependências têm faixas
compatíveis em `requirements.txt`; o snapshot registra parâmetros científicos,
mas atualizações de bibliotecas podem alterar a renderização dos gráficos.

Para manutenção, instale `requirements-dev.txt` e execute
`ruff check main.py config.py src tests` e `ruff format --check main.py config.py src tests`.
O snapshot também registra a versão do Python e das dependências de análise.
