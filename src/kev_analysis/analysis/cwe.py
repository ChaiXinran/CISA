"""CWE expansion and summaries for the prepared KEV dataset."""

from __future__ import annotations

import pandas as pd

from .vendor import AnalysisArtifacts, _require_columns

EXPLODED_COLUMNS = [
    "cveID", "date_added", "year_added", "vendor_clean", "product_clean",
    "knownRansomwareCampaignUse", "cwe",
]


def explode_cwes(df: pd.DataFrame) -> pd.DataFrame:
    """Expand non-empty CWE lists into a separate table; never fill empty lists."""
    required = set(EXPLODED_COLUMNS) - {"cwe"}
    required.add("cwes")
    _require_columns(df, required)
    mask = df["cwes"].map(lambda value: isinstance(value, list) and len(value) > 0)
    exploded = df.loc[mask, list(required)].copy().explode("cwes")
    exploded = exploded.rename(columns={"cwes": "cwe"})
    return exploded[EXPLODED_COLUMNS].reset_index(drop=True)


def build_cwe_summary(exploded_df: pd.DataFrame, records_with_cwe: int) -> pd.DataFrame:
    """Summarize CWE occurrence using the assignment's subset denominators."""
    _require_columns(exploded_df, {"cveID", "cwe", "knownRansomwareCampaignUse"})
    unique_status_records = exploded_df.drop_duplicates("cveID")
    known_denominator = int(
        unique_status_records.loc[
            unique_status_records["knownRansomwareCampaignUse"].eq("Known"), "cveID"
        ].nunique()
    )
    unknown_denominator = int(
        unique_status_records.loc[
            unique_status_records["knownRansomwareCampaignUse"].eq("Unknown"), "cveID"
        ].nunique()
    )
    rows = []
    for cwe, group in exploded_df.groupby("cwe", sort=False):
        unique = group.drop_duplicates(["cwe", "cveID"])
        known = int((unique["knownRansomwareCampaignUse"] == "Known").sum())
        unknown = int((unique["knownRansomwareCampaignUse"] == "Unknown").sum())
        count = int(unique["cveID"].nunique())
        rows.append({
            "cwe": cwe, "cve_count": count,
            "record_share": count / records_with_cwe if records_with_cwe else 0.0,
            "known_count": known, "unknown_count": unknown,
            "known_share": known / known_denominator if known_denominator else 0.0,
            "unknown_share": unknown / unknown_denominator if unknown_denominator else 0.0,
        })
    result = pd.DataFrame(rows, columns=[
        "cwe", "cve_count", "record_share", "known_count", "unknown_count",
        "known_share", "unknown_share",
    ])
    if result.empty:
        result.insert(0, "rank", pd.Series(dtype="int64"))
        return result
    result = result.sort_values(["cve_count", "cwe"], ascending=[False, True], kind="mergesort")
    result = result.reset_index(drop=True)
    result.insert(0, "rank", result.index + 1)
    return result


def build_cwe_by_year(exploded_df: pd.DataFrame) -> pd.DataFrame:
    """Count unique CVEs by year and CWE with stable ordering."""
    _require_columns(exploded_df, {"year_added", "cwe", "cveID"})
    return (
        exploded_df.groupby(["year_added", "cwe"], as_index=False)["cveID"]
        .nunique().rename(columns={"cveID": "cve_count"})
        .sort_values(["year_added", "cve_count", "cwe"], ascending=[True, False, True], kind="mergesort")
        .reset_index(drop=True)
    )


def run_cwe_analysis(df: pd.DataFrame) -> AnalysisArtifacts:
    """Build all B-line CWE tables and figures."""
    from kev_analysis.visualization.cwe_charts import build_cwe_figures

    exploded = explode_cwes(df)
    records_with_cwe = int(df["cwes"].map(bool).sum())
    summary = build_cwe_summary(exploded, records_with_cwe)
    by_year = build_cwe_by_year(exploded)
    comparison = summary[[
        "cwe", "cve_count", "known_count", "unknown_count", "known_share", "unknown_share"
    ]].copy()
    return AnalysisArtifacts(
        tables={
            "cwe_exploded": exploded,
            "cwe_summary": summary,
            "cwe_by_year": by_year,
            "cwe_ransomware_comparison": comparison,
        },
        metrics={
            "records_with_cwe": records_with_cwe,
            "records_without_cwe": int((~df["cwes"].map(bool)).sum()),
            "known_records_with_cwe": int(
                df.loc[df["knownRansomwareCampaignUse"].eq("Known"), "cwes"].map(bool).sum()
            ),
            "unknown_records_with_cwe": int(
                df.loc[df["knownRansomwareCampaignUse"].eq("Unknown"), "cwes"].map(bool).sum()
            ),
            "distinct_cwes": int(summary.shape[0]),
        },
        figures=build_cwe_figures(summary, by_year),
        notes=["Empty CWE lists are retained in prepared data and excluded only from the exploded table."],
    )
