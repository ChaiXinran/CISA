"""Plotly charts that consume precomputed temporal tables."""

from __future__ import annotations

from typing import Any

import pandas as pd


def _plotly_express():
    try:
        import plotly.express as px
    except ImportError as exc:
        raise RuntimeError("Plotly is required for chart generation; install requirements.txt") from exc
    return px


def build_temporal_figures(
    monthly: pd.DataFrame,
    annual: pd.DataFrame,
    deadline_frequency: pd.DataFrame,
    prepared_df: pd.DataFrame,
    ransomware_summary: pd.DataFrame,
    ransomware_by_year: pd.DataFrame,
) -> dict[str, Any]:
    """Create six figures without recalculating the supplied summary tables."""

    px = _plotly_express()
    figures: dict[str, Any] = {}
    figures["monthly_additions"] = px.line(
        monthly, x="month", y="count", markers=True,
        title="CISA KEV 每月加入记录数（2021-11 至 2026-07）",
        labels={"month": "月份", "count": "记录数"},
    )
    annual_chart = annual.copy()
    annual_chart["coverage"] = annual_chart["is_complete_year"].map({True: "完整年份", False: "部分年份"})
    figures["annual_additions"] = px.bar(
        annual_chart, x="year", y="count", color="coverage", barmode="group",
        title="CISA KEV 年度加入记录数", labels={"year": "年份", "count": "记录数", "coverage": "覆盖范围"},
    )
    figures["deadline_distribution"] = px.bar(
        deadline_frequency, x="deadline_days", y="count",
        title="目录规定处置期限分布", labels={"deadline_days": "期限（天）", "count": "记录数"},
    )
    figures["deadline_by_year"] = px.box(
        prepared_df, x="year_added", y="deadline_days", points=False,
        title="各加入年份的目录处置期限", labels={"year_added": "加入年份", "deadline_days": "期限（天）"},
    )
    figures["ransomware_overall"] = px.bar(
        ransomware_summary, x="status", y="count", color="status",
        color_discrete_map={"Known": "#c0392b", "Unknown": "#7f8c8d"},
        title="勒索软件活动利用确认状态", labels={"status": "CISA 状态", "count": "记录数"},
    )
    annual_long = ransomware_by_year.melt(
        id_vars="year", value_vars=["known_count", "unknown_count"],
        var_name="status", value_name="count",
    )
    annual_long["status"] = annual_long["status"].map(
        {"known_count": "Known", "unknown_count": "Unknown"}
    )
    figures["ransomware_by_year"] = px.bar(
        annual_long, x="year", y="count", color="status", barmode="stack",
        color_discrete_map={"Known": "#c0392b", "Unknown": "#7f8c8d"},
        title="各加入年份的勒索软件确认状态", labels={"year": "年份", "count": "记录数", "status": "CISA 状态"},
    )
    for figure in figures.values():
        figure.update_layout(template="plotly_white")
    return figures

