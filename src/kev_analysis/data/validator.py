"""Structural, format and logical validation for the KEV snapshot."""

from __future__ import annotations

import re
from typing import Any

import pandas as pd

from kev_analysis.constants import (
    EXPECTED_RECORD_COUNT,
    EXPECTED_SHA256,
    ORIGINAL_COLUMNS,
    RANSOMWARE_VALUES,
    TOP_LEVEL_FIELDS,
)
from kev_analysis.models import ValidationResult

CVE_PATTERN = re.compile(r"^CVE-[0-9]{4}-[0-9]{4,19}$")
CWE_PATTERN = re.compile(r"^CWE-[0-9]+$")
REQUIRED_TEXT_COLUMNS = [
    "vendorProject",
    "product",
    "vulnerabilityName",
    "shortDescription",
    "requiredAction",
]


def _all_strings_match(series: pd.Series, pattern: re.Pattern[str]) -> bool:
    return bool(series.map(lambda value: isinstance(value, str) and bool(pattern.fullmatch(value))).all())


def _parse_strict_dates(series: pd.Series) -> pd.Series:
    valid_shape = series.map(
        lambda value: isinstance(value, str)
        and bool(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value))
    )
    parsed = pd.to_datetime(series.where(valid_shape), format="%Y-%m-%d", errors="coerce")
    return parsed


def build_field_quality(df: pd.DataFrame) -> pd.DataFrame:
    """Build per-field completeness and type statistics."""

    rows: list[dict[str, Any]] = []
    for column in df.columns:
        series = df[column]
        empty_string_count = int(
            series.map(lambda value: isinstance(value, str) and value.strip() == "").sum()
        )
        empty_list_count = int(series.map(lambda value: isinstance(value, list) and len(value) == 0).sum())
        observed_types = sorted({type(value).__name__ for value in series.dropna()})
        rows.append(
            {
                "field": column,
                "dtype": str(series.dtype),
                "observed_types": "|".join(observed_types),
                "non_null_count": int(series.notna().sum()),
                "null_count": int(series.isna().sum()),
                "empty_string_count": empty_string_count,
                "empty_list_count": empty_list_count,
            }
        )
    return pd.DataFrame(rows)


def validate_catalog(
    metadata: dict[str, Any],
    df: pd.DataFrame,
    *,
    expected_sha256: str | None = EXPECTED_SHA256,
    expected_record_count: int | None = EXPECTED_RECORD_COUNT,
) -> ValidationResult:
    """Validate course requirements and return all failures together."""

    checks: dict[str, bool] = {}
    statistics: dict[str, Any] = {}

    source_metadata_fields = set(metadata) - {"actualRecordCount", "sourcePath", "sha256"}
    checks["top_level_fields"] = source_metadata_fields == (TOP_LEVEL_FIELDS - {"vulnerabilities"})
    checks["original_fields"] = set(df.columns) == set(ORIGINAL_COLUMNS)
    checks["record_count_matches_metadata"] = metadata.get("count") == len(df)
    if expected_record_count is not None:
        checks["expected_record_count"] = len(df) == expected_record_count
    if expected_sha256 is not None:
        checks["sha256"] = str(metadata.get("sha256", "")).upper() == expected_sha256.upper()

    statistics.update(
        {
            "catalog_version": metadata.get("catalogVersion"),
            "date_released": metadata.get("dateReleased"),
            "metadata_count": metadata.get("count"),
            "actual_record_count": len(df),
            "sha256": metadata.get("sha256"),
        }
    )

    required_columns_present = set(ORIGINAL_COLUMNS).issubset(df.columns)
    checks["required_columns_present"] = required_columns_present
    if required_columns_present:
        cve = df["cveID"]
        checks["cve_nonempty"] = bool(cve.notna().all() and cve.map(lambda x: isinstance(x, str) and x != "").all())
        checks["cve_format"] = _all_strings_match(cve, CVE_PATTERN)
        checks["cve_unique"] = bool(cve.is_unique)

        date_added = _parse_strict_dates(df["dateAdded"])
        due_date = _parse_strict_dates(df["dueDate"])
        checks["date_added_valid"] = bool(date_added.notna().all())
        checks["due_date_valid"] = bool(due_date.notna().all())
        checks["due_not_before_added"] = bool(
            date_added.notna().all() and due_date.notna().all() and (due_date >= date_added).all()
        )

        ransomware_values = set(df["knownRansomwareCampaignUse"].dropna().unique())
        checks["ransomware_values"] = bool(
            df["knownRansomwareCampaignUse"].notna().all()
            and ransomware_values.issubset(RANSOMWARE_VALUES)
        )
        checks["cwes_are_lists"] = bool(df["cwes"].map(lambda value: isinstance(value, list)).all())
        checks["cwe_values_valid"] = bool(
            df["cwes"].map(
                lambda value: isinstance(value, list)
                and all(isinstance(cwe, str) and CWE_PATTERN.fullmatch(cwe) for cwe in value)
            ).all()
        )
        checks["required_text_complete"] = all(
            df[column].notna().all()
            and df[column].map(lambda value: isinstance(value, str) and value.strip() != "").all()
            for column in REQUIRED_TEXT_COLUMNS
        )

        statistics.update(
            {
                "unique_cve_count": int(cve.nunique(dropna=True)),
                "empty_cwe_records": int(df["cwes"].map(lambda value: isinstance(value, list) and not value).sum()),
                "vendor_with_outer_whitespace": int(
                    df["vendorProject"].map(lambda value: isinstance(value, str) and value != value.strip()).sum()
                ),
                "product_with_outer_whitespace": int(
                    df["product"].map(lambda value: isinstance(value, str) and value != value.strip()).sum()
                ),
                "ransomware_counts": {
                    str(key): int(value)
                    for key, value in df["knownRansomwareCampaignUse"].value_counts().items()
                },
            }
        )

    errors = [name for name, passed in checks.items() if not passed]
    warnings: list[str] = []
    empty_cwes = statistics.get("empty_cwe_records", 0)
    if empty_cwes:
        warnings.append(f"{empty_cwes} records have empty CWE lists; they are retained as supplied.")

    return ValidationResult(
        passed=not errors,
        checks=checks,
        statistics=statistics,
        errors=errors,
        warnings=warnings,
    )

