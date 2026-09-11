import pymupdf
from test_parsers import ENTRANTS

from elas_ti.pdf_reader import read_pdf


def test_searchable_pdf(tmp_path):
    path = tmp_path / "nome_arbitrario.pdf"
    with pymupdf.open() as doc:
        for _ in range(2):
            page = doc.new_page()
            page.insert_text((30, 40), ENTRANTS, fontsize=10)
        doc.save(path)
    result = read_pdf(path)
    assert result.status == "OK"
    assert result.registros_unicos == 2
    assert result.duplicacoes_removidas == 2


def test_corrupt_pdf(tmp_path):
    path = tmp_path / "corrupt.pdf"
    path.write_bytes(b"invalid")
    assert read_pdf(path).status == "WARNING"


def test_image_only_pdf(tmp_path):
    path = tmp_path / "scan.pdf"
    with pymupdf.open() as doc:
        doc.new_page()
        doc.save(path)
    assert read_pdf(path).needs_ocr


def test_dry_run(tmp_path, capsys):
    from main import main

    assert (
        main(
            [
                "--dry-run",
                "--pdf-root",
                str(tmp_path),
                "--output-dir",
                str(tmp_path / "output"),
            ]
        )
        == 0
    )
    assert "Nenhum PDF" in capsys.readouterr().out
    assert (tmp_path / "output/reports/validacao_pdfs.txt").exists()
