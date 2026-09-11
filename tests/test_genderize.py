from unittest.mock import Mock

import pytest
import requests
from test_parsers import ENTRANTS

from elas_ti.cache import GenderCache
from elas_ti.genderize_client import GenderizeClient, GenderizeError, apply_prediction
from elas_ti.ingressantes_parser import parse_ingressantes


def response(names, gender="female", p=0.95):
    return [
        {"name": n, "gender": gender, "probability": p, "count": 100} for n in names
    ]


def test_persistent_cache_and_query_modes(tmp_path):
    path = tmp_path / "cache.sqlite"
    session = Mock()
    session.get.return_value = Mock(
        status_code=200, json=lambda: response(["ANA TESTE SILVA"])
    )
    with GenderCache(path) as cache:
        client = GenderizeClient(cache, "synthetic-test-value", session=session)
        result = client.lookup(["ANA TESTE SILVA", "ANA TESTE SILVA"])
        assert result["ANA TESTE SILVA"]["timestamp_consulta"]
        assert session.get.call_count == 1
    with GenderCache(path) as cache:
        client = GenderizeClient(cache, session=session)
        assert (
            client.lookup(["ANA TESTE SILVA"])["ANA TESTE SILVA"]["probability"] == 0.95
        )
        assert session.get.call_count == 1
        assert (
            GenderizeClient(cache, mode="first").lookup(
                ["ANA TESTE SILVA"], no_api=True
            )["ANA TESTE SILVA"]
            is None
        )
        assert (
            GenderizeClient(cache, country="PT").lookup(
                ["ANA TESTE SILVA"], no_api=True
            )["ANA TESTE SILVA"]
            is None
        )


@pytest.mark.parametrize("status", [401, 402, 422])
def test_permanent_errors_do_not_retry(tmp_path, status):
    session = Mock()
    session.get.return_value.status_code = status
    with GenderCache(tmp_path / "cache.sqlite") as cache:
        with pytest.raises(GenderizeError) as error:
            GenderizeClient(cache, "synthetic-test-value", session=session).lookup(
                ["ANA TESTE SILVA"]
            )
        assert "synthetic-test-value" not in str(error.value)
        assert session.get.call_count == 1


@pytest.mark.parametrize(
    "failure",
    [
        429,
        500,
        502,
        503,
        requests.Timeout("secret"),
        requests.ConnectionError("secret"),
        ValueError("secret"),
    ],
)
def test_recoverable_errors(tmp_path, failure):
    session, sleep = Mock(), Mock()
    good = Mock(status_code=200, json=lambda: response(["ANA TESTE SILVA"]))
    if isinstance(failure, ValueError):
        bad = Mock(status_code=200)
        bad.json.side_effect = failure
    else:
        bad = Mock(status_code=failure) if isinstance(failure, int) else failure
    session.get.side_effect = [bad, good]
    with GenderCache(tmp_path / "cache.sqlite") as cache:
        result = GenderizeClient(
            cache, "synthetic-test-value", session=session, sleep=sleep
        ).lookup(["ANA TESTE SILVA"])
        assert result["ANA TESTE SILVA"]["gender"] == "female"
        sleep.assert_called_once_with(1)


def test_exhaustion_and_no_api(tmp_path):
    session, sleep = Mock(), Mock()
    session.get.side_effect = requests.Timeout("sensitive URL")
    with GenderCache(tmp_path / "cache.sqlite") as cache:
        client = GenderizeClient(
            cache, "synthetic-test-value", session=session, sleep=sleep
        )
        assert client.lookup(["ANA TESTE SILVA"], no_api=True) == {
            "ANA TESTE SILVA": None
        }
        session.get.assert_not_called()
        with pytest.raises(GenderizeError, match="tentativas") as error:
            client.lookup(["ANA TESTE SILVA"])
        assert "sensitive" not in str(error.value)
        assert [c.args[0] for c in sleep.call_args_list] == [1, 2, 4]


@pytest.mark.parametrize(
    "gender,p,q,confidence",
    [
        ("female", 0.95, 0.95, "alta confiança"),
        ("male", 0.8, 0.2, "confiança moderada"),
        ("female", 0.6, 0.6, "baixa confiança"),
        (None, None, None, "não identificado"),
    ],
)
def test_individual_probability(gender, p, q, confidence):
    record = parse_ingressantes([ENTRANTS]).records[0]
    apply_prediction(record, {"gender": gender, "probability": p, "count": 10})
    assert record.p_female == (pytest.approx(q) if q is not None else None)
    assert record.p_male == (pytest.approx(1 - q) if q is not None else None)
    assert record.confidence_class == confidence


def test_malformed_probability_rejected():
    record = parse_ingressantes([ENTRANTS]).records[0]
    with pytest.raises(ValueError):
        apply_prediction(
            record, {"gender": "female", "probability": float("nan"), "count": 1}
        )


def test_batch_sizes_and_null_cache(tmp_path):
    session = Mock()

    def reply(*args, **kwargs):
        names = kwargs["params"]["name[]"]
        return Mock(status_code=200, json=lambda: response(names, None, None))

    session.get.side_effect = reply
    names = [f"PESSOA SINTETICA {i}" for i in range(101)]
    with GenderCache(tmp_path / "cache.sqlite") as cache:
        client = GenderizeClient(cache, "synthetic-test-value", session=session)
        client.lookup(names)
        assert [
            len(c.kwargs["params"]["name[]"]) for c in session.get.call_args_list
        ] == [100, 1]
        result = client.lookup(names)
        assert session.get.call_count == 2
        assert result[names[0]]["gender"] is None
