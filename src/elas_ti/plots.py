"""Figuras agregadas sem identificadores pessoais."""

import os
from pathlib import Path

from .utils import period_index


def create_plots(entrants: list[dict], graduates: list[dict], output: Path):
    output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(output / ".matplotlib"))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    series = [
        ("Ingressantes", entrants, "#355c9a"),
        ("Concluintes", graduates, "#a83e65"),
    ]
    selections = [
        ([series[0]], "participacao_feminina_ingressantes.png"),
        ([series[1]], "participacao_feminina_concluintes.png"),
        (series, "ingressantes_vs_concluintes.png"),
    ]
    for selected, filename in selections:
        fig, ax = plt.subplots(figsize=(9, 4.8), layout="constrained")
        periods = sorted(
            {r["periodo"] for _, rows, _ in selected for r in rows}, key=period_index
        )
        any_data = False
        for label, rows, color in selected:
            x = [period_index(r["periodo"]) for r in rows]
            y = [
                r["female_percent_resolved"]
                if r["female_percent_resolved"] is not None
                else float("nan")
                for r in rows
            ]
            if rows:
                ax.plot(x, y, marker="o", label=label, color=color)
            any_data |= any(r["female_percent_resolved"] is not None for r in rows)
        ax.set_xticks(
            [period_index(p) for p in periods], periods, rotation=45, ha="right"
        )
        ax.set_ylim(0, 100)
        ax.set_xlabel("Ano/semestre (períodos disponíveis)")
        ax.set_ylabel("Participação feminina estimada (% dos resolvidos)")
        ax.grid(axis="y", alpha=0.25)
        ax.spines[["top", "right"]].set_visible(False)
        if ax.get_legend_handles_labels()[0]:
            ax.legend(frameon=False)
        if not any_data:
            ax.text(
                0.5,
                0.5,
                "Sem estimativas disponíveis",
                transform=ax.transAxes,
                ha="center",
            )
        fig.savefig(output / filename, dpi=180)
        plt.close(fig)
