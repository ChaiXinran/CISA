import pytest

from kev_analysis.analysis.vendor import (
    build_vendor_product_summary, build_vendor_summary, calculate_concentration,
)


def test_vendor_shares_are_decimal_and_sum_to_one(prepared_df):
    summary = build_vendor_summary(prepared_df)
    assert summary["share"].sum() == pytest.approx(1.0)
    assert summary["known_share"].between(0, 1).all()
    assert summary["unknown_share"].between(0, 1).all()


def test_vendor_summary_counts_unique_products(prepared_df):
    summary = build_vendor_summary(prepared_df).set_index("vendor_clean")
    assert summary.loc["Acme", "unique_product_count"] == 1
    assert summary.loc["acme Labs", "unique_product_count"] == 1
    assert summary.loc["Beta", "unique_product_count"] == 2


def test_vendor_product_ties_have_stable_order(prepared_df):
    summary = build_vendor_product_summary(prepared_df)
    tied = summary[summary["count"] == 1]
    pairs = list(zip(tied["vendor_clean"], tied["product_clean"]))
    assert pairs == sorted(pairs)


def test_concentration_uses_decimal_shares(prepared_df):
    summary = build_vendor_summary(prepared_df)
    metrics = calculate_concentration(summary)
    assert metrics["cr5"] == pytest.approx(1.0)
    assert metrics["hhi"] == pytest.approx((summary["share"] ** 2).sum())


def test_concentration_rejects_percent_units(prepared_df):
    summary = build_vendor_summary(prepared_df)
    summary["share"] *= 100
    with pytest.raises(ValueError):
        calculate_concentration(summary)
