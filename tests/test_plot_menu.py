import json
from dataclasses import asdict

import pytest
from test_cohort_matching import records as synthetic_records

from elas_ti.plot_menu import choose, prepare_chart, render_chart, run_menu
from main import main


def test_counts_preserve_missing_periods():
    chart = prepare_chart(synthetic_records(), "1")
    assert chart["labels"] == ["2019/1", "2025/2"]
    assert chart["series"][0]["values"] == [2, None]
    assert chart["series"][1]["values"] == [None, 1]
    assert chart["x"][1] - chart["x"][0] == 13


def test_filters_and_unknown_probabilities():
    data = synthetic_records()
    chart = prepare_chart(data, "1", start="2025/2", kind="concluinte")
    assert chart["series"][0]["values"] == [1]
    chart = prepare_chart(data, "2", kind="ingressante")
    assert chart["series"][0]["values"] == [None]
    chart = prepare_chart(data, "4", kind="ingressante")
    assert chart["series"][0]["values"] == [0]
    assert prepare_chart(data, "1", course="CURSO AUSENTE")["labels"] == []


def test_cohort_window_retains_later_graduates():
    chart = prepare_chart(synthetic_records(), "5", start="2019/1", end="2019/1")
    assert chart["series"][0]["values"] == [50]
    assert "2019/1: 13" in chart["note"]
    chart = prepare_chart(synthetic_records(), "6", start="2019/1", end="2019/1")
    assert chart["series"][0]["values"] == [13]
    assert chart["series"][0]["lower"] == [13]


def test_probability_interval_and_denominator():
    data = synthetic_records()
    data[0].p_female = 0.8
    chart = prepare_chart(data, "2", kind="ingressante")
    assert chart["series"][0]["values"] == [80]
    assert chart["series"][0]["lower"] == [0]
    assert chart["series"][0]["upper"] == [100]
    assert prepare_chart(data, "4", kind="ingressante")["series"][0]["values"] == [50]


@pytest.mark.parametrize("extension", ["png", "pdf", "svg"])
def test_export_formats_without_personal_names(tmp_path, extension):
    chart = prepare_chart(synthetic_records(), "1")
    fig = render_chart(chart, "bar")
    path = tmp_path / f"chart.{extension}"
    fig.savefig(path)
    assert path.stat().st_size > 1000
    assert all(
        "ANA" not in t.get_text() for t in fig.findobj() if hasattr(t, "get_text")
    )


def test_menu_saves_chart_and_exits(tmp_path, monkeypatch, capsys):
    (tmp_path / "registros_snapshot.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "records": [asdict(r) for r in synthetic_records()],
                "created_at": "data sintética",
            }
        )
    )
    answers = iter(["1", "0", "0", "1", "2", "2", "1", "1", "0"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert run_menu(tmp_path) == 0
    assert len(list((tmp_path / "figures").glob("*.png"))) == 1
    output = capsys.readouterr().out
    assert "Gráfico salvo" in output
    assert "ANA TESTE" not in output


def test_cli_missing_snapshot_and_cancel(tmp_path, monkeypatch):
    assert main(["--graphs", "--output-dir", str(tmp_path)]) == 1
    answers = iter(["invalid", "1"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert choose("teste", {"1": "Continuar"}) == "1"


def test_inverted_period_rejected():
    with pytest.raises(ValueError):
        prepare_chart(synthetic_records(), "1", start="2025/2", end="2019/1")
