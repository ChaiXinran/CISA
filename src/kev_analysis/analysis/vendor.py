"""Vendor, product, and concentration analysis for a prepared KEV dataset."""

from __future__ import annotations

import pandas as pd
from kev_analysis.models import AnalysisArtifacts


def _require_columns(df: pd.DataFrame, columns: set[str]) -> None:
    missing = sorted(columns.difference(df.columns))
    if missing:
        raise KeyError(f"prepared_df is missing required columns: {missing}")


def build_vendor_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Count vendor labels and ransomware flags using decimal shares."""
    _require_columns(df, {"vendor_clean", "knownRansomwareCampaignUse"})
    if df.empty:
        return pd.DataFrame(columns=[
            "rank", "vendor_clean", "count", "share", "cumulative_share",
            "known_count", "unknown_count", "known_share", "unknown_share",
        ])

    counts = (
        df.groupby("vendor_clean", dropna=False, sort=False)
        .size().rename("count").reset_index()
    )
    flags = pd.crosstab(df["vendor_clean"], df["knownRansomwareCampaignUse"])
    flags = flags.reindex(columns=["Known", "Unknown"], fill_value=0)
    flags = flags.rename(columns={"Known": "known_count", "Unknown": "unknown_count"})
    result = counts.merge(flags, left_on="vendor_clean", right_index=True, how="left")
    result = result.sort_values(["count", "vendor_clean"], ascending=[False, True], kind="mergesort")
    result = result.reset_index(drop=True)
    result.insert(0, "rank", result.index + 1)
    result["share"] = result["count"] / len(df)
    result["cumulative_share"] = result["share"].cumsum()
    result["known_share"] = result["known_count"] / result["count"]
    result["unknown_share"] = result["unknown_count"] / result["count"]
    return result[[
        "rank", "vendor_clean", "count", "share", "cumulative_share",
        "known_count", "unknown_count", "known_share", "unknown_share",
    ]]


def build_vendor_product_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Count deterministic vendor-product labels with stable tie ordering."""
    _require_columns(df, {"vendor_clean", "product_clean"})
    result = (
        df.groupby(["vendor_clean", "product_clean"], dropna=False, sort=False)
        .size().rename("count").reset_index()
        .sort_values(
            ["count", "vendor_clean", "product_clean"],
            ascending=[False, True, True], kind="mergesort",
        ).reset_index(drop=True)
    )
    result.insert(0, "rank", result.index + 1)
    denominator = len(df)
    result["share"] = result["count"] / denominator if denominator else 0.0
    result["cumulative_share"] = result["share"].cumsum()
    return result[[
        "rank", "vendor_clean", "product_clean", "count", "share", "cumulative_share"
    ]]


def calculate_concentration(vendor_summary: pd.DataFrame) -> dict[str, float]:
    """Calculate CR5, CR10 and HHI from decimal vendor shares."""
    _require_columns(vendor_summary, {"share"})
    shares = pd.to_numeric(vendor_summary["share"], errors="raise").astype(float)
    if ((shares < 0) | (shares > 1)).any():
        raise ValueError("vendor shares must be decimals in [0, 1]")
    return {
        "cr5": float(shares.head(5).sum()),
        "cr10": float(shares.head(10).sum()),
        "hhi": float((shares ** 2).sum()),
    }


def run_vendor_analysis(df: pd.DataFrame) -> AnalysisArtifacts:
    """Build all B-line vendor artifacts without mutating ``df``."""
    from kev_analysis.visualization.vendor_charts import build_vendor_figures

    vendor_summary = build_vendor_summary(df)
    vendor_product_summary = build_vendor_product_summary(df)
    concentration = calculate_concentration(vendor_summary)
    figures = build_vendor_figures(vendor_summary, vendor_product_summary, concentration)
    return AnalysisArtifacts(
        tables={
            "vendor_summary": vendor_summary,
            "vendor_product_summary": vendor_product_summary,
            "top30_vendor_products": vendor_product_summary.head(30).copy(),
        },
        metrics={"vendor_concentration": concentration},
        figures=figures,
        notes=[
            "Counts describe labels in this KEV snapshot, not vendor security or attack probability.",
            "Shares and HHI use decimal proportions in [0, 1].",
        ],
    )
