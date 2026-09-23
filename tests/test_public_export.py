import copy
import csv
import json
from dataclasses import asdict, replace

import pytest
from test_parsers import ENTRANTS

from elas_ti.ingressantes_parser import parse_ingressantes
from elas_ti.public_export import public_rows
from elas_ti.public_schema import (
    FIELDS,
    validate_csv,
    validate_data,
    validate_directory,
)
from main import main


def fixture_records():
    r = parse_ingressantes([ENTRANTS]).records[0]
    return [
        replace(r, p_female=0.8),
        replace(r, periodo="2019/2", semestre=2, p_female=0.2),
        replace(r, periodo="2019/2", semestre=2, p_female=None),
    ]


def payload(rows):
    return {
        "schema_version": 1,
        "generated_at": "2026-09-23",
        "analysis_at": "2026-09-23",
        "rows": rows,
    }


def test_public_aggregation_preserves_small_groups_and_uncertainty():
    rows = public_rows(fixture_records())
    validate_data(payload(rows))
    annual = next(
        r for r in rows if r["agrupamento"] == "ano" and r["curso"] == "Todos os cursos"
    )
    assert annual["total"] == 3
    assert annual["resolvidos"] == 2
    assert annual["nao_identificados"] == 1
    assert annual["expected_female"] == 1
    assert annual["female_percent_resolved"] == 50
    assert annual["cobertura"] == pytest.approx(2 / 3)
    assert annual["variance_female"] == pytest.approx(0.32)
    assert (
        annual["interval95_lower_resolved"],
        annual["interval95_upper_resolved"],
    ) == (0, 2)
    assert any(r["total"] == 1 for r in rows)
    assert all(set(r) == set(FIELDS) for r in rows)
    encoded = json.dumps(rows)
    for key in (
        "nome_original",
        "nome_chave",
        "arquivo",
        "pagina",
        "genderize_probability",
        "records",
    ):
        assert key not in encoded


def test_cli_export_offline_and_no_identifiers(tmp_path):
    source = tmp_path / "output"
    source.mkdir()
    private = [asdict(r) for r in fixture_records()]
    (source / "registros_snapshot.json").write_text(
        json.dumps(
            {"schema_version": 2, "created_at": "2026-09-23", "records": private}
        )
    )
    destination = tmp_path / "site/data"
    assert (
        main(
            [
                "--export-site",
                "--output-dir",
                str(source),
                "--site-data-dir",
                str(destination),
            ]
        )
        == 0
    )
    assert validate_directory(destination.parent) == 6
    text = (destination / "resumo.json").read_text()
    for record in private:
        assert record["nome_original"] not in text
        assert record["nome_chave"] not in text
    data = json.loads(text)
    csv_text = (destination / "resumo.csv").read_text(encoding="utf-8-sig")
    validate_csv(csv_text, data)
    with (destination / "resumo.csv").open(encoding="utf-8-sig") as stream:
        assert len(list(csv.DictReader(stream))) == len(data["rows"])
    altered = copy.deepcopy(data)
    altered["rows"] = []
    with pytest.raises(ValueError, match="divergentes"):
        validate_csv(csv_text, altered)
    (destination / "private.pdf").write_bytes(b"not a PDF")
    with pytest.raises(ValueError, match="inesperado"):
        validate_directory(destination.parent)


@pytest.mark.parametrize(
    "field,value",
    [
        ("nome", "PRIVATE"),
        ("total", -1),
        ("resolvidos", 4),
        ("cobertura", 0.1),
        ("female_percent_resolved", 99),
        ("curso", "=FORMULA()"),
        ("periodo", "a.pdf"),
        ("variance_female", float("nan")),
    ],
)
def test_rejects_unsafe_or_inconsistent_public_data(field, value):
    rows = public_rows(fixture_records())
    rows[0][field] = value
    with pytest.raises(ValueError):
        validate_data(payload(rows))


def test_unknown_is_not_male_or_zero_percent():
    records = [replace(fixture_records()[0], p_female=None)]
    data = payload(public_rows(records))
    validate_data(data)
    for row in data["rows"]:
        assert row["total"] == row["nao_identificados"] == 1
        assert row["female_percent_resolved"] is None
        assert row["male_percent_resolved"] is None
        assert row["interval95_lower_resolved"] is None


def test_missing_snapshot_does_not_overwrite_public_data(tmp_path):
    destination = tmp_path / "site/data"
    destination.mkdir(parents=True)
    target = destination / "resumo.json"
    target.write_text("previous")
    assert (
        main(
            [
                "--export-site",
                "--output-dir",
                str(tmp_path / "missing"),
                "--site-data-dir",
                str(destination),
            ]
        )
        == 2
    )
    assert target.read_text() == "previous"


def test_rejects_extra_csv_cells():
    import io

    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerow(public_rows(fixture_records())[0])
    malformed = stream.getvalue().rstrip() + ",PRIVATE_NAME\n"
    with pytest.raises(ValueError, match="colunas"):
        validate_csv(malformed)
