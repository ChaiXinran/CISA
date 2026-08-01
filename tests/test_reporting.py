from __future__ import annotations

import sys
import tempfile
import unittest
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kev_analysis.analysis import analyze_ransomware, run_temporal_analysis
from kev_analysis.data import build_field_quality, load_catalog, prepare_data, validate_catalog
from kev_analysis.reporting import build_report
from kev_analysis.visualization import build_temporal_figures


class ReportingTests(unittest.TestCase):
    def test_report_is_self_contained(self) -> None:
        metadata, raw = load_catalog(PROJECT_ROOT / "data/CISA_KEV_2026-07-29.json")
        validation = validate_catalog(metadata, raw)
        prepared = prepare_data(raw)
        temporal = run_temporal_analysis(prepared)
        ransomware = analyze_ransomware(prepared)
        figures = build_temporal_figures(
            temporal.tables["monthly_additions"], temporal.tables["annual_additions"],
            temporal.tables["deadline_frequency"], prepared,
            ransomware.tables["ransomware_summary"], ransomware.tables["ransomware_by_year"],
        )
        with tempfile.TemporaryDirectory() as directory:
            output = build_report(
                Path(directory) / "report.html", PROJECT_ROOT / "report/templates",
                metadata=metadata, validation=validation,
                field_quality=build_field_quality(raw), temporal=temporal,
                ransomware=ransomware, figures=figures,
            )
            html = output.read_text(encoding="utf-8")
        self.assertIn("KEV 冻结快照分析报告", html)
        self.assertIn("plotly.js", html.lower())
        self.assertIsNone(re.search(r'<script[^>]+src=["\']https?://', html, re.IGNORECASE))
        self.assertIn("1,656", html)


if __name__ == "__main__":
    unittest.main()
