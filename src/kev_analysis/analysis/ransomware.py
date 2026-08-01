"""Known/Unknown ransomware campaign-use statistics."""

from __future__ import annotations

import pandas as pd

from kev_analysis.constants import RANSOMWARE_VALUES
from kev_analysis.models import AnalysisArtifacts

STATUS_ORDER = ["Known", "Unknown"]


def _validate_statuses(df: pd.DataFrame) -> None:
    required = {"knownRansomwareCampaignUse", "year_added"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing prepared columns: {sorted(missing)}")
    values = set(df["knownRansomwareCampaignUse"].dropna().unique())
    if df["knownRansomwareCampaignUse"].isna().any() or not values.issubset(RANSOMWARE_VALUES):
        raise ValueError("Ransomware status must contain only Known and Unknown")


def build_ransomware_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Return overall Known/Unknown counts and decimal shares."""

    _validate_statuses(df)
    counts = df["knownRansomwareCampaignUse"].value_counts().reindex(STATUS_ORDER, fill_value=0)
    result = counts.rename_axis("status").reset_index(name="count")
    result["share"] = result["count"] / len(df) if len(df) else 0.0
    return result


def build_ransomware_by_year(df: pd.DataFrame) -> pd.DataFrame:
    """Return annual status counts and within-year decimal shares."""

    _validate_statuses(df)
    counts = pd.crosstab(df["year_added"], df["knownRansomwareCampaignUse"])
    counts = counts.reindex(columns=STATUS_ORDER, fill_value=0)
    counts = counts.rename(columns={"Known": "known_count", "Unknown": "unknown_count"})
    counts["total_count"] = counts["known_count"] + counts["unknown_count"]
    denominator = counts["total_count"].replace(0, pd.NA)
    counts["known_share"] = (counts["known_count"] / denominator).fillna(0.0)
    counts["unknown_share"] = (counts["unknown_count"] / denominator).fillna(0.0)
    return counts.reset_index(names="year")


def analyze_ransomware(df: pd.DataFrame) -> AnalysisArtifacts:
    """Build ransomware tables with interpretation notes."""

    summary = build_ransomware_summary(df)
    annual = build_ransomware_by_year(df)
    return AnalysisArtifacts(
        tables={"ransomware_summary": summary, "ransomware_by_year": annual},
        metrics={
            row.status.lower() + "_count": int(row.count)
            for row in summary.itertuples(index=False)
        },
        notes=[
            "Unknown means CISA has not confirmed ransomware campaign use; it is not negative evidence.",
            "Shares are stored as decimals in [0, 1] and should only be formatted as percentages for display.",
        ],
    )

