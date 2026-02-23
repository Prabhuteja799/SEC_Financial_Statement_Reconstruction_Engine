# Setup Guide

## Installation Steps

### 1. Create Virtual Environment

```bash
cd /Users/prabhutejachintala/Documents/SEC_Financial_Statement_Reconstruction_Engine
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Quick Start Test

```bash
python quickstart.py
```

### 4. Run Examples

```bash
python examples.py
```

### 5. Run Tests

```bash
pytest tests/ -v
```

### 6. Run Proof Scorecard (Multi-Filing Validation)

```bash
python tools/prove_exactness.py --limit 10 --unique-cik --save-per-filing
```

This creates:
- `proof_reports/summary_scoreboard.json`
- `proof_reports/batch_report.json`
- `proof_reports/filings/*.json` (when `--save-per-filing` is used)

### 7. Create Golden CSVs (Strict Regression Proof)

Export approved statement tables for a filing:

```bash
python tools/export_golden_csv.py --adsh 0001628280-24-043777 --stmt BS
```

After manual approval against the SEC filing, add the CSV to `golden/manifest.json`, then run:

```bash
pytest tests/test_golden_regression.py -v
```

## Project Structure

- `src/` - Main engine code
  - `parsers/` - XBRL file format parsers
  - `models/` - Pydantic data models
  - `core/` - Engine and reconstruction logic

- `2024q4/` - Sample SEC XBRL data (Q4 2024 filings)

- `examples.py` - Comprehensive usage examples

- `quickstart.py` - Quick test to verify installation

- `tests/` - Unit test suite
- `golden/` - Approved golden CSV outputs + manifest for strict regression proof
- `tools/` - Proof helpers (`prove_exactness.py`, `export_golden_csv.py`)

- `requirements.txt` - Python dependencies

## Key Components

### Parsers
- **SubmissionParser** - Parses sub.txt (filing metadata)
- **NumericParser** - Parses num.txt (financial values)
- **PresentationParser** - Parses pre.txt (statement structure)
- **TagParser** - Parses tag.txt (concept definitions)

### Engine
- **FinancialStatementEngine** - Main orchestration engine
- **StatementReconstructor** - Rebuilds traditional financial statements
- Includes table reconstruction, validation, export, and persistence APIs

### Models
- **Company** - Company information
- **BalanceSheet**, **IncomeStatement**, **CashFlowStatement** - Financial statements
- **FinancialStatement** - Complete filing package

## Usage Examples

### Basic Setup
```python
from pathlib import Path
from src.core.engine import FinancialStatementEngine

engine = FinancialStatementEngine(Path('2024q4'))
```

### Get Companies
```python
companies = engine.get_all_companies()
company = engine.get_company_info('789460')
```

### Get Filings
```python
filings = engine.get_filings_for_company('789460')
ten_qs = engine.filter_filings_by_form('10-Q')
```

### Reconstruct Statements
```python
from src.core.reconstructor import StatementReconstructor

reconstructor = StatementReconstructor(
    engine.numeric_parser,
    engine.presentation_parser,
    engine.tag_parser
)

balance_sheet = reconstructor.reconstruct_balance_sheet(adsh, company)
```

## Troubleshooting

### Virtual Environment Issues
Make sure venv is activated: `source venv/bin/activate`

### Import Errors
Check that you're running from the project root directory

### Missing Data Files
Ensure all files exist in 2024q4/:
- sub.txt
- num.txt
- pre.txt
- tag.txt

## Next Steps

1. ✓ Project structure created
2. ✓ Core modules implemented
3. ✓ Data models defined
4. ✓ Parsers developed
5. ✓ Tests passing
6. ✓ Proof scorecard tooling added
7. ✓ Golden regression tooling added
8. Next: Expand approved golden filing coverage (more companies/filings)
