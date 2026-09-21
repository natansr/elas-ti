import csv
from pathlib import Path

from .privacy import protect_summaries, remove_legacy_exports, review_summary


def write_csv(path: Path, rows: list[dict], fields=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = (
        fields or list(dict.fromkeys(k for row in rows for k in row)) or ["sem_dados"]
    )
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def audit_documents(documents, output: Path):
    rows = [
        {
            "documento": f"documento_{i:03d}",
            "tipo_registro": d.tipo_registro,
            "registros_brutos": d.registros_brutos,
            "registros_unicos": d.registros_unicos,
            "duplicacoes_removidas": d.duplicacoes_removidas,
            "total_pdf": d.total_pdf,
            "needs_ocr": d.needs_ocr,
            "status": d.status,
            "avisos": " | ".join(d.warnings),
        }
        for i, d in enumerate(documents, 1)
    ]
    write_csv(output / "csv/documentos_processados.csv", rows)
    write_csv(
        output / "csv/resumo_revisao.csv",
        review_summary([r for d in documents for r in d.review]),
    )
    lines = ["ELAS-TI — validação dos PDFs", f"Documentos: {len(documents)}"]
    for d in documents:
        groups = {}
        for r in d.records:
            key = (r.tipo_registro, r.curso_normalizado, r.periodo)
            groups[key] = groups.get(key, 0) + 1
        # Não incluir nomes de arquivos, que também podem conter dados pessoais.
        lines.append(
            f"Documento {documents.index(d) + 1}: {d.status}; brutos={d.registros_brutos}; únicos={d.registros_unicos}; duplicações={d.duplicacoes_removidas}"
        )
        lines.extend(
            f"{kind} | {course} | {period} | {n}"
            for (kind, course, period), n in groups.items()
        )
        lines.extend(d.warnings)
    path = output / "reports/validacao_pdfs.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(lines)


METHODOLOGY = """Estimativa baseada no Genderize.io: gênero inferido a partir do nome,
sem observação de gênero autodeclarado. As probabilidades são parâmetros do
modelo, não ground truth. E[F]=soma(q), E[M]=soma(1-q), Var(F)=soma(q*(1-q)).
A Poisson-binomial exata assume independência entre registros resolvidos.
Seus quantis 2,5% e 97,5% formam o intervalo probabilístico de incerteza de 95%,
condicional ao modelo. Não se trata de intervalo de confiança amostral clássico.
Percentuais principais usam resolvidos como denominador. Nulos não recebem 0,5.
Limites conservadores de contagem: [quantil inferior, quantil superior + nulos].
Limites para expectativa no total: [E[F]/N, (E[F]+nulos)/N]. São conceitos distintos.
As séries ingresso e conclusão no mesmo semestre não representam a mesma coorte.
Match exige nome_chave e curso iguais, conclusão posterior e unicidade bilateral.
A medida longitudinal é a proporção de ingressantes reencontrados posteriormente
nas listas de conclusão disponíveis. Ela não é taxa oficial de conclusão."""

LIMITATIONS = """PDFs ausentes, mudanças de nome/curso, reingressos, homônimos, transferências,
abandono e coortes recentes limitam a interpretação. Exact_unique é uma
correspondência documental por nome, não uma confirmação externa de identidade.
A cobertura pode ser seletiva. O Genderize pode apresentar vieses culturais,
erros de calibração e dependência entre nomes. O modelo binário não representa
a diversidade das identidades de gênero. A independência da Poisson-binomial
pode não valer em grupos com pessoas repetidas entre períodos.
Não há medidas de accuracy, precision, recall ou F1 sem referência observada.
Linhas nos gráficos conectam períodos disponíveis; não imputam semestres ausentes."""


def generate_reports(records, documents, output: Path, settings):
    import json

    from .cohort_matching import match_cohorts, summarize_cohorts, time_summary
    from .plots import create_plots
    from .statistics import compare_periods, grouped_summary, temporal_summary

    output.mkdir(parents=True, exist_ok=True)
    remove_legacy_exports(output)
    minimum = getattr(settings, "MIN_GROUP_SIZE", 5)

    def safe(rows):
        return protect_summaries(rows, minimum)

    series, summaries = {}, {}
    for kind, label in [("ingressante", "ingressantes"), ("concluinte", "concluintes")]:
        subset = [r for r in records if r.tipo_registro == kind]
        series[kind] = safe(temporal_summary(subset))
        summaries[kind] = safe(grouped_summary(subset, ()))
        write_csv(output / f"csv/resumo_{label}_periodo.csv", series[kind])
        write_csv(
            output / f"csv/resumo_{label}_curso_periodo.csv",
            safe(temporal_summary(subset, True)),
        )
        for suffix, fields in [
            ("global", ()),
            ("curso", ("curso_normalizado",)),
            ("ano", ("ano",)),
            ("curso_ano", ("curso_normalizado", "ano")),
        ]:
            write_csv(
                output / f"csv/resumo_{label}_{suffix}.csv",
                safe(grouped_summary(subset, fields)),
            )
    comparison = compare_periods(series["ingressante"], series["concluinte"])
    matches = match_cohorts(records)
    cohorts = safe(summarize_cohorts(records, matches, settings.MIN_FOLLOWUP_SEMESTERS))
    durations = safe(time_summary(matches))
    write_csv(output / "csv/comparacao_ingressantes_concluintes.csv", comparison)
    write_csv(output / "csv/resumo_coortes.csv", cohorts)
    write_csv(output / "csv/tempo_ate_conclusao.csv", durations)
    review = [r for d in documents for r in d.review]
    review += [
        dict(m, motivo="matching ambíguo")
        for m in matches
        if m["status"] == "ambiguous"
    ]
    write_csv(output / "csv/resumo_revisao.csv", review_summary(review))
    # Todas as estruturas a seguir são agregadas, sem nomes ou caminhos de PDF.
    sections = [
        (
            "1. Dados analisados",
            {"documentos": len(documents), "registros": len(records)},
        ),
        (
            "2. Qualidade dos dados",
            {
                "avisos": sum(len(d.warnings) for d in documents),
                "duplicacoes_internas_removidas": sum(
                    d.duplicacoes_removidas for d in documents
                ),
            },
        ),
        ("3. Ingressantes", summaries["ingressante"]),
        ("4. Concluintes", summaries["concluinte"]),
        ("5. Evolução temporal", series),
        ("6. Comparação ingresso x conclusão", comparison),
        ("7. Análise de coortes", cohorts),
        ("8. Tempo entre ingresso e conclusão", durations),
    ]
    text = [
        "ELAS-TI",
        f"Privacidade: grupos com menos de {minimum} registros são suprimidos; saídas exigem revisão antes de divulgação.",
        "Estudo Longitudinal da Participação Feminina no Ingresso e na Conclusão dos Cursos de Tecnologia da Informação",
        "Universidade Estadual de Goiás",
        "Unidade Universitária de Goianésia",
    ]
    for title, data in sections:
        text.extend(
            ["", title, json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)]
        )
    text.extend(["", "9. Metodologia", METHODOLOGY, "10. Limitações", LIMITATIONS])
    report = output / "reports/relatorio_elas_ti.txt"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(text) + "\n", encoding="utf-8")
    create_plots(series["ingressante"], series["concluinte"], output / "figures")
