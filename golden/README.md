# Golden Files (Proof of "Exactly as Presented")

This folder is for **approved expected outputs** ("golden files").

The idea:
- Your engine reconstructs a statement table
- You manually verify it against the SEC filing rendering
- You save that approved output here as CSV
- Future test runs compare current output vs the approved CSV

## Why this matters

This is how you **prove** your project is correct across multiple filings, not just say it.

## Step-by-step (kid version)

1. Pick a filing (`ADSH`) and statement (`BS`, `IS`, `CF`, `EQ`, `CI`)
2. Run your engine and export the table
3. Compare it with the real SEC statement page
4. If it matches, save it as a CSV in this folder
5. Add it to `golden/manifest.json`
6. Run:

```bash
pytest tests/test_golden_regression.py -v
```

If your code changes later and breaks the layout/values, the test will fail and show where.

## Manifest format

```json
{
  "cases": [
    {
      "adsh": "0001628280-24-043777",
      "stmt": "BS",
      "expected_csv": "golden/0001628280-24-043777_BS.csv"
    }
  ]
}
```

## Recommended columns to keep in the CSV

- `report`
- `line`
- `inpth`
- `tag`
- `label`
- `formatted_value`
- `ddate`
- `qtrs`

These columns prove both structure and displayed values.
