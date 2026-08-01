"""Reusable AND-combined filters and three reproducible query cases."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import pandas as pd

from .vendor import AnalysisArtifacts, _require_columns


def _iso(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return pd.Timestamp(value).date().isoformat()


def filter_kev(
    df: pd.DataFrame,
    start_date=None,
    end_date=None,
    vendor=None,
    ransomware=None,
    cwe=None,
) -> tuple[pd.DataFrame, dict]:
    """Filter prepared KEV rows using AND semantics and return a summary."""
    _require_columns(df, {
        "cveID", "dateAdded", "date_added", "vendor_clean", "product_clean",
        "knownRansomwareCampaignUse", "cwes",
    })
    if ransomware not in {None, "Known", "Unknown"}:
        raise ValueError("ransomware must be 'Known', 'Unknown', or None")
    start = pd.Timestamp(start_date).normalize() if start_date is not None else None
    end = pd.Timestamp(end_date).normalize() if end_date is not None else None
    if start is not None and end is not None and start > end:
        raise ValueError("start_date must be on or before end_date")

    result = df.copy(deep=True)
    dates = pd.to_datetime(result["date_added"], errors="raise").dt.normalize()
    mask = pd.Series(True, index=result.index)
    if start is not None:
        mask &= dates >= start
    if end is not None:
        mask &= dates <= end
    if vendor is not None:
        mask &= result["vendor_clean"].astype(str).str.contains(
            str(vendor), case=False, regex=False, na=False
        )
    if ransomware is not None:
        mask &= result["knownRansomwareCampaignUse"].eq(ransomware)
    normalized_cwe = str(cwe).upper() if cwe is not None else None
    if normalized_cwe is not None:
        if re.fullmatch(r"CWE-[0-9]+", normalized_cwe) is None:
            raise ValueError("cwe must match the pattern ^CWE-[0-9]+$")
        mask &= result["cwes"].map(
            lambda values: isinstance(values, list)
            and normalized_cwe in {str(value).upper() for value in values}
        )

    result = result.loc[mask].copy()
    result["__sort_date"] = pd.to_datetime(result["dateAdded"], errors="raise")
    result = result.sort_values(
        ["__sort_date", "cveID"], ascending=[False, True], kind="mergesort"
    ).drop(columns="__sort_date").reset_index(drop=True)
    result_dates = pd.to_datetime(result["date_added"], errors="raise")
    summary = {
        "filters": {
            "start_date": _iso(start), "end_date": _iso(end), "vendor": vendor,
            "ransomware": ransomware, "cwe": normalized_cwe,
        },
        "result_count": int(len(result)),
        "unique_vendors": int(result["vendor_clean"].nunique()),
        "unique_products": int(result["product_clean"].nunique()),
        "known_count": int(result["knownRansomwareCampaignUse"].eq("Known").sum()),
        "date_min": _iso(result_dates.min()) if not result.empty else None,
        "date_max": _iso(result_dates.max()) if not result.empty else None,
    }
    return result, summary


DEFAULT_QUERY_CASES = [
    {"start_date": "2025-01-01", "end_date": "2025-12-31", "ransomware": "Known"},
    {"vendor": "Microsoft", "cwe": "CWE-79"},
    {
        "start_date": "2021-11-01", "end_date": "2026-07-29",
        "vendor": "Microsoft", "ransomware": "Known", "cwe": "CWE-20",
    },
]


def run_query_cases(
    df: pd.DataFrame,
    cases: list[dict[str, Any]] | None = None,
) -> AnalysisArtifacts:
    """Execute three default cases (or caller-supplied cases) without file I/O."""
    selected = DEFAULT_QUERY_CASES if cases is None else cases
    if len(selected) < 3:
        raise ValueError("at least three query cases are required")
    tables: dict[str, pd.DataFrame] = {}
    summaries: dict[str, dict] = {}
    for index, filters in enumerate(selected, start=1):
        name = f"query_{index:02d}"
        tables[f"{name}_results"] , summaries[name] = filter_kev(df, **filters)
    return AnalysisArtifacts(
        tables=tables,
        metrics={"query_summaries": summaries, "query_log": list(summaries.values())},
        figures={},
        notes=["All query conditions are combined with AND; date endpoints are inclusive."],
    )
