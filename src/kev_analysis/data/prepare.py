"""Deterministic preparation of validated KEV records."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from kev_analysis.constants import ORIGINAL_COLUMNS


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    """Return a prepared copy while retaining every original field."""

    missing = [column for column in ORIGINAL_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Cannot prepare data; missing columns: {missing}")

    prepared = df.copy(deep=True)
    # Copy list objects as well so callers cannot mutate the source through them.
    prepared["cwes"] = prepared["cwes"].map(
        lambda value: list(value) if isinstance(value, list) else value
    )
    prepared["vendor_clean"] = prepared["vendorProject"].str.strip()
    prepared["product_clean"] = prepared["product"].str.strip()
    prepared["date_added"] = pd.to_datetime(
        prepared["dateAdded"], format="%Y-%m-%d", errors="raise"
    )
    prepared["due_date"] = pd.to_datetime(
        prepared["dueDate"], format="%Y-%m-%d", errors="raise"
    )
    prepared["deadline_days"] = (
        prepared["due_date"] - prepared["date_added"]
    ).dt.days.astype("int64")
    prepared["year_added"] = prepared["date_added"].dt.year.astype("int64")
    prepared["month_added"] = prepared["date_added"].dt.strftime("%Y-%m")
    return prepared


def serialize_cwes(value: object) -> str:
    """Serialize an in-memory CWE list for a flat CSV export."""

    if not isinstance(value, list):
        raise TypeError("cwes must be a list before CSV serialization")
    return "|".join(value)


def export_prepared_data(df: pd.DataFrame, path: str | Path) -> Path:
    """Export prepared data without changing its in-memory list column."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    exported = df.copy(deep=True)
    exported["cwes"] = exported["cwes"].map(serialize_cwes)
    exported.to_csv(destination, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
    return destination

