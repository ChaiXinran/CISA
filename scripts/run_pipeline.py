"""Run the implemented A-line pipeline and build the offline HTML report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from kev_analysis.analysis import analyze_ransomware, run_temporal_analysis  # noqa: E402
from kev_analysis.data import (  # noqa: E402
    build_field_quality, export_prepared_data, load_catalog, prepare_data, validate_catalog,
)
from kev_analysis.reporting import build_report  # noqa: E402
from kev_analysis.utils import export_json, export_table  # noqa: E402
from kev_analysis.visualization import build_temporal_figures  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    parser.add_argument("--report", type=Path, default=Path("report/output/kev_report.html"))
    args = parser.parse_args()

    metadata, raw = load_catalog(args.input)
    validation = validate_catalog(metadata, raw)
    field_quality = build_field_quality(raw)
    export_json(metadata, args.output / "metrics/catalog_metadata.json")
    export_json(validation.to_dict(), args.output / "metrics/validation_report.json")
    export_table(field_quality, args.output / "tables/field_quality.csv")
    if not validation.passed:
        print(f"[FAIL] Validation failed: {', '.join(validation.errors)}", file=sys.stderr)
        return 1

    prepared = prepare_data(raw)
    export_prepared_data(prepared, args.output / "prepared/kev_prepared.csv")
    temporal = run_temporal_analysis(prepared)
    ransomware = analyze_ransomware(prepared)
    for name, table in {**temporal.tables, **ransomware.tables}.items():
        export_table(table, args.output / "tables" / f"{name}.csv")
    figures = build_temporal_figures(
        temporal.tables["monthly_additions"], temporal.tables["annual_additions"],
        temporal.tables["deadline_frequency"], prepared,
        ransomware.tables["ransomware_summary"], ransomware.tables["ransomware_by_year"],
    )
    report = build_report(
        args.report, PROJECT_ROOT / "report/templates", metadata=metadata,
        validation=validation, field_quality=field_quality, temporal=temporal,
        ransomware=ransomware, figures=figures,
    )
    print(f"[PASS] Loaded, validated and prepared {len(prepared):,} records")
    print(f"[PASS] Exported {len(temporal.tables) + len(ransomware.tables)} analysis tables")
    print(f"[PASS] Generated offline HTML report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
