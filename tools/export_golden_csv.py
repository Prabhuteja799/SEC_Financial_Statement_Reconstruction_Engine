"""Export one reconstructed statement table to a CSV for golden regression approval."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.engine import FinancialStatementEngine


DEFAULT_COLUMNS = [
    "report",
    "line",
    "inpth",
    "tag",
    "label",
    "formatted_value",
    "ddate",
    "qtrs",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Export reconstructed statement table to golden CSV.")
    parser.add_argument("--adsh", required=True, help="Filing accession number")
    parser.add_argument("--stmt", required=True, help="Statement code (BS/IS/CF/EQ/CI)")
    parser.add_argument("--data-dir", default="2024q4", help="SEC dataset directory")
    parser.add_argument(
        "--out",
        default=None,
        help="Output CSV path (default: golden/<adsh>_<stmt>.csv)",
    )
    args = parser.parse_args()

    engine = FinancialStatementEngine(Path(args.data_dir))
    table = engine.reconstruct_statement_table(args.adsh, args.stmt)
    if table.empty:
        raise SystemExit(f"No rows reconstructed for {args.adsh} {args.stmt}")

    out_path = Path(args.out) if args.out else Path("golden") / f"{args.adsh}_{args.stmt}.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    cols = [c for c in DEFAULT_COLUMNS if c in table.columns]
    table[cols].to_csv(out_path, index=False)
    print(f"Exported {len(table)} rows to {out_path}")
    print("Now compare this CSV to the SEC filing manually before approving it as a golden file.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
