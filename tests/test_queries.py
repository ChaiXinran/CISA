import pandas as pd
import pytest

from kev_analysis.analysis.queries import filter_kev, run_query_cases


def test_date_filter_is_closed_interval(prepared_df):
    result, _ = filter_kev(prepared_df, start_date="2025-01-01", end_date="2025-01-31")
    assert set(result["cveID"]) == {"CVE-2025-0001", "CVE-2025-0002", "CVE-2025-0004"}


def test_vendor_filter_is_case_insensitive_substring(prepared_df):
    result, _ = filter_kev(prepared_df, vendor="ACME")
    assert set(result["vendor_clean"]) == {"Acme", "acme Labs"}


def test_product_filter_is_case_insensitive_substring(prepared_df):
    result, summary = filter_kev(prepared_df, product="one")
    assert set(result["product_clean"]) == {"One"}
    assert summary["filters"]["product"] == "one"


def test_invalid_ransomware_raises_value_error(prepared_df):
    with pytest.raises(ValueError):
        filter_kev(prepared_df, ransomware="No")


def test_cwe_filter_is_exact_match(prepared_df):
    result, _ = filter_kev(prepared_df, cwe="cwe-79")
    assert set(result["cveID"]) == {"CVE-2025-0001", "CVE-2025-0002"}
    result, _ = filter_kev(prepared_df, cwe="CWE-7")
    assert result.empty


@pytest.mark.parametrize("invalid", ["79", "CWE-79x", " CWE-79 ", "CWE-"])
def test_invalid_cwe_raises_value_error(prepared_df, invalid):
    with pytest.raises(ValueError, match="CWE"):
        filter_kev(prepared_df, cwe=invalid)


def test_all_conditions_use_and(prepared_df):
    result, _ = filter_kev(prepared_df, vendor="acme", ransomware="Known", cwe="CWE-89")
    assert list(result["cveID"]) == ["CVE-2025-0001"]


def test_filter_does_not_mutate_input(prepared_df):
    before = prepared_df.copy(deep=True)
    filter_kev(prepared_df, vendor="acme")
    pd.testing.assert_frame_equal(prepared_df, before)


def test_result_sort_order(prepared_df):
    result, _ = filter_kev(prepared_df)
    assert list(result["cveID"][:2]) == ["CVE-2025-0002", "CVE-2025-0004"]


def test_three_query_cases_are_exposed(prepared_df):
    artifacts = run_query_cases(prepared_df)
    assert len(artifacts.tables) == 3
    assert len(artifacts.metrics["query_summaries"]) == 3


def test_query_summary_includes_known_count_and_handles_empty(prepared_df):
    result, summary = filter_kev(prepared_df, vendor="does-not-exist")
    assert result.empty
    assert summary["result_count"] == 0
    assert summary["unique_vendors"] == 0
    assert summary["known_count"] == 0
    assert summary["date_max"] is None
