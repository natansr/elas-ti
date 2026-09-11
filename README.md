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
