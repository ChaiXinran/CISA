"""Catalog addition and required-action deadline analysis."""

from __future__ import annotations

import pandas as pd

from kev_analysis.models import AnalysisArtifacts


def _require_columns(df: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in df.columns]
    if missing:
        raise ValueError(f"Missing prepared columns: {missing}")


def build_monthly_series(
    df: pd.DataFrame,
    start: str = "2021-11",
    end: str = "2026-07",
) -> pd.DataFrame:
    """Return a continuous inclusive monthly series for the frozen snapshot."""

    _require_columns(df, ["month_added"])
    months = pd.period_range(start=start, end=end, freq="M")
    observed = df["month_added"].astype(str).value_counts()
    result = pd.DataFrame({"month": months.astype(str)})
    result["count"] = result["month"].map(observed).fillna(0).astype("int64")
    result["share"] = result["count"] / len(df) if len(df) else 0.0
    return result


def build_annual_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Count records by year and describe the months covered by the snapshot."""

    _require_columns(df, ["date_added", "year_added"])
    if df.empty:
        return pd.DataFrame(
            columns=[
                "year", "count", "share", "first_month", "last_month",
                "months_covered", "is_complete_year",
            ]
        )

    work = df[["date_added", "year_added"]].copy()
    work["month_number"] = work["date_added"].dt.month
    grouped = work.groupby("year_added", sort=True)
    result = grouped.agg(
        count=("date_added", "size"),
        first_month=("month_number", "min"),
        last_month=("month_number", "max"),
    ).reset_index(names="year")

    # Coverage describes the catalog snapshot window, including months with zero additions.
    first_date = work["date_added"].min()
    last_date = work["date_added"].max()
    result["first_month"] = result["year"].map(
        lambda year: first_date.month if year == first_date.year else 1
    )
    result["last_month"] = result["year"].map(
        lambda year: last_date.month if year == last_date.year else 12
    )
    result["months_covered"] = result["last_month"] - result["first_month"] + 1
    result["is_complete_year"] = result["months_covered"].eq(12)
    result["share"] = result["count"] / len(df)
    return result[
        ["year", "count", "share", "first_month", "last_month", "months_covered", "is_complete_year"]
    ]


def analyze_deadlines(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Return overall statistics, full frequency and annual comparisons."""

    _require_columns(df, ["deadline_days", "year_added"])
    deadlines = df["deadline_days"]
    if deadlines.isna().any():
        raise ValueError("deadline_days contains null values")
    if (deadlines < 0).any():
        raise ValueError("deadline_days cannot be negative")

    summary = pd.DataFrame(
        {
            "metric": ["count", "minimum", "q1", "median", "mean", "q3", "maximum"],
            "value": [
                int(deadlines.count()),
                float(deadlines.min()),
                float(deadlines.quantile(0.25)),
                float(deadlines.median()),
                float(deadlines.mean()),
                float(deadlines.quantile(0.75)),
                float(deadlines.max()),
            ],
        }
    )

    frequency = deadlines.value_counts().sort_index().rename_axis("deadline_days").reset_index(name="count")
    frequency["share"] = frequency["count"] / len(df) if len(df) else 0.0

    annual = (
        df.groupby("year_added", sort=True)["deadline_days"]
        .agg(
            count="size",
            minimum="min",
            q1=lambda values: values.quantile(0.25),
            median="median",
            mean="mean",
            q3=lambda values: values.quantile(0.75),
            maximum="max",
        )
        .reset_index(names="year")
    )
    return {"deadline_summary": summary, "deadline_frequency": frequency, "deadline_by_year": annual}


def run_temporal_analysis(df: pd.DataFrame) -> AnalysisArtifacts:
    """Build all time and deadline tables using prepared data."""

    monthly = build_monthly_series(df)
    annual = build_annual_summary(df)
    deadlines = analyze_deadlines(df)
    return AnalysisArtifacts(
        tables={"monthly_additions": monthly, "annual_additions": annual, **deadlines},
        metrics={
            "total_records": len(df),
            "date_min": df["date_added"].min().strftime("%Y-%m-%d") if len(df) else None,
            "date_max": df["date_added"].max().strftime("%Y-%m-%d") if len(df) else None,
        },
        notes=[
            "2021 and 2026 are partial years in this frozen snapshot.",
            "dateAdded is the KEV catalog addition date, not a disclosure or attack date.",
            "deadline_days is the catalog action window, not observed remediation time.",
        ],
    )

