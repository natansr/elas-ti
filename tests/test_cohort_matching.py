from dataclasses import replace

from elas_ti.ingressantes_parser import parse_ingressantes
from elas_ti.formandos_parser import parse_formandos
from elas_ti.cohort_matching import match_cohorts, summarize_cohorts, time_summary
from test_parsers import ENTRANTS, GRADS


def records():
    return parse_ingressantes([ENTRANTS]).records + parse_formandos([GRADS]).records


def test_exact_and_not_found():
    data = records()
    matches = match_cohorts(data)
    assert [m["status"] for m in matches] == ["exact_unique", "not_found"]
    assert matches[0]["semesters_to_graduation"] == 13
    assert time_summary(matches)[0]["media_semestres"] == 13
    cohort = summarize_cohorts(data, matches)[0]
    assert cohort["match_proportion"] == .5
    assert cohort["followup_semesters"] == 13
    assert summarize_cohorts(data, matches, min_followup=14) == []


def test_multiple_graduations_are_ambiguous():
    data = records()
    data.append(replace(data[-1], periodo="2026/1"))
    assert match_cohorts(data)[0]["status"] == "ambiguous"


def test_reentry_and_homonyms_cannot_share_graduate():
    data = records()
    data.append(replace(data[0], periodo="2020/1", numero_sequencial=3))
    matches = match_cohorts(data)
    assert matches[0]["status"] == matches[2]["status"] == "ambiguous"
    assert summarize_cohorts(data, matches)[0]["n_matches_exact_unique"] == 0


def test_same_semester_earlier_and_other_course_do_not_match():
    for change in [{"periodo": "2019/1"}, {"periodo": "2018/2"}, {"curso_normalizado": "OUTRO CURSO"}]:
        data = records()
        data[-1] = replace(data[-1], **change)
        assert match_cohorts(data)[0]["status"] == "not_found"


def test_recent_cohort_and_absent_course_followup():
    data = records()
    data[0] = replace(data[0], periodo="2026/1")
    cohorts = summarize_cohorts(data, match_cohorts(data))
    assert cohorts[-1]["followup_semesters"] == 0
    only_entrants = data[:2]
    assert all(c["followup_semesters"] is None for c in summarize_cohorts(only_entrants, match_cohorts(only_entrants)))
