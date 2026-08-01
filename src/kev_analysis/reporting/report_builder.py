"""Build a self-contained, offline Jinja2/Plotly report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from plotly.io import to_html

from kev_analysis.models import AnalysisArtifacts, ValidationResult


def _table_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    return df.where(pd.notna(df), None).to_dict(orient="records")


def _figure_fragments(figures: dict[str, Any]) -> dict[str, str]:
    fragments: dict[str, str] = {}
    include_js: str | bool = "inline"
    for name, figure in figures.items():
        fragments[name] = to_html(
            figure,
            full_html=False,
            include_plotlyjs=include_js,
            config={"displaylogo": False, "responsive": True},
        )
        include_js = False
    return fragments


def build_report(
    destination: str | Path,
    template_dir: str | Path,
    *,
    metadata: dict[str, Any],
    validation: ValidationResult,
    field_quality: pd.DataFrame,
    temporal: AnalysisArtifacts,
    ransomware: AnalysisArtifacts,
    vendor: AnalysisArtifacts,
    cwe: AnalysisArtifacts,
    queries: AnalysisArtifacts,
    figures: dict[str, Any],
) -> Path:
    """Render all A-line and B-line artifacts into one offline HTML file."""

    template_path = Path(template_dir)
    environment = Environment(
        loader=FileSystemLoader(template_path),
        autoescape=select_autoescape(["html", "xml"]),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    environment.filters["integer"] = lambda value: f"{int(value):,}"
    environment.filters["percent"] = lambda value: f"{float(value):.2%}"
    environment.filters["number"] = lambda value: f"{float(value):,.2f}"

    css = (template_path.parent / "assets" / "report.css").read_text(encoding="utf-8")
    annual = temporal.tables["annual_additions"]
    all_figures = {**figures, **vendor.figures, **cwe.figures}
    figure_html = _figure_fragments(all_figures)
    context = {
        "metadata": metadata,
        "validation": validation,
        "field_quality": _table_records(field_quality),
        "annual": _table_records(annual),
        "deadline_summary": _table_records(temporal.tables["deadline_summary"]),
        "ransomware_summary": _table_records(ransomware.tables["ransomware_summary"]),
        "ransomware_by_year": _table_records(ransomware.tables["ransomware_by_year"]),
        "temporal_metrics": temporal.metrics,
        "ransomware_metrics": ransomware.metrics,
        "figures": figure_html,
        "vendor": {
            "metrics": vendor.metrics,
            "tables": {name: _table_records(table) for name, table in vendor.tables.items()},
            "figure_html": {name: figure_html[name] for name in vendor.figures},
        },
        "cwe": {
            "metrics": cwe.metrics,
            "tables": {name: _table_records(table) for name, table in cwe.tables.items()},
            "figure_html": {name: figure_html[name] for name in cwe.figures},
        },
        "queries": {
            "metrics": queries.metrics,
            "tables": {name: _table_records(table) for name, table in queries.tables.items()},
        },
        "css": css,
    }
    html = environment.get_template("report.html.j2").render(**context)
    output = Path(destination)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output

