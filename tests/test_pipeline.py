import csv
import json

import pymupdf
from test_parsers import ENTRANTS, GRADS

from main import main


def make_pdf(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as doc:
        doc.new_page().insert_text((30, 40), text, fontsize=10)
        doc.save(path)


def test_offline_pipeline_rebuild_and_privacy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_pdf(tmp_path / "pdfs/a.pdf", ENTRANTS)
    make_pdf(tmp_path / "pdfs/b.pdf", GRADS)
    assert main(["--no-api"]) == 0
    report = (tmp_path / "output/reports/relatorio_elas_ti.txt").read_text()
    assert "ANA TESTE" not in report
    assert "JOAO EXEMPLO" not in report
    assert "10. Limitações" in report
    with (tmp_path / "output/csv/resumo_coortes.csv").open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert float(rows[0]["match_proportion"]) == 0.5
    assert len(list((tmp_path / "output/figures").glob("*.png"))) == 3
    snapshot = json.loads((tmp_path / "output/registros_snapshot.json").read_text())
    assert len(snapshot["records"]) == 3
    assert all(r["p_female"] is None for r in snapshot["records"])
    # Reconstrução não exige PDFs; preserva dados e parâmetros do snapshot.
    for p in (tmp_path / "pdfs").glob("*.pdf"):
        p.unlink()
    assert main(["--rebuild-reports"]) == 0
    assert (tmp_path / "output/reports/relatorio_elas_ti.txt").read_text() == report


def test_duplicate_documents_block_analysis(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_pdf(tmp_path / "pdfs/a.pdf", ENTRANTS)
    make_pdf(tmp_path / "pdfs/b.pdf", ENTRANTS)
    assert main(["--no-api"]) == 1
    assert not (tmp_path / "output/registros_snapshot.json").exists()
    assert (
        "sobreposição" in (tmp_path / "output/reports/validacao_pdfs.txt").read_text()
    )


def test_dry_run_and_validate_do_not_create_cache(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_pdf(tmp_path / "pdfs/a.pdf", ENTRANTS)
    assert main(["--dry-run"]) == 0
    assert main(["--validate"]) == 0
    assert not (tmp_path / "cache").exists()


def test_missing_key_is_sanitized(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GENDERIZE_API_KEY", raising=False)
    monkeypatch.setattr("elas_ti.pipeline.load_dotenv", lambda *a: None)
    make_pdf(tmp_path / "pdfs/a.pdf", ENTRANTS)
    assert main([]) == 2
    assert "GENDERIZE_API_KEY ausente" in capsys.readouterr().err


def test_nonempty_output_ignore_is_not_overwritten(tmp_path):
    import pytest

    from elas_ti.pipeline import protect_output

    marker = tmp_path / ".gitignore"
    marker.write_text("*.tmp\n")
    with pytest.raises(ValueError):
        protect_output(tmp_path)
    assert marker.read_text() == "*.tmp\n"
