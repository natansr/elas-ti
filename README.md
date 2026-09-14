# ELAS-TI

**Estudo Longitudinal da Participação Feminina no Ingresso e na Conclusão dos Cursos de Tecnologia da Informação**

Projeto de pesquisa da **Universidade Estadual de Goiás — Unidade Universitária de Goianésia**. Analisa relatórios institucionais em PDF para estimar a participação feminina e acompanhar correspondências entre listas de ingresso e conclusão.

Extrai e valida registros, remove repetições e gera tabelas e gráficos por curso e período. Usa o Genderize.io: **gênero inferido pelo nome não representa gênero autodeclarado**.

## Instalação

Requer **Python 3.11 ou superior**. Na pasta do projeto:

```sh
python -m venv .venv
```

Ative o ambiente com `source .venv/bin/activate` no Linux/macOS ou `.venv\Scripts\activate` no Windows. Depois:

```sh
pip install -r requirements.txt
```

Para usar o Genderize, copie `.env.example` para `.env` e preencha `GENDERIZE_API_KEY` com sua chave. Sem chave, use `--no-api` para trabalhar apenas com o cache local.

## Como usar

**1. Coloque os PDFs nas pastas correspondentes:**

```text
pdfs/
├── ingressantes/
└── formandos/
```

**2. Valide a extração antes de analisar:**

```sh
python main.py --dry-run
```

Confira `output/reports/validacao_pdfs.txt`. O dry-run não consulta a API. PDFs sem texto ou com layout não reconhecido exigem revisão; não há OCR automático.

**3. Gere as análises:**

```sh
python main.py
```

Somente nomes ausentes do cache são consultados. Falhas de extração bloqueiam a análise; homônimos são preservados para revisão.

| Opção | Uso |
|---|---|
| `--no-api` | Gera análises com o cache; nomes sem resposta continuam não identificados. |
| `--rebuild-reports` | Recria as saídas a partir dos dados e parâmetros salvos localmente, sem PDFs ou API. |
| `--match-cohorts` | Executa a análise, incluindo coortes, usando somente o cache. |
| `--pdf-root caminho`, `--output-dir caminho` | Define as pastas de entrada e saída. |

Configurações de cursos, inferência e acompanhamento ficam em `config.py`. Veja todas as opções com `python main.py --help`.

## Escolher gráficos no terminal

```sh
python main.py --graphs
```

O menu permite escolher **contagens, participação feminina, comparação ingresso × conclusão, cobertura, correspondência por coorte ou tempo até conclusão**. Selecione curso e período, linhas ou barras (coortes usam barras), e salve em **PNG, PDF ou SVG**. Você também pode abrir uma janela local do Matplotlib; nenhum navegador é necessário.

O menu lê a última análise salva, informa a data dos dados e não consulta a API. Para preparar ou atualizar as contagens, execute `python main.py --no-api`. Gráficos de participação feminina precisam de inferências salvas. Os filtros de coorte usam o período de **ingresso**, mantendo as conclusões posteriores no acompanhamento. As figuras ficam em `output/figures/`, com nomes únicos e notas sobre as métricas e seus intervalos.

## Estatísticas calculadas

Ingressantes e concluintes são analisados **separadamente**, nos níveis global, curso, ano, semestre, curso + ano e curso + semestre.

**N** = total de registros; **R** = registros com inferência (resolvidos); **U = N − R** = não identificados. **q** é a probabilidade feminina: `p` para resposta `female` e `1 − p` para `male`. Nulos não recebem 0,5.

| Métrica | Cálculo e interpretação |
|---|---|
| Contagens e cobertura | N, R e U após deduplicação; cobertura = `R / N` (de 0 a 1). |
| Número esperado de mulheres e homens | `E[F] = Σq` e `E[M] = R − E[F]`. São estimativas entre os resolvidos e podem ser fracionárias. |
| Participação feminina e masculina estimada | `100 × E[F] / R` e `100 × E[M] / R`. **O denominador é R, não N.** Sem resolvidos, ficam sem valor. |
| Variância e desvio padrão | `Var(F) = Σq(1 − q)` e `SD(F) = √Var(F)`: dispersão da contagem feminina sob o modelo. |
| Intervalo probabilístico de incerteza de 95% | Quantis de 2,5% e 97,5% da Poisson-binomial exata sobre os resolvidos. Expressos em número de mulheres; assumem independência entre registros. |
| Limites considerando não identificados | Para contagem: `[limite inferior do intervalo, limite superior + U]`; para percentual, divide-se por N e multiplica-se por 100. Os limites da **expectativa** no total são, separadamente, `[E[F]/N, (E[F]+U)/N] × 100`. |
| Indicadores auxiliares da API | Contagens por confiança: alta ≥0,90, moderada ≥0,75 e <0,90, baixa <0,75. Média/mediana de `probability` e `count` entre resolvidos; `count` é a base de observações da API, não estudantes. |

**Exemplo ilustrativo:** com 40 registros, 30 resolvidos e `E[F] = 12`, a cobertura é 75% e a participação feminina estimada **entre resolvidos** é 40%. Considerando os 10 não identificados, a expectativa feminina no total fica entre 30% e 55%.

A evolução temporal informa a variação em **pontos percentuais** entre períodos sucessivos disponíveis. A comparação no mesmo semestre calcula **percentual de concluintes − percentual de ingressantes**; isso não compara a mesma coorte. Semestres ausentes não são preenchidos.

O intervalo depende do modelo; **não é um intervalo de confiança amostral clássico**. A função opcional de Monte Carlo compara grupos independentes (100 mil simulações; percentis 2,5/50/97,5). Não integra a execução automática.

## Coortes e acompanhamento

Uma **coorte** reúne ingressantes do mesmo curso e semestre. O vínculo exige curso e nome normalizado iguais, conclusão posterior e unicidade nos dois sentidos. Os status são `exact_unique`, `ambiguous` e `not_found`; apenas o primeiro conta como correspondência única.

| Métrica | Significado |
|---|---|
| Tamanho e composição da coorte | Total de ingressantes e números esperados de mulheres/homens entre os resolvidos, na coorte e no subconjunto reencontrado. |
| Proporção de correspondência | Vínculos `exact_unique` divididos pelo total de ingressantes da coorte. |
| Tempo até conclusão | Diferença em semestres nos vínculos únicos; média, mediana, mínimo e máximo, no geral e por curso. Exemplo: 2019/1 → 2020/1 = 2 semestres. |
| Tempo de acompanhamento | Semestres entre o ingresso e a última lista de conclusão disponível do curso. Sem lista, fica vazio; se ela antecede o ingresso, vale zero. Por padrão, nenhuma coorte é excluída. |

Essa proporção mede **ingressantes reencontrados nas listas de conclusão disponíveis**, não a taxa oficial de conclusão. PDFs ausentes, mudanças de nome/curso, homônimos e coortes recentes limitam o resultado. Um vínculo por nome não confirma identidade.

## Resultados e privacidade

| Pasta | Conteúdo |
|---|---|
| `output/reports/` | Relatório principal (`relatorio_elas_ti.txt`) e auditoria dos PDFs (`validacao_pdfs.txt`). |
| `output/csv/` | Registros, resumos estatísticos, comparações, coortes e casos para revisão. |
| `output/figures/` | Gráficos de participação feminina no ingresso, na conclusão e na comparação das séries. |

O snapshot `output/registros_snapshot.json` permite reconstruir os relatórios. O dry-run atualiza apenas a auditoria, não análises anteriores.

**PDFs, `.env`, cache e saídas ficam fora do Git.** Relatórios agregados não listam nomes; CSVs detalhados e snapshot exigem acesso restrito. Apenas os nomes consultados são enviados ao Genderize, nunca os PDFs. Repositório privado, sem licença definida.

As estimativas estão sujeitas à cobertura, a vieses e à calibração do Genderize. O modelo binário não representa a diversidade de gênero.

## Desenvolvimento

O código está em `src/elas_ti/`, as configurações em `config.py` e os testes em `tests/`.

```sh
pytest
```

Os testes usam dados sintéticos e bloqueiam chamadas reais à API. As integrações com PDFs institucionais são executadas apenas quando os arquivos estão disponíveis localmente. O GitHub Actions executa a suíte sem chaves ou PDFs privados.
