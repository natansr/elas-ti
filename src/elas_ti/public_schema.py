"""Validação estrita do formato público, sem dependências externas."""

import csv
import io
import json
import math
import re
from datetime import datetime
from pathlib import Path

FIELDS = (
    "tipo_registro",
    "curso",
    "agrupamento",
    "periodo",
    "total",
    "resolvidos",
    "nao_identificados",
    "cobertura",
    "expected_female",
    "expected_male",
    "female_percent_resolved",
    "male_percent_resolved",
    "variance_female",
    "interval95_lower_resolved",
    "interval95_upper_resolved",
)


def validate_data(data):
    if (
        set(data) != {"schema_version", "generated_at", "analysis_at", "rows"}
        or data["schema_version"] != 1
    ):
        raise ValueError("Formato público incompatível")
    for key in ("generated_at", "analysis_at"):
        datetime.fromisoformat(data[key])
    if not isinstance(data["rows"], list):
        raise ValueError("Agregados inválidos")
    seen = set()
    for row in data["rows"]:
        if set(row) != set(FIELDS):
            raise ValueError("Campo não permitido na exportação pública")
        if row["tipo_registro"] not in {"ingressante", "concluinte"} or row[
            "agrupamento"
        ] not in {"ano", "semestre"}:
            raise ValueError("Dimensão inválida")
        course = row["curso"]
        if (
            not isinstance(course, str)
            or not course.strip()
            or len(course) > 200
            or course[0] in "=+-@"
            or any(c in course for c in "\r\n\t<>")
        ):
            raise ValueError("Curso inválido")
        pattern = r"\d{4}" if row["agrupamento"] == "ano" else r"\d{4}/[12]"
        if not isinstance(row["periodo"], str) or not re.fullmatch(
            pattern, row["periodo"]
        ):
            raise ValueError("Período inválido")
        key = tuple(row[k] for k in FIELDS[:4])
        if key in seen:
            raise ValueError("Agregado duplicado")
        seen.add(key)
        for field in FIELDS[4:]:
            value = row[field]
            if value is not None and (
                type(value) not in (int, float) or not math.isfinite(value) or value < 0
            ):
                raise ValueError("Métrica inválida")
        n, r, u = (row[k] for k in ("total", "resolvidos", "nao_identificados"))
        if any(type(v) is not int for v in (n, r, u)) or n != r + u or n < 1:
            raise ValueError("Contagens inconsistentes")
        female, male = row["expected_female"], row["expected_male"]
        if (
            female is None
            or male is None
            or not math.isclose(female + male, r, abs_tol=1e-9)
        ):
            raise ValueError("Estimativas inconsistentes")
        if row["cobertura"] is None or not math.isclose(row["cobertura"], r / n):
            raise ValueError("Cobertura inconsistente")
        for name, count in (("female", female), ("male", male)):
            percent = row[f"{name}_percent_resolved"]
            if (not r and percent is not None) or (
                r
                and (
                    percent is None
                    or not math.isclose(percent, count / r * 100, abs_tol=1e-9)
                )
            ):
                raise ValueError("Percentual inconsistente")
        low, high = row["interval95_lower_resolved"], row["interval95_upper_resolved"]
        if not r:
            if low is not None or high is not None:
                raise ValueError("Intervalo sem inferência")
        elif type(low) is not int or type(high) is not int or not 0 <= low <= high <= r:
            raise ValueError("Intervalo inválido")


def validate_csv(content, data=None):
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    if reader.fieldnames != list(FIELDS):
        raise ValueError("Colunas públicas inválidas")
    rows = list(reader)
    converted = []
    for row in rows:
        if set(row) != set(FIELDS) or any(value is None for value in row.values()):
            raise ValueError("Linha CSV com colunas excedentes ou ausentes")
        converted.append(
            {
                k: row[k] if k in FIELDS[:4] else json.loads(row[k]) if row[k] else None
                for k in FIELDS
            }
        )
    validate_data(
        {
            "schema_version": 1,
            "generated_at": "2026-01-01",
            "analysis_at": "2026-01-01",
            "rows": converted,
        }
    )
    if data is not None and converted != data["rows"]:
        raise ValueError("CSV e JSON divergentes")


def validate_directory(root):
    root = Path(root)
    allowed = {
        "index.html",
        "styles.css",
        "app.js",
        ".nojekyll",
        "data/resumo.json",
        "data/resumo.csv",
    }
    for path in root.rglob("*"):
        if path.is_symlink() or (
            path.is_file() and path.relative_to(root).as_posix() not in allowed
        ):
            raise ValueError("Arquivo inesperado no site")
    data = json.loads((root / "data/resumo.json").read_text(encoding="utf-8"))
    validate_data(data)
    validate_csv((root / "data/resumo.csv").read_text(encoding="utf-8-sig"), data)
    return len(data["rows"])
