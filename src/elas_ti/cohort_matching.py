from collections import defaultdict
from statistics import mean, median

from .utils import period_index, semester_difference


def match_cohorts(records: list) -> list[dict]:
    entrants = [(i, r) for i, r in enumerate(records) if r.tipo_registro == "ingressante"]
    graduates = [(i, r) for i, r in enumerate(records) if r.tipo_registro == "concluinte"]
    candidates, reverse = defaultdict(list), defaultdict(list)
    index = defaultdict(list)
    for j, g in graduates:
        index[(g.curso_normalizado, g.nome_chave)].append((j, g))
    for i, e in entrants:
        for j, g in index[(e.curso_normalizado, e.nome_chave)]:
            if period_index(g.periodo) > period_index(e.periodo):
                candidates[i].append(j)
                reverse[j].append(i)
    matches = []
    for i, e in entrants:
        options = candidates[i]
        exact = len(options) == 1 and len(reverse[options[0]]) == 1
        j = options[0] if exact else None
        matches.append({
            "entrant_id": i, "graduate_id": j,
            "status": "exact_unique" if exact else "ambiguous" if options else "not_found",
            "candidate_ids": ";".join(map(str, options)),
            "curso_normalizado": e.curso_normalizado, "periodo_ingresso": e.periodo,
            "periodo_conclusao": records[j].periodo if exact else None,
            "semesters_to_graduation": semester_difference(e.periodo, records[j].periodo) if exact else None,
        })
    return matches


def summarize_cohorts(records: list, matches: list[dict], min_followup=None) -> list[dict]:
    grads = [r for r in records if r.tipo_registro == "concluinte"]
    latest = max((r.periodo for r in grads), key=period_index, default=None)
    latest_course = {}
    for g in grads:
        course = g.curso_normalizado
        if course not in latest_course or period_index(g.periodo) > period_index(latest_course[course]):
            latest_course[course] = g.periodo
    groups = defaultdict(list)
    for match in matches:
        groups[(match["curso_normalizado"], match["periodo_ingresso"])].append(match)
    rows = []
    for (course, period), group in sorted(groups.items()):
        entrants = [records[m["entrant_id"]] for m in group]
        matched = [records[m["entrant_id"]] for m in group if m["status"] == "exact_unique"]
        last_course = latest_course.get(course)
        followup = max(0, semester_difference(period, last_course)) if last_course else None
        if min_followup is not None and (followup is None or followup < min_followup):
            continue
        rows.append({
            "curso_normalizado": course, "periodo_ingresso": period,
            "n_ingressantes": len(entrants),
            "resolved_entrants": sum(r.p_female is not None for r in entrants),
            "expected_female_entrants": sum(r.p_female for r in entrants if r.p_female is not None),
            "expected_male_entrants": sum(r.p_male for r in entrants if r.p_male is not None),
            "n_matches_exact_unique": len(matched),
            "resolved_matched": sum(r.p_female is not None for r in matched),
            "expected_female_matched": sum(r.p_female for r in matched if r.p_female is not None),
            "expected_male_matched": sum(r.p_male for r in matched if r.p_male is not None),
            "latest_graduation_period": latest, "latest_graduation_period_course": last_course,
            "followup_semesters": followup,
            "match_proportion": len(matched) / len(entrants),
        })
    return rows


def time_summary(matches: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    groups["global"] = []
    for match in matches:
        if match["status"] == "exact_unique":
            duration = match["semesters_to_graduation"]
            groups["global"].append(duration)
            groups[match["curso_normalizado"]].append(duration)
    return [{"grupo": group, "n": len(values), "media_semestres": mean(values) if values else None,
             "mediana_semestres": median(values) if values else None,
             "min_semestres": min(values) if values else None,
             "max_semestres": max(values) if values else None} for group, values in groups.items()]
