import pandas as pd

from kev_analysis.analysis.cwe import build_cwe_summary, explode_cwes


def test_empty_cwe_records_are_not_filled(prepared_df):
    exploded = explode_cwes(prepared_df)
    assert "CVE-2024-0003" not in set(exploded["cveID"])
    assert "Unknown" not in set(exploded["cwe"])


def test_multiple_cwes_are_exploded(prepared_df):
    exploded = explode_cwes(prepared_df)
    assert set(exploded.loc[exploded["cveID"] == "CVE-2025-0001", "cwe"]) == {"CWE-79", "CWE-89"}


def test_cwe_count_uses_unique_cve(prepared_df):
    exploded = explode_cwes(prepared_df)
    duplicated = pd.concat([exploded, exploded.iloc[[0]]], ignore_index=True)
    summary = build_cwe_summary(duplicated, len(prepared_df))
    assert summary.loc[summary["cwe"] == "CWE-79", "cve_count"].item() == 2


def test_cwe_shares_use_assignment_denominators(prepared_df):
    exploded = explode_cwes(prepared_df)
    records_with_cwe = prepared_df["cwes"].map(bool).sum()
    summary = build_cwe_summary(exploded, records_with_cwe).set_index("cwe")
    unique = exploded.drop_duplicates("cveID")
    known_denominator = unique["knownRansomwareCampaignUse"].eq("Known").sum()
    unknown_denominator = unique["knownRansomwareCampaignUse"].eq("Unknown").sum()
    assert summary.loc["CWE-79", "record_share"] == 2 / records_with_cwe
    assert summary.loc["CWE-79", "known_share"] == 1 / known_denominator
    assert summary.loc["CWE-79", "unknown_share"] == 1 / unknown_denominator
