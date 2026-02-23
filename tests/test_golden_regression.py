"""Golden regression checks for proving repeatable reconstruction outputs.

How to use:
1. Create `golden/manifest.json` with filings/statements to verify.
2. Export approved statement tables as CSV files into `golden/`.
3. Run `pytest tests/test_golden_regression.py -v`.

The test skips automatically when no manifest exists yet.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.core.engine import FinancialStatementEngine


DATA_DIR = Path(__file__).resolve().parents[1] / "2024q4"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = PROJECT_ROOT / "golden"
MANIFEST_PATH = GOLDEN_DIR / "manifest.json"

# Columns that define the visual structure + values seen by users.
DEFAULT_COMPARE_COLUMNS = [
    "report",
    "line",
    "inpth",
    "tag",
    "label",
    "formatted_value",
    "ddate",
    "qtrs",
]


def _normalize(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    existing = [c for c in columns if c in df.columns]
    view = df[existing].copy()
    # Normalize all compared columns to stable strings so CSV dtype inference
    # (e.g., ddate as int) does not cause false mismatches.
    for col in view.columns:
        series = view[col]
        if pd.api.types.is_float_dtype(series):
            # Avoid "1.0" vs "1" noise for identifier-like floats loaded from CSV.
            series = series.map(
                lambda v: "" if pd.isna(v) else (str(int(v)) if float(v).is_integer() else str(v))
            )
            view[col] = series.astype(str).str.strip()
            continue
        view[col] = series.fillna("").astype(str).str.strip()
    return view.reset_index(drop=True)


@pytest.mark.skipif(not MANIFEST_PATH.exists(), reason="No golden manifest configured yet.")
def test_golden_statement_tables():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    engine = FinancialStatementEngine(DATA_DIR)

    cases = manifest.get("cases", [])
    assert cases, "Golden manifest exists but has no cases."
    cases = [
        c
        for c in cases
        if "README_CREATE_FILES_FIRST" not in str(c.get("expected_csv", ""))
    ]
    if not cases:
        pytest.skip("Golden manifest contains only placeholders. Create approved CSVs first.")

    failures: list[str] = []

    for case in cases:
        adsh = case["adsh"]
        stmt = case["stmt"]
        csv_path = PROJECT_ROOT / case["expected_csv"]
        compare_columns = case.get("compare_columns", DEFAULT_COMPARE_COLUMNS)

        assert csv_path.exists(), f"Missing golden file: {csv_path}"

        actual = engine.reconstruct_statement_table(adsh, stmt)
        expected = pd.read_csv(csv_path)

        actual_norm = _normalize(actual, compare_columns)
        expected_norm = _normalize(expected, compare_columns)

        if len(actual_norm) != len(expected_norm):
            failures.append(
                f"{adsh} {stmt}: row count mismatch actual={len(actual_norm)} expected={len(expected_norm)}"
            )
            continue

        if list(actual_norm.columns) != list(expected_norm.columns):
            failures.append(
                f"{adsh} {stmt}: column mismatch actual={list(actual_norm.columns)} expected={list(expected_norm.columns)}"
            )
            continue

        unequal = actual_norm.ne(expected_norm)
        if unequal.any().any():
            idx = int(unequal.any(axis=1).idxmax())
            diff_cols = [c for c in actual_norm.columns if bool(unequal.loc[idx, c])]
            failures.append(
                f"{adsh} {stmt}: first mismatch at row={idx} cols={diff_cols} "
                f"actual={actual_norm.loc[idx, diff_cols].to_dict()} "
                f"expected={expected_norm.loc[idx, diff_cols].to_dict()}"
            )

    assert not failures, "Golden regression mismatches:\n" + "\n".join(failures)
