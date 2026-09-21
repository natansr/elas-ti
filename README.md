# ELAS-TI

**Estudo Longitudinal da Participação Feminina no Ingresso e na Conclusão dos Cursos de Tecnologia da Informação**

Projeto de pesquisa da Universidade Estadual de Goiás — Unidade Universitária de Goianésia. Processa PDFs institucionais, valida os registros e produz estatísticas e gráficos locais com **Matplotlib**, sem interface web.

**A inferência probabilística é realizada pelo [Genderize.io](https://genderize.io).** Ela estima gênero a partir do nome; não representa gênero autodeclarado. O software não inventa respostas quando a API ou o cache não têm informação.

## Instalação

Requer **Python 3.11+**. Na pasta do projeto:

```sh
python -m venv .venv
```

Ative com `source .venv/bin/activate` no Linux/macOS ou `.venv\Scripts\activate` no Windows. Depois:

```sh
pip install -r requirements.txt
```

Para consultar a API, copie `.env.example` para `.env` e preencha `GENDERIZE_API_KEY`. A configuração padrão usa nomes completos e contexto brasileiro (`BR`). **Os nomes consultados são enviados ao Genderize.io; os PDFs nunca são enviados.** Use essa modalidade apenas com autorização para tratar e transmitir os dados.

## Uso em três passos

**1. Coloque os PDFs** em `pdfs/ingressantes/` e `pdfs/formandos/`.

**2. Valide os documentos e prepare os resultados:**

```sh
python main.py --dry-run  # Extrai e confere os totais, sem API
python main.py --no-api   # Gera análises usando apenas o cache local
```

Confira `output/reports/validacao_pdfs.txt`. PDFs sem texto ou layouts não reconhecidos exigem revisão; não há OCR automático. Para obter inferências ainda ausentes, após configurar a chave, execute `python main.py`.

**3. Escolha o gráfico:**

```sh
python main.py --graphs
```

O menu orienta a escolha de análise, curso, período e formato. Salva **PNG, PDF ou SVG** em `output/figures/` e permite abrir uma janela local do Matplotlib. Ele lê a última análise salva, mostra sua data e não faz chamadas à API.

| Gráfico | O que mostra |
|---|---|
| Quantidade de estudantes | Registros de ingresso ou conclusão por semestre, em linhas ou barras. |
| Participação feminina | Percentual estimado entre resolvidos, com intervalo probabilístico de 95%. |
| Ingresso × conclusão | Duas séries distintas; não representam a mesma coorte. |
| Cobertura | Percentual dos registros com inferência disponível. |
| Coortes e tempo até conclusão | Correspondências por coorte e tempo médio dos vínculos únicos. |
| **Pizza feminina × masculina** | Composição estimada entre resolvidos no período selecionado, com cobertura indicada. |
| **Barras femininas × masculinas por ano** | Percentuais anuais, calculados sobre todos os registros resolvidos do ano. |

Pizza e barras anuais analisam ingresso **ou** conclusão separadamente. Não identificados ficam fora dos percentuais e não são contados como homens. Sem inferências suficientes, o programa explica por que não pode gerar o gráfico. A pizza não exibe a incerteza: use o gráfico de participação feminina para isso.

## Entenda as métricas

**N** = total; **R** = registros com inferência; **U = N − R** = não identificados. Para cada resolvido, **q** é a probabilidade feminina: `p` para resposta `female`, `1 − p` para `male`.

| Métrica | Cálculo e interpretação |
|---|---|
| Cobertura | `R / N` (fração nos CSVs; percentual nos gráficos). |
| Quantidades esperadas | Mulheres: `Σq`; homens: `R − Σq`. Podem ser fracionárias. |
| Percentuais estimados | Quantidade esperada dividida por **R**, multiplicada por 100. |
| Variância e desvio padrão | `Σq(1 − q)` e sua raiz quadrada, para a contagem feminina. |
| Incerteza de 95% | Quantis 2,5% e 97,5% da Poisson-binomial exata, sob independência. Não é intervalo de confiança amostral clássico. |
| Limites com não identificados | Contagem: `[quantil inferior, quantil superior + U]`. Expectativa percentual no total: `[Σq/N, (Σq+U)/N] × 100`. |
| Evolução temporal | Diferença em pontos percentuais entre períodos disponíveis; sem imputar períodos ausentes. |

**Exemplo fictício:** N=40, R=30 e quantidade feminina esperada=12 → cobertura de 75%, participação feminina de 40% entre resolvidos e expectativa feminina entre 30% e 55% no total.

Também são calculadas médias/medianas de `probability` e `count` da API e contagens de confiança alta (≥0,90), moderada (≥0,75 e <0,90) e baixa (<0,75). `count` se refere às observações da API, não a estudantes.

Uma **coorte** é curso + período de ingresso. O vínculo exige nome normalizado e curso iguais, conclusão posterior e unicidade nos dois sentidos. A proporção de vínculos mede **ingressantes reencontrados nas listas disponíveis**, não taxa oficial de conclusão. O tempo é medido em semestres. Filtros de coorte selecionam ingressos e preservam conclusões posteriores.

## Privacidade e resultados

- **Não são gerados CSVs individuais:** as saídas são resumos em `output/csv/`, relatórios em `output/reports/` e figuras em `output/figures/`. Auditorias não exibem nomes de estudantes nem nomes/caminhos dos PDFs.
- O snapshot local usa identificadores aleatórios, sem nomes, números de sequência, turno ou modalidade de ingresso. O cache usa índices HMAC e respostas sem nomes em texto claro. **São dados pseudonimizados e continuam privados**, assim como a chave local do cache.
- Por padrão, gráficos e resumos suprimem grupos menores que **5** e estimativas com poucos resolvidos. A auditoria local mantém contagens para conferir a extração. Supressão não garante anonimato: grupos e cruzamentos ainda podem permitir reidentificação.
- PDFs, `.env`, cache, chaves e toda a pasta `output/` ficam fora do Git. **Publique o código, não os dados locais.** Revise qualquer resultado antes de compartilhá-lo.

Ao regenerar análises, as antigas exportações individuais são removidas. Snapshots antigos são migrados ao abrir os gráficos ou reconstruir relatórios; o cache é migrado ao ser aberto. Isso não remove cópias externas ou backups. O Genderize é um modelo binário sujeito a vieses e não representa a diversidade de gênero.

## Configuração e manutenção

`config.py` define cursos, inferência, acompanhamento e `MIN_GROUP_SIZE` (padrão 5). Reduzir esse limite diminui a proteção. `--rebuild-reports` reconstrói relatórios do snapshot local; `--pdf-root` e `--output-dir` alteram as pastas. Veja outras opções em `python main.py --help`.

```sh
pytest
python scripts/check_publication.py --history
```

Os testes usam dados sintéticos e bloqueiam HTTP real; integrações institucionais só rodam com PDFs locais. O GitHub Actions verifica testes e possíveis arquivos privados/credenciais no histórico. Essa verificação preventiva não substitui revisão humana. A visibilidade do repositório não é alterada pelo programa. Ainda não há licença definida.
