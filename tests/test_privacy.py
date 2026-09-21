import json
import sqlite3
from dataclasses import asdict

import pytest
from test_cohort_matching import records

from elas_ti.cache import GenderCache
from elas_ti.cohort_matching import match_cohorts
from elas_ti.models import StudentRecord
from elas_ti.privacy import load_snapshot, protect_summaries, pseudonymize_payload
from elas_ti.statistics import summarize


def test_snapshot_removes_names_paths_and_preserves_matches():
    data = records()
    result = pseudonymize_payload(
        {
            "records": [asdict(r) for r in data],
            "documents": [],
            "settings": {"API_SECRET": "sensitive", "COUNTRY_ID": "BR"},
        }
    )
    text = json.dumps(result)
    assert "ANA TESTE" not in text and "JOAO EXEMPLO" not in text
    assert "sintetico.pdf" not in text and "sensitive" not in text
    clean = [StudentRecord(**r) for r in result["records"]]
    assert [m["status"] for m in match_cohorts(clean)] == [
        m["status"] for m in match_cohorts(data)
    ]
    assert all(r.numero_sequencial == 0 and r.nome_normalizado == "" for r in clean)
    other = pseudonymize_payload({"records": [asdict(r) for r in data]})
    assert result["records"][0]["nome_chave"] != other["records"][0]["nome_chave"]


def test_old_snapshot_migrates_and_removes_individual_exports(tmp_path):
    path = tmp_path / "registros_snapshot.json"
    path.write_text(
        json.dumps({"schema_version": 1, "records": [asdict(r) for r in records()]})
    )
    (tmp_path / "csv").mkdir()
    private_csv = tmp_path / "csv/registros_classificados.csv"
    private_csv.write_text("ANA TESTE SILVA")
    assert load_snapshot(tmp_path)["schema_version"] == 2
    assert "ANA TESTE" not in path.read_text()
    assert not private_csv.exists()


def test_cache_migration_removes_plaintext_and_keeps_response(tmp_path):
    path = tmp_path / "cache.sqlite"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE predictions (name TEXT, country TEXT, mode TEXT, response TEXT, PRIMARY KEY(name,country,mode))"
    )
    response = {
        "name": "ANA TESTE SILVA",
        "nome_consultado": "ANA TESTE SILVA",
        "gender": "female",
        "probability": 0.9,
        "count": 10,
    }
    conn.execute(
        "INSERT INTO predictions VALUES (?,?,?,?)",
        ("ANA TESTE SILVA", "BR", "full", json.dumps(response)),
    )
    conn.commit()
    conn.close()
    with GenderCache(path) as cache:
        assert cache.get("ANA TESTE SILVA", "BR", "full")["probability"] == 0.9
    assert b"ANA TESTE SILVA" not in path.read_bytes()
    with GenderCache(path) as cache:
        assert cache.get("ANA TESTE SILVA", "BR", "full")["gender"] == "female"
    path.with_suffix(".key").unlink()
    with pytest.raises(ValueError):
        GenderCache(path)


def test_small_group_suppressed_and_large_counts_retained():
    row = summarize(records())
    assert protect_summaries([row], 5)[0]["total"] is None
    data = records() * 3
    data[0].p_female = 0.9
    row = protect_summaries([summarize(data)], 5)[0]
    assert row["total"] == 9
    assert row["female_percent_resolved"] is None


def test_temporal_change_cannot_reveal_suppressed_previous_group():
    rows = [
        {
            "periodo": "2019/1",
            "total": 3,
            "resolvidos": 3,
            "female_percent_resolved": 80,
            "variacao_pp": None,
        },
        {
            "periodo": "2020/1",
            "total": 10,
            "resolvidos": 10,
            "female_percent_resolved": 60,
            "variacao_pp": -20,
        },
    ]
    safe = protect_summaries(rows)
    assert safe[0]["female_percent_resolved"] is None
    assert safe[1]["variacao_pp"] is None


def test_publication_guard_paths():
    from scripts.check_publication import blocked_path

    assert blocked_path("pdfs/ingressantes/ARQUIVO.PdF")
    assert blocked_path("cache/genderize.key")
    assert blocked_path("output/snapshot.json")
    assert blocked_path(".env.production")
    assert not blocked_path(".env.example")
    assert not blocked_path("tests/test_privacy.py")
