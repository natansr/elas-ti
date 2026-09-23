"""Exportação pública: somente dimensões acadêmicas e estatísticas agregadas."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import StudentRecord
from .privacy import load_snapshot
from .public_schema import FIELDS, validate_data
from .statistics import grouped_summary

METRICS = FIELDS[4:]


def public_rows(records):
    rows = []
    for kind in ("ingressante", "concluinte"):
        subset = [r for r in records if r.tipo_registro == kind]
        for grain, period_field in (("ano", "ano"), ("semestre", "periodo")):
            for by_course in (False, True):
                fields = (
                    ("curso_normalizado", period_field)
                    if by_course
                    else (period_field,)
                )
                for summary in grouped_summary(subset, fields):
                    rows.append(
                        {
                            "tipo_registro": kind,
                            "curso": summary["curso_normalizado"]
                            if by_course
                            else "Todos os cursos",
                            "agrupamento": grain,
                            "periodo": str(summary[period_field]),
                            **{key: summary[key] for key in METRICS},
                        }
                    )
    return rows


def export_site(output: Path, destination: Path):
    payload = load_snapshot(output)
    records = [StudentRecord(**r) for r in payload["records"]]
    rows = public_rows(records)
    data = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "analysis_at": payload["created_at"],
        "rows": rows,
    }
    # Nenhum snapshot, documento ou configuração é copiado para o site.
    validate_data(data)
    destination.mkdir(parents=True, exist_ok=True)
    temporary = destination / "resumo.json.tmp"
    temporary.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination / "resumo.json")
    with (destination / "resumo.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(
        f"Exportação pública: {len(records)} registros agregados; JSON e CSV em {destination}."
    )
    resolved = sum(r.p_female is not None for r in records)
    print(
        f"Inferência disponível: {resolved}/{len(records)}. Sem nomes, identificadores individuais ou PDFs."
    )
    return 0
