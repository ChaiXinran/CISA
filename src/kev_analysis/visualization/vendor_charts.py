"""Plotly figures for vendor analysis; figures do not embed Plotly JS."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def build_vendor_figures(
    vendor_summary: pd.DataFrame,
    vendor_product_summary: pd.DataFrame,
    concentration: dict[str, float],
) -> dict[str, go.Figure]:
    top20 = vendor_summary.head(20).sort_values("count")
    top30 = vendor_product_summary.head(30).copy()
    top30["label"] = top30["vendor_clean"].astype(str) + " — " + top30["product_clean"].astype(str)
    top30 = top30.sort_values("count")

    vendors = go.Figure(go.Bar(x=top20["count"], y=top20["vendor_clean"], orientation="h"))
    vendors.update_layout(title="Top 20 vendor labels in the KEV snapshot", xaxis_title="KEV records")
    products = go.Figure(go.Bar(x=top30["count"], y=top30["label"], orientation="h"))
    products.update_layout(title="Top 30 vendor-product labels", xaxis_title="KEV records", height=850)
    pareto = go.Figure()
    pareto.add_bar(x=vendor_summary["vendor_clean"], y=vendor_summary["count"], name="Records")
    pareto.add_scatter(
        x=vendor_summary["vendor_clean"], y=vendor_summary["cumulative_share"],
        name="Cumulative share", yaxis="y2",
    )
    pareto.update_layout(
        title="Vendor-label Pareto distribution", yaxis_title="KEV records",
        yaxis2={"title": "Cumulative share", "overlaying": "y", "side": "right", "tickformat": ".0%"},
    )
    ransomware = go.Figure()
    ransomware.add_bar(x=top20["vendor_clean"], y=top20["known_count"], name="Known")
    ransomware.add_bar(x=top20["vendor_clean"], y=top20["unknown_count"], name="Unknown")
    ransomware.update_layout(title="Ransomware flag among Top 20 vendor labels", barmode="stack")
    indicators = go.Figure()
    for index, key in enumerate(("cr5", "cr10", "hhi")):
        indicators.add_trace(go.Indicator(
            mode="number", value=concentration[key], number={"valueformat": ".4f"},
            title={"text": key.upper()}, domain={"row": 0, "column": index},
        ))
    indicators.update_layout(grid={"rows": 1, "columns": 3, "pattern": "independent"}, title="Concentration metrics")
    return {
        "vendor_top20": vendors, "vendor_product_top30": products,
        "vendor_pareto": pareto, "vendor_ransomware": ransomware,
        "vendor_concentration": indicators,
    }
