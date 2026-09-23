from types import SimpleNamespace

import py7zr
import pytest
from test_parsers import ENTRANTS
from test_pipeline import make_pdf

from elas_ti.archive_input import ArchiveInputError, prepared_pdfs, validate_members
from main import main


def archive_file(path, files, **kwargs):
    with py7zr.SevenZipFile(path, "w", **kwargs) as archive:
        for name, data in files.items():
            archive.writestr(data, name)


def test_mixed_archive_pdf_deduplication_and_cleanup(tmp_path):
    root = tmp_path / "pdfs"
    root.mkdir()
    work = tmp_path / "output"
    work.mkdir()
    original = root / "original.pdf"
    original.write_bytes(b"original")
    archive_file(
        root / "documents.7Z",
        {
            "folder/copy.PDF": b"original",
            "folder/unique.pdf": b"new",
            "private.txt": b"PRIVATE",
        },
    )
    archive_file(root / "other.7z", {"copy.pdf": b"new"})
    with prepared_pdfs(root, work) as paths:
        assert len(paths) == 2
        assert sorted(p.read_bytes() for p in paths) == [b"new", b"original"]
        extracted = paths[1]
        assert extracted.stat().st_mode & 0o777 == 0o600
        assert not list(work.rglob("private.txt"))
    assert not extracted.exists()
    assert not list(work.iterdir())
    assert original.read_bytes() == b"original"
    # Reexecuções não acumulam PDFs antigos nem duplicam os totais.
    with prepared_pdfs(root, work) as paths:
        assert len(paths) == 2


def test_cleanup_on_parser_error(tmp_path):
    root = tmp_path / "pdfs"
    root.mkdir()
    work = tmp_path / "output"
    work.mkdir()
    archive_file(root / "archive.7z", {"a.pdf": b"pdf"})
    with pytest.raises(RuntimeError):
        with prepared_pdfs(root, work):
            raise RuntimeError("parse failure")
    assert not list(work.iterdir())


@pytest.mark.parametrize("kind", ["broken", "encrypted", "empty"])
def test_archive_errors_block_and_hide_names(tmp_path, capsys, kind):
    root = tmp_path / "pdfs"
    root.mkdir()
    archive = root / "PRIVATE_PERSON.7z"
    if kind == "broken":
        archive.write_bytes(b"broken")
    elif kind == "encrypted":
        archive_file(archive, {"PRIVATE_PERSON.pdf": b"secret"}, password="password")
    else:
        archive_file(archive, {"PRIVATE_PERSON.txt": b"secret"})
    output = tmp_path / "output"
    assert main(["--no-api", "--pdf-root", str(root), "--output-dir", str(output)]) == 2
    captured = capsys.readouterr()
    assert "PRIVATE_PERSON" not in captured.err + captured.out
    assert "Compactado 1" in captured.err
    assert not (output / "registros_snapshot.json").exists()
    assert not list(output.glob("extracao_7z_*"))


@pytest.mark.parametrize(
    "name",
    [
        "../escape.pdf",
        "/absolute.pdf",
        "C:/file.pdf",
        "folder/../../file.pdf",
        "folder\\file.pdf",
    ],
)
def test_rejects_unsafe_paths(name):
    member = SimpleNamespace(
        filename=name,
        is_file=True,
        is_directory=False,
        is_symlink=False,
        uncompressed=1,
    )
    with pytest.raises(ArchiveInputError):
        validate_members([member])


def test_rejects_links_collisions_and_oversized_archive():
    base = dict(
        filename="a.pdf",
        is_file=True,
        is_directory=False,
        is_symlink=False,
        uncompressed=1,
    )
    with pytest.raises(ArchiveInputError):
        validate_members(
            [SimpleNamespace(**(base | {"is_file": False, "is_symlink": True}))]
        )
    with pytest.raises(ArchiveInputError):
        validate_members(
            [SimpleNamespace(**base), SimpleNamespace(**(base | {"filename": "A.PDF"}))]
        )
    with pytest.raises(ArchiveInputError):
        validate_members([SimpleNamespace(**(base | {"uncompressed": 2**31}))])


def test_archive_pipeline_extracts_and_exports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    make_pdf(tmp_path / "source.pdf", ENTRANTS)
    root = tmp_path / "pdfs/ingressantes"
    root.mkdir(parents=True)
    archive_file(
        root / "archive.7z", {"folder/doc.pdf": (tmp_path / "source.pdf").read_bytes()}
    )
    assert main(["--no-api"]) == 0
    assert main(["--export-site"]) == 0
    assert not list((tmp_path / "output").glob("extracao_7z_*"))
    import json

    data = json.loads((tmp_path / "site/data/resumo.json").read_text())
    assert data["rows"][0]["total"] == 2
    assert "ANA TESTE" not in json.dumps(data)
