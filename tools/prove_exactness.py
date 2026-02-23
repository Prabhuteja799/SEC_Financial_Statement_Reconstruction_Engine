"""Generate evidence reports for reconstruction quality across multiple SEC filings.

This script helps prove the engine is not only implemented, but consistently correct.
It runs batch validation, summarizes outcomes, and optionally saves per-filing reports.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.engine import FinancialStatementEngine


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def build_sample_adsh_list(
    engine: FinancialStatementEngine,
    limit: int,
    forms: list[str] | None = None,
    unique_cik: bool = False,
) -> list[str]:
    submissions = engine.submission_parser.get_all_submissions() if engine.submission_parser else None
    if submissions is None or submissions.empty:
        return []

    df = submissions.copy()
    if forms:
        form_set = {f.strip().upper() for f in forms if f.strip()}
        df = df[df["form"].astype(str).str.upper().isin(form_set)]

    df = df[df["adsh"].notna()].copy()
    df = df.sort_values(["filed", "adsh"], ascending=[False, True], kind="stable")

    if unique_cik and "cik" in df.columns:
        df = df.drop_duplicates(subset=["cik"], keep="first")

    return df["adsh"].astype(str).head(limit).tolist()


def summarize_batch_report(batch: dict[str, Any]) -> dict[str, Any]:
    results = batch.get("results", {})
    coverage_values: list[float] = []
    structural_failures = 0
    context_warnings = 0
    subtotal_failures = 0
    duplicate_candidate_rows = 0
    per_statement_pass_counts: dict[str, int] = {}
    per_statement_total_counts: dict[str, int] = {}

    for adsh, report in results.items():
        _ = adsh
        summary = report.get("summary", {})
        duplicate_candidate_rows += int(summary.get("duplicate_candidate_rows", 0) or 0)
        structural_failures += int(summary.get("structural_failures", 0) or 0)
        context_warnings += int(summary.get("context_warnings", 0) or 0)
        subtotal_failures += int(summary.get("subtotal_failures", 0) or 0)

        statements = report.get("statements", {})
        for stmt_code, stmt in statements.items():
            cov = _safe_float(stmt.get("coverage", {}).get("coverage_ratio"))
            coverage_values.append(cov)
            per_statement_total_counts[stmt_code] = per_statement_total_counts.get(stmt_code, 0) + 1

            structural_ok = bool(stmt.get("structural_parity", {}).get("passed", True))
            context_ok = bool(stmt.get("context_coherence", {}).get("passed", True))
            subtotals = stmt.get("subtotal_checks", []) or []
            subtotal_ok = all(bool(check.get("passed", False)) for check in subtotals) if subtotals else True
            if structural_ok and context_ok and subtotal_ok:
                per_statement_pass_counts[stmt_code] = per_statement_pass_counts.get(stmt_code, 0) + 1

    avg_coverage = sum(coverage_values) / len(coverage_values) if coverage_values else 0.0
    min_coverage = min(coverage_values) if coverage_values else 0.0

    per_statement_health = {}
    for code in sorted(per_statement_total_counts):
        total = per_statement_total_counts[code]
        passed = per_statement_pass_counts.get(code, 0)
        per_statement_health[code] = {
            "pass_count": passed,
            "total_count": total,
            "pass_ratio": (passed / total) if total else 0.0,
        }

    return {
        "batch_count": int(batch.get("count", 0)),
        "status_counts": batch.get("status_counts", {}),
        "avg_statement_coverage_ratio": avg_coverage,
        "min_statement_coverage_ratio": min_coverage,
        "aggregate_structural_failures": structural_failures,
        "aggregate_context_warnings": context_warnings,
        "aggregate_subtotal_failures": subtotal_failures,
        "aggregate_duplicate_candidate_rows": duplicate_candidate_rows,
        "per_statement_health": per_statement_health,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate proof reports for reconstruction exactness.")
    parser.add_argument(
        "--data-dir",
        default="2024q4",
        help="Directory containing SEC dataset files (sub.txt, num.txt, pre.txt, tag.txt).",
    )
    parser.add_argument("--limit", type=int, default=10, help="Number of filings to validate.")
    parser.add_argument(
        "--forms",
        default="10-Q,10-K",
        help="Comma-separated SEC forms to include (example: 10-Q,10-K).",
    )
    parser.add_argument(
        "--unique-cik",
        action="store_true",
        help="Pick at most one filing per company for a broader sample.",
    )
    parser.add_argument(
        "--statement-codes",
        default="BS,IS,CF,EQ,CI",
        help="Comma-separated statement codes to validate.",
    )
    parser.add_argument(
        "--out-dir",
        default="proof_reports",
        help="Output directory for summary + per-filing reports.",
    )
    parser.add_argument(
        "--save-per-filing",
        action="store_true",
        help="Write one JSON report per filing in addition to batch summaries.",
    )
    args = parser.parse_args()

    forms = [f.strip() for f in args.forms.split(",") if f.strip()]
    statement_codes = [s.strip() for s in args.statement_codes.split(",") if s.strip()]

    engine = FinancialStatementEngine(Path(args.data_dir))
    adsh_list = build_sample_adsh_list(
        engine=engine,
        limit=args.limit,
        forms=forms or None,
        unique_cik=args.unique_cik,
    )
    if not adsh_list:
        raise SystemExit("No filings found for the requested filters.")

    batch = engine.validate_filings_batch(adsh_list, statement_codes=statement_codes)
    summary = summarize_batch_report(batch)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "batch_report.json").write_text(json.dumps(batch, indent=2), encoding="utf-8")
    (out_dir / "summary_scoreboard.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if args.save_per_filing:
        filings_dir = out_dir / "filings"
        filings_dir.mkdir(parents=True, exist_ok=True)
        for adsh, report in batch.get("results", {}).items():
            safe_name = adsh.replace("/", "_")
            (filings_dir / f"{safe_name}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("Proof report generated")
    print(f"Filings checked: {summary['batch_count']}")
    print(f"Status counts: {summary['status_counts']}")
    print(f"Average statement coverage: {summary['avg_statement_coverage_ratio']:.4f}")
    print(f"Minimum statement coverage: {summary['min_statement_coverage_ratio']:.4f}")
    print(f"Output directory: {out_dir}")
    print("Use this as evidence that the engine behavior is consistent across multiple filings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
