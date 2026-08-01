"""Plotly figures for CWE analysis."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def build_cwe_figures(summary: pd.DataFrame, by_year: pd.DataFrame) -> dict[str, go.Figure]:
    top = summary.head(20).sort_values("cve_count")
    main = go.Figure(go.Bar(x=top["cve_count"], y=top["cwe"], orientation="h"))
    main.update_layout(title="Top 20 CWE labels by unique CVE count", xaxis_title="Unique CVEs")
    ransomware = go.Figure()
    ransomware.add_bar(x=top["cwe"], y=top["known_count"], name="Known")
    ransomware.add_bar(x=top["cwe"], y=top["unknown_count"], name="Unknown")
    ransomware.update_layout(title="Ransomware flag among Top 20 CWE labels", barmode="stack")
    top_codes = set(summary.head(10)["cwe"])
    annual = by_year[by_year["cwe"].isin(top_codes)]
    trend = go.Figure()
    for cwe, group in annual.groupby("cwe"):
        trend.add_scatter(x=group["year_added"], y=group["cve_count"], mode="lines+markers", name=cwe)
    trend.update_layout(title="Top CWE labels by year added", xaxis_title="Year", yaxis_title="Unique CVEs")
    return {"cwe_top20": main, "cwe_ransomware": ransomware, "cwe_by_year": trend}
