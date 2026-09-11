"""Incerteza condicional ao modelo, com independência entre registros resolvidos."""
import math
from collections import defaultdict
from statistics import mean, median

import numpy as np

from .utils import period_index


def poisson_binomial(probabilities: list[float]) -> list[float]:
    pmf = [1.0]
    for q in probabilities:
        if not math.isfinite(q) or not 0 <= q <= 1:
            raise ValueError("Probabilidade fora de [0, 1]")
        next_pmf = [0.0] * (len(pmf) + 1)
        for k, mass in enumerate(pmf):
            next_pmf[k] += mass * (1 - q)
            next_pmf[k + 1] += mass * q
        pmf = next_pmf
    return pmf


def cdf(pmf: list[float]) -> list[float]:
    total, result = 0.0, []
    for mass in pmf:
        total += mass
        result.append(total)
    return result


def quantile(pmf: list[float], alpha: float) -> int:
    if not pmf or not 0 <= alpha <= 1:
        raise ValueError("Quantil inválido")
    for k, cumulative in enumerate(cdf(pmf)):
        if cumulative >= alpha:
            return k
    return len(pmf) - 1


def summarize(records: list) -> dict:
    q = [r.p_female for r in records if r.p_female is not None]
    n, resolved = len(records), len(q)
    unknown = n - resolved
    pmf = poisson_binomial(q)
    expected = sum(q)
    variance = sum(p * (1 - p) for p in q)
    lower, upper = quantile(pmf, .025), quantile(pmf, .975)
    probabilities = [r.genderize_probability for r in records if r.p_female is not None]
    counts = [r.genderize_count for r in records if r.p_female is not None and r.genderize_count is not None]
    probabilities = [p for p in probabilities if p is not None]
    return {
        "total": n, "resolvidos": resolved, "nao_identificados": unknown,
        "cobertura": resolved / n if n else None,
        "expected_female": expected, "expected_male": resolved - expected,
        "female_percent_resolved": 100 * expected / resolved if resolved else None,
        "male_percent_resolved": 100 * (resolved - expected) / resolved if resolved else None,
        "variance_female": variance, "sd_female": math.sqrt(variance),
        "interval95_lower_resolved": lower if resolved else None,
        "interval95_upper_resolved": upper if resolved else None,
        "conservative_count_lower": lower, "conservative_count_upper": upper + unknown,
        "conservative_percent_lower": 100 * lower / n if n else None,
        "conservative_percent_upper": 100 * (upper + unknown) / n if n else None,
        "expected_female_percent_total_min": 100 * expected / n if n else None,
        "expected_female_percent_total_max": 100 * (expected + unknown) / n if n else None,
        "alta_confianca": sum(r.confidence_class == "alta confiança" for r in records),
        "moderada": sum(r.confidence_class == "confiança moderada" for r in records),
        "baixa": sum(r.confidence_class == "baixa confiança" for r in records),
        "probability_media": mean(probabilities) if probabilities else None,
        "probability_mediana": median(probabilities) if probabilities else None,
        "count_medio": mean(counts) if counts else None,
        "count_mediano": median(counts) if counts else None,
    }


def grouped_summary(records: list, fields: tuple[str, ...]) -> list[dict]:
    groups = defaultdict(list)
    for r in records:
        groups[tuple(getattr(r, f) for f in fields)].append(r)
    if not fields and not records:
        groups[()] = []
    return [dict(zip(fields, key), **summarize(group)) for key, group in sorted(groups.items())]


def temporal_summary(records: list, by_course=False) -> list[dict]:
    fields = ("curso_normalizado", "periodo") if by_course else ("periodo",)
    rows = grouped_summary(records, fields)
    rows.sort(key=lambda row: (row.get("curso_normalizado", ""), period_index(row["periodo"])))
    previous = {}
    for row in rows:
        course = row.get("curso_normalizado", "")
        last = previous.get(course)
        value = row["female_percent_resolved"]
        row["variacao_pp"] = value - last if value is not None and last is not None else None
        previous[course] = value
    return rows


def compare_periods(entrants: list[dict], graduates: list[dict]) -> list[dict]:
    left, right = ({r["periodo"]: r for r in rows} for rows in (entrants, graduates))
    rows = []
    for period in sorted(left.keys() | right.keys(), key=period_index):
        a = left.get(period, {}).get("female_percent_resolved")
        b = right.get(period, {}).get("female_percent_resolved")
        rows.append({"periodo": period, "female_percent_entrants": a,
                     "female_percent_graduates": b,
                     "difference_pp_graduates_minus_entrants": b - a if a is not None and b is not None else None})
    return rows


def monte_carlo_difference(q_a: list[float], q_b: list[float], iterations=100000, seed=42) -> dict:
    """Comparação opcional de grupos independentes; não usar em coortes sobrepostas."""
    if iterations < 1:
        raise ValueError("Número de iterações inválido")
    poisson_binomial(q_a)
    poisson_binomial(q_b)
    if not q_a or not q_b:
        return {"p2_5": None, "p50": None, "p97_5": None}
    rng = np.random.default_rng(seed)
    # Memória O(iterações), sem matriz pessoas × iterações.
    def draws(q):
        totals = np.zeros(iterations)
        for p in q:
            totals += rng.binomial(1, p, iterations)
        return totals * 100 / len(q)
    difference = draws(q_b) - draws(q_a)
    values = np.quantile(difference, [.025, .5, .975])
    return dict(zip(("p2_5", "p50", "p97_5"), map(float, values)))
