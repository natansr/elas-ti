import csv
from pathlib import Path


def write_csv(path: Path, rows: list[dict], fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = fields or list(dict.fromkeys(k for row in rows for k in row)) or ["sem_dados"]
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def audit_documents(documents, output: Path):
    rows = [{"arquivo": d.arquivo, "tipo_registro": d.tipo_registro,
             "registros_brutos": d.registros_brutos, "registros_unicos": d.registros_unicos,
             "duplicacoes_removidas": d.duplicacoes_removidas, "total_pdf": d.total_pdf,
             "needs_ocr": d.needs_ocr, "status": d.status,
             "avisos": " | ".join(d.warnings)} for d in documents]
    write_csv(output / "csv/documentos_processados.csv", rows)
    write_csv(output / "csv/casos_para_revisao.csv", [r for d in documents for r in d.review])
    lines = ["ELAS-TI — validação dos PDFs", f"Documentos: {len(documents)}"]
    for d in documents:
        groups = {}
        for r in d.records:
            key = (r.tipo_registro, r.curso_normalizado, r.periodo)
            groups[key] = groups.get(key, 0) + 1
        # Não incluir nomes de arquivos, que também podem conter dados pessoais.
        lines.append(f"Documento {documents.index(d) + 1}: {d.status}; brutos={d.registros_brutos}; únicos={d.registros_unicos}; duplicações={d.duplicacoes_removidas}")
        lines.extend(f"{kind} | {course} | {period} | {n}" for (kind, course, period), n in groups.items())
        lines.extend(d.warnings)
    path = output / "reports/validacao_pdfs.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(lines)
