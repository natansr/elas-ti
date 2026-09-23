# ELAS-TI

Software em Python para análise da participação feminina entre ingressantes e concluintes de cursos de Tecnologia da Informação. Desenvolvido por **Vitória Maria Diniz e Natan S. Rodrigues**, no grupo de pesquisa **ANDSol/UEG**.

O [painel público](https://natansr.github.io/elas-ti/) apresenta os resultados do curso de Sistemas de Informação da **UEG/UnU Goianésia**, com dados fornecidos pela Secretaria Acadêmica da unidade. Há filtros, gráficos interativos, ajuda “?” e downloads em CSV e JSON.

## Instalação

Python 3.11 ou superior, na pasta do projeto:

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

Cada pessoa utiliza sua própria [chave do Genderize.io](https://genderize.io/register), no arquivo local `.env`:

```dotenv
GENDERIZE_API_KEY=sua_chave
```

O `.env` é ignorado pelo Git. A consulta envia os nomes ao Genderize.io; os PDFs permanecem no computador. Nenhuma chave é incluída no painel.

## Documentos e execução

| Pasta local | Conteúdo |
|---|---|
| `pdfs/ingressantes/` | PDFs ou `.7z` de ingressantes. |
| `pdfs/formandos/` | PDFs ou `.7z` de concluintes. |

Todo o conteúdo dessas pastas fica fora do Git, exceto os marcadores vazios `.gitkeep`. Os `.7z` são descompactados automaticamente em uma pasta temporária privada, removida após a leitura. Os originais são preservados.

A execução completa extrai os registros, consulta o Genderize.io quando necessário, calcula as estatísticas e atualiza os arquivos do painel:

```sh
python main.py --update-site
```

| Comando | Finalidade |
|---|---|
| `python main.py --dry-run` | Validar a extração, sem API. |
| `python main.py --update-site --no-api` | Processar somente com as inferências existentes no cache. |
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

## Painel e reprodução

Os arquivos públicos `site/data/resumo.json` e `resumo.csv` contêm os mesmos agregados. Há recortes por curso, ano e semestre: somar recortes sobrepostos duplica os totais. Campos vazios no CSV e `null` no JSON indicam indisponibilidade.

A prévia local fica em `http://localhost:8000` após:

```sh
python -m http.server 8000 --bind 127.0.0.1 --directory site
```

O painel pode ser consultado sem PDFs ou chave de API. Uma nova extração requer documentos próprios; novas inferências requerem uma chave pessoal. O serviço pode retornar probabilidades diferentes em consultas futuras.

O push de alterações em `site/` para a `main` publica o painel via GitHub Actions. Apenas `site/` é enviada ao Pages. PDFs, `.7z`, `.env`, cache e `output/` permanecem locais. O site publica números agregados, inclusive de grupos pequenos, sem nomes ou identificadores individuais; isso não garante anonimato absoluto.

## Verificação e licença

```sh
pytest
python scripts/check_publication.py --history
python scripts/validate_public_data.py
```

Os testes utilizam dados sintéticos e bloqueiam chamadas reais à API. A verificação do Git busca arquivos privados e possíveis credenciais, sem substituir a revisão do material publicado.

Licença [GNU GPL versão 3 ou posterior](LICENSE) (`GPL-3.0-or-later`). Copyright (C) 2026 Vitória Maria Diniz e Natan S. Rodrigues.
