"""Seleção local de gráficos; lê o snapshot sem consultar serviços externos."""

import json
import math
import os
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from .cohort_matching import match_cohorts, summarize_cohorts, time_summary
from .models import StudentRecord
from .statistics import temporal_summary
from .utils import period_index

ANALYSES = {
    "1": "Quantidade de estudantes",
    "2": "Participação feminina estimada",
    "3": "Comparação ingresso × conclusão",
    "4": "Cobertura da inferência",
    "5": "Correspondência por coorte",
    "6": "Tempo até conclusão por curso",
}


def choose(prompt: str, options: dict, default=None) -> str:
    while True:
        print("\n" + prompt)
        for key, label in options.items():
            print(f"  {key}. {label}")
        answer = input(f"Escolha{f' [{default}]' if default else ''}: ").strip()
        answer = answer or default
        if answer in options:
            return answer
        print("Opção inválida; escolha um dos números exibidos.")


def prepare_chart(records, analysis, course=None, start=None, end=None, kind=None):
    """Filtros de coorte atuam no ingresso, preservando conclusões posteriores."""
    records = [r for r in records if course is None or r.curso_normalizado == course]

    def within(period):
        value = period_index(period)
        return (start is None or value >= period_index(start)) and (
            end is None or value <= period_index(end)
        )

    if start and end and period_index(start) > period_index(end):
        raise ValueError("Intervalo de períodos invertido")
    series = []
    note = ""
    if analysis in ("5", "6"):
        matches = [m for m in match_cohorts(records) if within(m["periodo_ingresso"])]
        if analysis == "5":
            rows = summarize_cohorts(records, matches)
            labels = [
                f"{r['curso_normalizado']}\n{r['periodo_ingresso']}" for r in rows
            ]
            values = [100 * r["match_proportion"] for r in rows]
            note = (
                "Reencontrados nas listas disponíveis; não é taxa oficial de conclusão."
            )
            note += "\nAcompanhamento (semestres): " + "; ".join(
                f"{r['periodo_ingresso']}: {r['followup_semesters'] if r['followup_semesters'] is not None else 'sem lista'}"
                for r in rows
            )
            ylabel = "Correspondências únicas / ingressantes da coorte (%)"
        else:
            rows = [r for r in time_summary(matches) if r["grupo"] != "global"]
            labels = [f"{r['grupo']}\n(n={r['n']})" for r in rows]
            values = [r["media_semestres"] for r in rows]
            note = (
                "Média entre vínculos únicos; barras verticais indicam mínimo e máximo."
            )
            ylabel = "Tempo até conclusão (semestres)"
        series.append(
            {
                "label": "Coortes",
                "values": values,
                "lower": [r["min_semestres"] for r in rows] if analysis == "6" else [],
                "upper": [r["max_semestres"] for r in rows] if analysis == "6" else [],
            }
        )
        x = list(range(len(labels)))
    else:
        records = [r for r in records if within(r.periodo)]
        kinds = [kind] if kind and analysis != "3" else ["ingressante", "concluinte"]
        periods = sorted(
            {r.periodo for r in records if r.tipo_registro in kinds}, key=period_index
        )
        labels, x = periods, [period_index(p) for p in periods]
        field = {
            "1": "total",
            "2": "female_percent_resolved",
            "3": "female_percent_resolved",
            "4": "cobertura",
        }[analysis]
        ylabel = {
            "1": "Número de registros",
            "2": "Participação feminina estimada (% dos resolvidos)",
            "3": "Participação feminina estimada (% dos resolvidos)",
            "4": "Registros resolvidos / total (%)",
        }[analysis]
        for record_kind in kinds:
            rows = {
                r["periodo"]: r
                for r in temporal_summary(
                    [r for r in records if r.tipo_registro == record_kind]
                )
            }
            values, lower, upper = [], [], []
            for period in periods:
                row = rows.get(period)
                value = row[field] if row else None
                values.append(
                    value * 100 if value is not None and analysis == "4" else value
                )
                resolved = row["resolvidos"] if row else 0
                lower.append(
                    100 * row["interval95_lower_resolved"] / resolved
                    if resolved
                    else None
                )
                upper.append(
                    100 * row["interval95_upper_resolved"] / resolved
                    if resolved
                    else None
                )
            series.append(
                {
                    "label": "Ingressantes"
                    if record_kind == "ingressante"
                    else "Concluintes",
                    "values": values,
                    "lower": lower if analysis in ("2", "3") else [],
                    "upper": upper if analysis in ("2", "3") else [],
                }
            )
        note = "Somente períodos disponíveis; lacunas não equivalem a zero."
        if analysis in ("2", "3"):
            note += "\nPercentuais entre resolvidos; intervalo probabilístico de 95%, condicionado ao modelo."
        if analysis == "3":
            note += "\nIngresso e conclusão no mesmo semestre não representam a mesma coorte."
    return {
        "title": ANALYSES[analysis],
        "course": course or "Todos os cursos",
        "x": x,
        "labels": labels,
        "series": series,
        "ylabel": ylabel,
        "note": note,
        "percent": analysis in ("2", "3", "4", "5"),
        "xlabel": "Coorte de ingresso"
        if analysis == "5"
        else "Curso"
        if analysis == "6"
        else "Ano/semestre",
    }


def render_chart(chart, style="line", show=False):
    from matplotlib.figure import Figure

    if show:
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(11, 6), layout="constrained")
    else:
        fig = Figure(figsize=(11, 6), layout="constrained")
        ax = fig.subplots()
    colors = ["#355c9a", "#a83e65"]
    n = len(chart["series"])
    for index, series in enumerate(chart["series"]):
        values = [v if v is not None else math.nan for v in series["values"]]
        x = [
            v + (index - (n - 1) / 2) * 0.35 if style == "bar" else v
            for v in chart["x"]
        ]
        if style == "bar":
            ax.bar(
                x, values, width=0.32, label=series["label"], color=colors[index % 2]
            )
        else:
            ax.plot(
                x, values, marker="o", label=series["label"], color=colors[index % 2]
            )
        # Segmentos absolutos: quantis discretos podem não conter a expectativa.
        intervals = [
            (a, lo, hi)
            for a, lo, hi in zip(x, series["lower"], series["upper"])
            if lo is not None and hi is not None
        ]
        for a, lo, hi in intervals:
            ax.vlines(a, lo, hi, color=colors[index % 2], linewidth=1.4)
            ax.hlines([lo, hi], a - 0.06, a + 0.06, color=colors[index % 2])
    ax.set_title(chart["title"] + "\n" + chart["course"])
    ax.set_ylabel(chart["ylabel"])
    ax.set_xlabel(chart["xlabel"])
    ax.set_xticks(chart["x"], chart["labels"], rotation=35, ha="right")
    ax.set_ylim(bottom=0, top=100 if chart["percent"] else None)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.2)
    ax.legend(frameon=False)
    fig.supxlabel(chart["note"], fontsize=8)
    return fig


def run_menu(output: Path) -> int:
    from .pipeline import protect_output

    path = output / "registros_snapshot.json"
    if not path.exists():
        print(
            "Gere os dados locais primeiro: python main.py --no-api (ou python main.py para inferência)."
        )
        return 1
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload["schema_version"] != 1:
            raise ValueError
        records = [StudentRecord(**r) for r in payload["records"]]
    except (ValueError, TypeError, KeyError):
        print("Snapshot inválido; gere novamente a análise local.")
        return 1
    if not records:
        print(
            "Snapshot sem registros. Coloque os PDFs e execute python main.py --no-api."
        )
        return 1
    protect_output(output)
    destination = output / "figures"
    destination.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str((output / ".matplotlib").resolve()))
    print("ELAS-TI — gráficos locais (sem chamadas à API)")
    print("Dados da execução: " + str(payload.get("created_at", "não informada")))
    try:
        while True:
            analysis = choose(
                "Qual análise deseja visualizar?", {**ANALYSES, "0": "Sair"}
            )
            if analysis == "0":
                return 0
            courses = {
                str(i): c
                for i, c in enumerate(sorted({r.curso_normalizado for r in records}), 1)
            }
            course_choice = choose("Curso", {"0": "Todos", **courses}, "0")
            course = courses.get(course_choice)
            relevant = [
                r for r in records if course is None or r.curso_normalizado == course
            ]
            kind = None
            if analysis in ("1", "2", "4"):
                selected = choose(
                    "Registros",
                    {"0": "Ambos", "1": "Ingressantes", "2": "Concluintes"},
                    "0",
                )
                kind = {"1": "ingressante", "2": "concluinte"}.get(selected)
            periods = sorted(
                {
                    r.periodo
                    for r in relevant
                    if (
                        r.tipo_registro == "ingressante"
                        if analysis in ("5", "6")
                        else kind is None or r.tipo_registro == kind
                    )
                },
                key=period_index,
            )
            if not periods:
                print("Sem registros para essa seleção.")
                continue
            options = {str(i): p for i, p in enumerate(periods, 1)}
            print(
                "Períodos de ingresso da coorte"
                if analysis in ("5", "6")
                else "Períodos dos registros"
            )
            start = options[choose("Período inicial", options, "1")]
            end_options = {
                k: p
                for k, p in options.items()
                if period_index(p) >= period_index(start)
            }
            end = end_options[choose("Período final", end_options, str(len(periods)))]
            chart = prepare_chart(records, analysis, course, start, end, kind)
            if not any(v is not None for s in chart["series"] for v in s["values"]):
                print(
                    "Sem dados para este gráfico. Participação feminina exige inferências; tempo até conclusão exige vínculos únicos."
                )
                continue
            style = (
                "bar"
                if analysis in ("5", "6")
                else {"1": "line", "2": "bar"}[
                    choose("Formato", {"1": "Linhas", "2": "Barras"}, "1")
                ]
            )
            extension = {"1": "png", "2": "pdf", "3": "svg"}[
                choose("Salvar como", {"1": "PNG", "2": "PDF", "3": "SVG"}, "1")
            ]
            show = (
                choose(
                    "Exibição",
                    {"1": "Somente salvar", "2": "Salvar e abrir janela"},
                    "1",
                )
                == "2"
            )
            try:
                fig = render_chart(chart, style, show)
            except (ImportError, RuntimeError):
                print("Janela gráfica indisponível; o gráfico será salvo em arquivo.")
                show = False
                fig = render_chart(chart, style)
            target = (
                destination
                / f"grafico_{analysis}_{datetime.now():%Y%m%d_%H%M%S}_{uuid4().hex[:6]}.{extension}"
            )
            fig.savefig(target, dpi=180)
            print(f"Gráfico salvo em {target}")
            if show:
                import matplotlib
                import matplotlib.pyplot as plt

                if str(matplotlib.get_backend()).lower() in (
                    "agg",
                    "pdf",
                    "svg",
                    "ps",
                    "cairo",
                    "template",
                ):
                    print(
                        "Ambiente sem janela gráfica. Abra o arquivo salvo no visualizador do computador."
                    )
                else:
                    try:
                        plt.show()
                    except (ImportError, RuntimeError):
                        print("Não foi possível abrir a janela; o arquivo foi salvo.")
                plt.close(fig)
    except (EOFError, KeyboardInterrupt):
        print("\nMenu encerrado.")
        return 0
