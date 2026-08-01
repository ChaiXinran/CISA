"""Run the complete KEV analysis pipeline and build the offline HTML report."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from kev_analysis.analysis import (  # noqa: E402
    analyze_ransomware,
    run_cwe_analysis,
    run_query_cases,
    run_temporal_analysis,
    run_vendor_analysis,
)
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
    vendor = run_vendor_analysis(prepared)
    cwe = run_cwe_analysis(prepared)
    queries = run_query_cases(prepared)

    for name, table in {**temporal.tables, **ransomware.tables}.items():
        export_table(table, args.output / "tables" / f"{name}.csv")
    for name, table in vendor.tables.items():
        export_table(table, args.output / "tables" / f"{name}.csv")
    export_table(cwe.tables["cwe_exploded"], args.output / "prepared/cwe_exploded.csv")
    for name in ("cwe_summary", "cwe_by_year", "cwe_ransomware_comparison"):
        export_table(cwe.tables[name], args.output / "tables" / f"{name}.csv")
    export_json(vendor.metrics["vendor_concentration"], args.output / "metrics/vendor_concentration.json")
    for name, table in queries.tables.items():
        query_name = name.removesuffix("_results")
        export_table(table, args.output / "queries" / f"{name}.csv")
        export_json(
            queries.metrics["query_summaries"][query_name],
            args.output / "queries" / f"{query_name}_summary.json",
        )
    export_json({"queries": queries.metrics["query_log"]}, args.output / "logs/query_log.json")
    figures = build_temporal_figures(
        temporal.tables["monthly_additions"], temporal.tables["annual_additions"],
        temporal.tables["deadline_frequency"], prepared,
        ransomware.tables["ransomware_summary"], ransomware.tables["ransomware_by_year"],
    )
    report = build_report(
        args.report, PROJECT_ROOT / "report/templates", metadata=metadata,
        validation=validation, field_quality=field_quality, temporal=temporal,
        ransomware=ransomware, vendor=vendor, cwe=cwe, queries=queries, figures=figures,
    )
    print(f"[PASS] Loaded, validated and prepared {len(prepared):,} records")
    print(
        f"[PASS] Temporal/ransomware analysis completed: "
        f"{len(temporal.tables) + len(ransomware.tables)} tables"
    )
    print(f"[PASS] Vendor analysis completed: {len(vendor.tables['vendor_summary']):,} labels")
    print(f"[PASS] CWE analysis completed: {len(cwe.tables['cwe_summary']):,} labels")
    print(f"[PASS] Query cases completed: {len(queries.tables)} cases")
    print(f"[PASS] Generated offline HTML report: {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
