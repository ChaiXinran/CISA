from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from kev_analysis.constants import EXPECTED_SHA256, ORIGINAL_COLUMNS
from kev_analysis.data import load_catalog, prepare_data, serialize_cwes, validate_catalog


class DataLayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.metadata, cls.raw = load_catalog(PROJECT_ROOT / "data" / "CISA_KEV_2026-07-29.json")

    def test_loader_preserves_catalog_structure(self) -> None:
        self.assertEqual(self.metadata["catalogVersion"], "2026.07.29")
        self.assertEqual(self.metadata["count"], 1656)
        self.assertEqual(len(self.raw), 1656)
        self.assertEqual(set(self.raw.columns), set(ORIGINAL_COLUMNS))
        self.assertTrue(self.raw["cwes"].map(lambda value: isinstance(value, list)).all())
        self.assertEqual(self.metadata["sha256"], EXPECTED_SHA256)

    def test_course_snapshot_passes_validation(self) -> None:
        result = validate_catalog(self.metadata, self.raw)
        self.assertTrue(result.passed, result.errors)
        self.assertEqual(result.statistics["empty_cwe_records"], 171)
        self.assertEqual(result.statistics["vendor_with_outer_whitespace"], 6)
        self.assertEqual(result.statistics["product_with_outer_whitespace"], 10)

    def test_prepare_preserves_original_fields_and_input(self) -> None:
        original_vendor = self.raw["vendorProject"].copy(deep=True)
        original_cwes = [list(value) for value in self.raw["cwes"]]
        prepared = prepare_data(self.raw)

        self.assertTrue(original_vendor.equals(self.raw["vendorProject"]))
        self.assertEqual(original_cwes, self.raw["cwes"].tolist())
        self.assertEqual(prepared[ORIGINAL_COLUMNS].columns.tolist(), ORIGINAL_COLUMNS)
        self.assertTrue((prepared["vendor_clean"] == self.raw["vendorProject"].str.strip()).all())
        self.assertTrue((prepared["product_clean"] == self.raw["product"].str.strip()).all())
        self.assertTrue((prepared["deadline_days"] >= 0).all())
        self.assertEqual(prepared["month_added"].str.fullmatch(r"\d{4}-\d{2}").sum(), 1656)

    def test_prepared_cwe_lists_do_not_alias_input_lists(self) -> None:
        prepared = prepare_data(self.raw)
        row = next(index for index, value in enumerate(prepared["cwes"]) if value)
        original = list(self.raw.iloc[row]["cwes"])
        prepared.iloc[row]["cwes"].append("CWE-999999")
        self.assertEqual(self.raw.iloc[row]["cwes"], original)

    def test_cwe_csv_serialization(self) -> None:
        self.assertEqual(serialize_cwes([]), "")
        self.assertEqual(serialize_cwes(["CWE-79", "CWE-89"]), "CWE-79|CWE-89")

    def test_validation_detects_invalid_enum(self) -> None:
        bad = self.raw.copy(deep=True)
        bad.loc[0, "knownRansomwareCampaignUse"] = "No"
        result = validate_catalog(self.metadata, bad)
        self.assertFalse(result.passed)
        self.assertIn("ransomware_values", result.errors)


if __name__ == "__main__":
    unittest.main()

