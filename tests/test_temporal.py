from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kev_analysis.analysis import (
    analyze_deadlines,
    build_annual_summary,
    build_monthly_series,
    build_ransomware_by_year,
    build_ransomware_summary,
)
from kev_analysis.data import load_catalog, prepare_data


class TemporalAnalysisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _, raw = load_catalog(PROJECT_ROOT / "data" / "CISA_KEV_2026-07-29.json")
        cls.prepared = prepare_data(raw)

    def test_monthly_series_is_continuous_and_complete(self) -> None:
        monthly = build_monthly_series(self.prepared)
        self.assertEqual(len(monthly), 57)
        self.assertEqual(monthly.iloc[0]["month"], "2021-11")
        self.assertEqual(monthly.iloc[-1]["month"], "2026-07")
        self.assertEqual(int(monthly["count"].sum()), 1656)
        self.assertAlmostEqual(float(monthly["share"].sum()), 1.0)

    def test_annual_coverage_marks_partial_years(self) -> None:
        annual = build_annual_summary(self.prepared).set_index("year")
        self.assertEqual(int(annual["count"].sum()), 1656)
        self.assertEqual(int(annual.loc[2021, "first_month"]), 11)
        self.assertEqual(int(annual.loc[2021, "months_covered"]), 2)
        self.assertFalse(bool(annual.loc[2021, "is_complete_year"]))
        self.assertEqual(int(annual.loc[2026, "last_month"]), 7)
        self.assertFalse(bool(annual.loc[2026, "is_complete_year"]))
        for year in [2022, 2023, 2024, 2025]:
            self.assertTrue(bool(annual.loc[year, "is_complete_year"]))

    def test_deadline_outputs_reconcile(self) -> None:
        result = analyze_deadlines(self.prepared)
        summary = result["deadline_summary"].set_index("metric")
        frequency = result["deadline_frequency"]
        annual = result["deadline_by_year"]
        self.assertEqual(int(summary.loc["count", "value"]), 1656)
        self.assertEqual(int(frequency["count"].sum()), 1656)
        self.assertAlmostEqual(float(frequency["share"].sum()), 1.0)
        self.assertEqual(int(annual["count"].sum()), 1656)

    def test_ransomware_overall_uses_decimal_shares(self) -> None:
        summary = build_ransomware_summary(self.prepared).set_index("status")
        self.assertEqual(int(summary.loc["Known", "count"]), 332)
        self.assertEqual(int(summary.loc["Unknown", "count"]), 1324)
        self.assertAlmostEqual(float(summary["share"].sum()), 1.0)
        self.assertTrue(summary["share"].between(0, 1).all())

    def test_ransomware_annual_denominators(self) -> None:
        annual = build_ransomware_by_year(self.prepared)
        self.assertEqual(int(annual["total_count"].sum()), 1656)
        self.assertTrue(annual["known_share"].between(0, 1).all())
        self.assertTrue(annual["unknown_share"].between(0, 1).all())
        self.assertTrue(((annual["known_share"] + annual["unknown_share"]) - 1).abs().lt(1e-12).all())


if __name__ == "__main__":
    unittest.main()

