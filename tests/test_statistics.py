from dataclasses import replace
from itertools import product

import pytest
from test_parsers import ENTRANTS

from elas_ti.ingressantes_parser import parse_ingressantes
from elas_ti.statistics import (
    cdf,
    compare_periods,
    monte_carlo_difference,
    poisson_binomial,
    quantile,
    summarize,
    temporal_summary,
)


def test_poisson_binomial_against_enumeration():
    probabilities = [0.2, 0.7, 0.9]
    expected = [0.0] * 4
    for outcomes in product((0, 1), repeat=3):
        mass = 1
        for outcome, q in zip(outcomes, probabilities):
            mass *= q if outcome else 1 - q
        expected[sum(outcomes)] += mass
    pmf = poisson_binomial(probabilities)
    assert pmf == pytest.approx(expected)
    assert sum(pmf) == pytest.approx(1)
    assert cdf(pmf)[-1] == pytest.approx(1)
    assert quantile(pmf, 0.025) == 1
    assert quantile(pmf, 0.975) == 3


def test_degenerate_and_empty():
    assert poisson_binomial([]) == [1]
    assert poisson_binomial([0, 1, 1]) == [0, 0, 1, 0]
    assert quantile([0, 0, 1], 0.975) == 2
    for bad in [-0.1, 1.1, float("nan")]:
        with pytest.raises(ValueError):
            poisson_binomial([bad])


def test_coverage_unknown_and_moments():
    records = parse_ingressantes([ENTRANTS]).records
    records[0].p_female = 0.8
    result = summarize(records)
    assert result["cobertura"] == 0.5
    assert result["expected_female"] == 0.8
    assert result["expected_male"] == pytest.approx(0.2)
    assert result["variance_female"] == pytest.approx(0.16)
    assert result["female_percent_resolved"] == 80
    assert result["expected_female_percent_total_min"] == 40
    assert result["expected_female_percent_total_max"] == 90
    assert summarize([])["cobertura"] is None
    assert summarize([records[1]])["female_percent_resolved"] is None
    assert summarize([records[1]])["conservative_percent_upper"] == 100


def test_temporal_missing_semesters():
    r = parse_ingressantes([ENTRANTS]).records[0]
    rows = temporal_summary(
        [replace(r, periodo="2020/2", p_female=0.6), replace(r, p_female=0.8)]
    )
    assert [row["periodo"] for row in rows] == ["2019/1", "2020/2"]
    assert rows[1]["variacao_pp"] == pytest.approx(-20)
    comparison = compare_periods(rows, [])
    assert all(r["difference_pp_graduates_minus_entrants"] is None for r in comparison)


def test_monte_carlo_seed_and_deterministic():
    assert monte_carlo_difference([0], [1], 100) == {
        "p2_5": 100.0,
        "p50": 100.0,
        "p97_5": 100.0,
    }
    assert monte_carlo_difference([0.4], [0.7], 1000) == monte_carlo_difference(
        [0.4], [0.7], 1000
    )
    assert monte_carlo_difference([], [0.7])["p50"] is None
