"""Minimização de dados locais; pseudonimização não garante anonimato."""

import json
from collections import Counter
from pathlib import Path
from uuid import uuid4

# Exportações individuais antigas: removidas ao regenerar ou migrar saídas.
LEGACY_EXPORTS = (
    "registros_classificados.csv",
    "cohort_matches.csv",
    "casos_para_revisao.csv",
)


def remove_legacy_exports(output: Path):
    for filename in LEGACY_EXPORTS:
        (output / "csv" / filename).unlink(missing_ok=True)


def pseudonymize_payload(payload: dict) -> dict:
    tokens, files = {}, {}

    def document_id(name):
        return files.setdefault(name, f"documento_{len(files) + 1:03d}")

    def record(item):
        item = dict(item)
        key = item["nome_chave"]
        item["nome_chave"] = tokens.setdefault(key, uuid4().hex)
        item["nome_original"] = item["nome_normalizado"] = ""
        item["arquivo"] = document_id(item["arquivo"])
        item["pagina"] = item["numero_sequencial"] = 0
        item["turno"] = item["tipo_ingresso"] = item["motivo_entrada"] = None
        return item

    result = dict(payload, schema_version=2)
    result["records"] = [record(r) for r in payload["records"]]
    result["documents"] = []
    for d in payload.get("documents", []):
        copy = dict(d, arquivo=document_id(d["arquivo"]))
        copy["records"] = [record(r) for r in d["records"]]
        copy["review"] = [
            {"motivo": r.get("motivo", "revisão")} for r in d.get("review", [])
        ]
        result["documents"].append(copy)
    # Hashes de arquivos não são necessários para os gráficos/reconstrução.
    result.pop("source_sha256", None)
    result["privacy"] = "pseudonimizado; uso local restrito; não publicar"
    allowed = {
        "PROJECT_NAME",
        "COUNTRY_ID",
        "GENDERIZE_NAME_MODE",
        "GENDERIZE_BATCH_SIZE",
        "HIGH_CONFIDENCE",
        "MEDIUM_CONFIDENCE",
        "MONTE_CARLO_ITERATIONS",
        "RANDOM_SEED",
        "MIN_FOLLOWUP_SEMESTERS",
        "COURSES_OF_INTEREST",
        "COURSE_ALIASES",
        "MIN_GROUP_SIZE",
    }
    result["settings"] = {
        k: v for k, v in result.get("settings", {}).items() if k in allowed
    }
    return result


def write_snapshot(payload, path: Path):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding="utf-8"
    )
    temporary.chmod(0o600)
    temporary.replace(path)


def load_snapshot(output: Path) -> dict:
    path = output / "registros_snapshot.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") == 1:
        payload = pseudonymize_payload(payload)
        write_snapshot(payload, path)
    if payload.get("schema_version") != 2:
        raise ValueError("Snapshot incompatível")
    remove_legacy_exports(output)
    return payload


def review_summary(reviews):
    return [
        {"motivo": reason, "quantidade": count}
        for reason, count in sorted(
            Counter(r.get("motivo", "revisão") for r in reviews).items()
        )
    ]


def protect_summaries(rows, minimum=5):
    """Suprime células pequenas; não é garantia contra reidentificação."""
    if minimum < 1:
        raise ValueError("Tamanho mínimo deve ser positivo")
    result = []
    labels = {"curso_normalizado", "periodo", "ano", "periodo_ingresso", "grupo"}
    for source in rows:
        row = dict(source)
        n = row.get("total", row.get("n_ingressantes", row.get("n")))
        if n is not None and 0 < n < minimum:
            row = {k: v if k in labels else None for k, v in row.items()}
            row["privacidade"] = "grupo pequeno suprimido"
        else:
            resolved = row.get("resolvidos")
            if resolved is not None and 0 < resolved < minimum:
                row = {
                    k: v if k in labels | {"total"} else None for k, v in row.items()
                }
                row["privacidade"] = "inferência suprimida: poucos resolvidos"
            matched = row.get("n_matches_exact_unique")
            if matched is not None and 0 < matched < minimum:
                for k in (
                    "n_matches_exact_unique",
                    "match_proportion",
                    "resolved_matched",
                    "expected_female_matched",
                    "expected_male_matched",
                ):
                    row[k] = None
                row["privacidade"] = "correspondências pequenas suprimidas"
        for suffix in ("entrants", "matched"):
            resolved = row.get(f"resolved_{suffix}")
            if resolved is not None and 0 < resolved < minimum:
                for field in (
                    f"resolved_{suffix}",
                    f"expected_female_{suffix}",
                    f"expected_male_{suffix}",
                ):
                    row[field] = None
                row["privacidade"] = "inferência de coorte suprimida"
        result.append(row)
    previous = {}
    for row in result:
        if "variacao_pp" in row:
            course = row.get("curso_normalizado", "")
            value = row.get("female_percent_resolved")
            last = previous.get(course)
            row["variacao_pp"] = (
                value - last if value is not None and last is not None else None
            )
            previous[course] = value
    return result
