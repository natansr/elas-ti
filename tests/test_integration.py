from pathlib import Path

import pytest

from elas_ti.pdf_reader import discover_pdfs, read_pdf


@pytest.mark.integration
@pytest.mark.parametrize(
    "kind,period,expected",
    [
        ("ingressante", "2019/1", 44),
        ("ingressante", "2020/1", 30),
        ("concluinte", "2025/2", 3),
        ("concluinte", "2026/1", 2),
    ],
)
def test_local_pdfs(kind, period, expected):
    documents = [read_pdf(p) for p in discover_pdfs(Path("pdfs"))]
    matching = [
        d
        for d in documents
        if any(
            r.tipo_registro == kind
            and r.periodo == period
            and r.curso_normalizado == "SISTEMAS DE INFORMACAO"
            for r in d.records
        )
    ]
    if not matching:
        if any(d.status != "OK" for d in documents):
            pytest.fail("Há PDFs locais não validados; inspecione o dry-run.")
        pytest.skip("PDF institucional correspondente não disponível localmente")
    for doc in matching:
        assert doc.status == "OK"
        assert len([r for r in doc.records if r.periodo == period]) == expected
