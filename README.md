# ELAS-TI

Estudo Longitudinal da Participação Feminina no Ingresso e na Conclusão dos Cursos de Tecnologia da Informação

Software em Python para análise da participação feminina entre ingressantes e concluintes de cursos de Tecnologia da Informação. Desenvolvido por **Vitória Maria Diniz e Natan de S. Rodrigues**, no grupo de pesquisa **ANDSol/UEG**.

O [painel público](https://natansr.github.io/elas-ti/) apresenta os resultados do curso de Sistemas de Informação da **UEG/UnU Goianésia**, com dados fornecidos pela Secretaria Acadêmica da unidade. Há filtros, gráficos interativos, ajuda “?” e downloads em CSV e JSON.

## Instalação

Requisito: Python 3.11 ou superior. Na pasta do projeto, crie um ambiente para instalar as dependências:

```sh
python -m venv .venv
```

Ativação do ambiente:

```sh
# Linux e macOS
source .venv/bin/activate

# Windows — Prompt de Comando
.venv\Scripts\activate.bat
```

```sh
pip install -r requirements.txt
```

Para consultar o [Genderize.io](https://genderize.io/register), copie `.env.example` para `.env` e preencha sua chave pessoal:

```dotenv
GENDERIZE_API_KEY=sua_chave
```

A chave fica no computador e não é incluída no painel. As consultas enviam nomes ao Genderize.io, mas não os PDFs.

## Documentos e execução

| Pasta local | Conteúdo |
|---|---|
| `pdfs/ingressantes/` | PDFs ou `.7z` de ingressantes. |
| `pdfs/formandos/` | PDFs ou `.7z` de concluintes. |

Essas pastas são destinadas aos documentos privados e estão excluídas da publicação. Arquivos `.7z` são extraídos automaticamente para leitura, sem alterar os originais.

A execução completa extrai os registros, consulta o Genderize.io quando necessário, calcula as estatísticas e atualiza os arquivos do painel:

```sh
python main.py --update-site
```

| Comando | Finalidade |
|---|---|
| `python main.py --dry-run` | Validar a extração, sem API. |
| `python main.py --update-site --no-api` | Processar com as inferências já salvas, sem novas consultas ao serviço. |
| `python main.py --export-site` | Exportar a última análise salva, sem reler documentos. |
| `python main.py --graphs` | Abrir o menu local de gráficos Matplotlib. |
| `python main.py --rebuild-reports` | Reconstruir os relatórios locais da análise salva. |

O relatório de validação fica em `output/reports/validacao_pdfs.txt`. Falhas estruturais interrompem a análise. O programa exige PDFs com texto pesquisável no layout suportado e não realiza OCR. Configurações ficam em `config.py`; demais opções, em `python main.py --help`.

## Interpretação dos resultados

O [Genderize.io](https://genderize.io) fornece uma categoria e uma probabilidade associada ao nome, com contexto brasileiro. O ELAS-TI utiliza essa probabilidade como parâmetro do modelo; **não se trata de gênero autodeclarado nem de classificação confirmada**.

Para cada registro, a probabilidade feminina `q` é `p` quando a resposta é `female`, e `1 − p` quando é `male`. Por exemplo, uma resposta masculina com `p = 0,95` contribui com `0,05` para a quantidade feminina esperada.

| Medida | Cálculo |
|---|---|
| Quantidade feminina esperada | Soma de `q` nos registros com inferência. |
| Quantidade masculina esperada | Número de registros com inferência menos a soma de `q`. |
| Participação feminina (%) | `100 × soma(q) / registros com inferência`. |
| Cobertura (%) | `100 × registros com inferência / total de registros`. |
| Intervalo probabilístico de 95% | Quantis de 2,5% e 97,5% da distribuição Poisson-binomial, sob independência. |

Quantidades esperadas podem ser fracionárias. Registros sem inferência entram no total, mas ficam fora dos percentuais de gênero. **Cobertura de 100% não significa 100% de acerto.** O intervalo depende do modelo, não é um intervalo de confiança amostral e não incorpora todos os erros ou vieses do serviço.

Ingresso e conclusão abrangem grupos e períodos distintos. Diferenças entre seus percentuais são descritivas e não medem evasão, probabilidade de conclusão ou significância estatística. Fórmulas, resultados da execução e limitações estão em [Método e resultados](docs/METODOLOGIA.md).

## Painel público

Os arquivos públicos `site/data/resumo.json` e `resumo.csv` contêm os mesmos agregados. Há recortes por curso, ano e semestre: somar recortes sobrepostos duplica os totais. Campos vazios no CSV e `null` no JSON indicam indisponibilidade.

A prévia local fica em `http://localhost:8000` após:

```sh
python -m http.server 8000 --bind 127.0.0.1 --directory site
```

O painel pode ser consultado sem PDFs ou chave de API. Uma nova extração requer documentos próprios; novas inferências requerem uma chave pessoal. O serviço pode retornar probabilidades diferentes em consultas futuras.

O painel é publicado no GitHub Pages a partir da pasta `site/`. Apenas os gráficos e os dados agregados são públicos; documentos, chave de API e arquivos de processamento permanecem locais. Não coloque material privado na pasta `site/`.

Os resultados não contêm nomes ou identificadores individuais. Como incluem grupos pequenos, devem ser interpretados com cuidado ao cruzá-los com outras fontes de informação.

## Licença

Licença [GNU GPL versão 3 ou posterior](LICENSE) (`GPL-3.0-or-later`). Copyright (C) 2026 Vitória Maria Diniz e Natan de S. Rodrigues.
