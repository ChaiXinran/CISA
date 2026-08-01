"""Run the A-line data, temporal, deadline and ransomware pipeline."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from kev_analysis.analysis import analyze_ransomware, run_temporal_analysis  # noqa: E402
from kev_analysis.data import load_catalog, prepare_data, validate_catalog  # noqa: E402
from kev_analysis.utils import export_json, export_table  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata, raw = load_catalog(args.input)
    validation = validate_catalog(metadata, raw)
    if not validation.passed:
        print(f"[FAIL] Validation failed: {', '.join(validation.errors)}", file=sys.stderr)
        return 1

    prepared = prepare_data(raw)
    temporal = run_temporal_analysis(prepared)
    ransomware = analyze_ransomware(prepared)
    for name, table in {**temporal.tables, **ransomware.tables}.items():
        export_table(table, args.output / "tables" / f"{name}.csv")
    export_json(
        {
            "temporal": temporal.metrics,
            "ransomware": ransomware.metrics,
            "notes": temporal.notes + ransomware.notes,
        },
        args.output / "metrics" / "temporal_metrics.json",
    )
    print(f"[PASS] Temporal and deadline analysis exported ({len(temporal.tables)} tables)")
    print(f"[PASS] Ransomware analysis exported ({len(ransomware.tables)} tables)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

