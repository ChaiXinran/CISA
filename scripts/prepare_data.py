"""Validate and prepare the frozen course dataset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from kev_analysis.data import (  # noqa: E402
    build_field_quality,
    export_prepared_data,
    load_catalog,
    prepare_data,
    validate_catalog,
)
from kev_analysis.utils import export_json, export_table  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata, raw_df = load_catalog(args.input)
    validation = validate_catalog(metadata, raw_df)

    export_json(metadata, args.output / "metrics" / "catalog_metadata.json")
    export_json(validation.to_dict(), args.output / "metrics" / "validation_report.json")
    export_table(build_field_quality(raw_df), args.output / "tables" / "field_quality.csv")

    if not validation.passed:
        print(f"[FAIL] Validation failed: {', '.join(validation.errors)}", file=sys.stderr)
        return 1

    prepared = prepare_data(raw_df)
    export_prepared_data(prepared, args.output / "prepared" / "kev_prepared.csv")
    print(f"[PASS] SHA-256 verified: {metadata['sha256']}")
    print(f"[PASS] Loaded and validated {len(prepared):,} records")
    print(f"[PASS] Prepared data exported to {args.output / 'prepared' / 'kev_prepared.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

