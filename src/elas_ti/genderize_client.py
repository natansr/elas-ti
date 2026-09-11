"""Cliente com mensagens sanitizadas: nunca expor URL, chave ou payload de erro."""

import math
import time
from datetime import datetime, timezone

import requests

from .name_normalizer import normalize_name


class GenderizeError(RuntimeError):
    pass


def validate_prediction(item: dict):
    if (
        not isinstance(item, dict)
        or not {"gender", "probability", "count"} <= item.keys()
    ):
        raise ValueError("Resposta incompleta")
    gender, probability, count = item["gender"], item["probability"], item["count"]
    if gender not in (None, "female", "male"):
        raise ValueError("Categoria inválida")
    if probability is not None and (
        isinstance(probability, bool)
        or not isinstance(probability, (int, float))
        or not math.isfinite(probability)
        or not 0 <= probability <= 1
    ):
        raise ValueError("Probabilidade inválida")
    if gender is not None and probability is None:
        raise ValueError("Probabilidade ausente")
    if count is not None and (type(count) is not int or count < 0):
        raise ValueError("Contagem inválida")


class GenderizeClient:
    def __init__(
        self,
        cache,
        api_key=None,
        country="BR",
        mode="full",
        batch_size=100,
        session=None,
        sleep=time.sleep,
        attempts=4,
    ):
        if mode not in ("full", "first") or not 1 <= batch_size <= 100 or attempts < 1:
            raise ValueError("Configuração Genderize inválida")
        self.cache, self.api_key = cache, api_key
        self.country, self.mode, self.batch_size = country, mode, batch_size
        self.session = session or requests.Session()
        self.sleep, self.attempts = sleep, attempts

    def query_name(self, name: str) -> str:
        normalized = normalize_name(name).upper()
        if not normalized:
            raise ValueError("Nome vazio")
        return normalized.split()[0] if self.mode == "first" else normalized

    def _batch(self, names: list[str]) -> list[dict]:
        if not self.api_key:
            raise GenderizeError(
                "GENDERIZE_API_KEY ausente; configure .env ou use --no-api."
            )
        for attempt in range(self.attempts):
            try:
                response = self.session.get(
                    "https://api.genderize.io",
                    params={
                        "name[]": names,
                        "country_id": self.country,
                        "apikey": self.api_key,
                    },
                    timeout=(10, 30),
                    allow_redirects=False,
                )
                status = response.status_code
                if status in (401, 402):
                    raise GenderizeError(
                        f"Genderize HTTP {status}: verifique credencial/assinatura."
                    )
                if status in (429, 500, 502, 503):
                    raise requests.ConnectionError("Falha recuperável")
                if status != 200:
                    raise GenderizeError(
                        f"Genderize HTTP {status}; consulta interrompida."
                    )
                payload = response.json()
                if not isinstance(payload, list) or len(payload) != len(names):
                    raise ValueError("Lote inválido")
                for name, item in zip(names, payload):
                    validate_prediction(item)
                    if (
                        item.get("name") != name
                        or item.get("country_id", self.country) != self.country
                    ):
                        raise ValueError("Resposta não corresponde à consulta")
                return payload
            except (requests.RequestException, ValueError, TypeError):
                if attempt + 1 == self.attempts:
                    raise GenderizeError(
                        "Genderize indisponível ou resposta inválida após tentativas limitadas."
                    ) from None
                self.sleep(2**attempt)
        raise GenderizeError("Consulta não concluída")

    def lookup(self, names: list[str], no_api=False) -> dict[str, dict | None]:
        queries = {name: self.query_name(name) for name in names}
        results = {
            q: self.cache.get(q, self.country, self.mode) for q in set(queries.values())
        }
        missing = sorted(q for q, result in results.items() if result is None)
        if not no_api:
            for start in range(0, len(missing), self.batch_size):
                batch = missing[start : start + self.batch_size]
                for query, item in zip(batch, self._batch(batch)):
                    result = dict(
                        item,
                        country_id=self.country,
                        name_mode=self.mode,
                        nome_consultado=query,
                        timestamp_consulta=datetime.now(timezone.utc).isoformat(),
                    )
                    self.cache.put(query, self.country, self.mode, result)
                    results[query] = result
        return {name: results[query] for name, query in queries.items()}


def apply_prediction(record, prediction, high=0.90, medium=0.75):
    if not 0 <= medium <= high <= 1:
        raise ValueError("Limiares inválidos")
    record.genderize_gender = record.genderize_probability = record.genderize_count = (
        None
    )
    record.p_female = record.p_male = None
    record.confidence_class = "não identificado"
    if prediction is None:
        return
    validate_prediction(prediction)
    record.genderize_gender = prediction["gender"]
    record.genderize_probability = prediction["probability"]
    record.genderize_count = prediction["count"]
    if prediction["gender"] is None:
        return
    p = prediction["probability"]
    record.p_female = p if prediction["gender"] == "female" else 1 - p
    record.p_male = 1 - record.p_female
    record.confidence_class = (
        "alta confiança"
        if p >= high
        else ("confiança moderada" if p >= medium else "baixa confiança")
    )
