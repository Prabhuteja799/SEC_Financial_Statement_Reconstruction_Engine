# SEC Financial Statement Reconstruction Engine

A professional-grade Python engine for parsing, processing, and reconstructing financial statements from SEC XBRL filing packages.

## Overview

This engine processes SEC's XBRL (eXtensible Business Reporting Language) filing data and reconstructs traditional financial statements (Balance Sheet, Income Statement, Cash Flow Statement) in a structured, machine-readable format.

### Features

- **Multi-file XBRL Parser**: Handles sub.txt, num.txt, pre.txt, and tag.txt SEC XBRL files
- **Financial Statement Reconstruction**: Automatically builds balance sheets, income statements, and cash flow statements
- **Row-Accurate Statement Tables**: Rebuilds BS/IS/CF/EQ/CI tables in `pre.txt` order with mapped numeric values
- **Validation & Coverage Reports**: Per-statement coverage metrics, context checks, and subtotal diagnostics
- **Excel Export**: Export reconstructed filing statements to a multi-sheet workbook
- **PostgreSQL Persistence**: Persist statement rows and validation reports for downstream analytics
- **Data Validation**: Comprehensive integrity checking for filing data
- **Flexible Querying**: Query financial data by company, filing, date range, or statement type
- **Type-Safe Models**: Pydantic models for all financial entities
- **Extensible Architecture**: Easy to add custom analysis and transformations

## Project Structure

```
SEC_Financial_Statement_Reconstruction_Engine/
├── src/
│   ├── __init__.py
│   ├── parsers/              # XBRL file parsers
│   │   ├── __init__.py
│   │   ├── submission_parser.py    # sub.txt parser
│   │   ├── numeric_parser.py       # num.txt parser
│   │   ├── presentation_parser.py  # pre.txt parser
│   │   └── tag_parser.py           # tag.txt parser
│   ├── models/               # Pydantic data models
│   │   ├── __init__.py
│   │   ├── financial_entities.py   # Financial statement models
│   │   └── xbrl_models.py          # XBRL-specific models
│   ├── core/                 # Core engine logic
│   │   ├── __init__.py
│   │   ├── engine.py               # Main orchestration engine
│   │   └── reconstructor.py        # Statement reconstruction logic
│   └── storage/              # Optional persistence backends
│       ├── __init__.py
│       └── postgres_store.py       # PostgreSQL persistence for outputs
├── tests/                    # Unit tests
├── tools/                    # Proof helpers (scorecards + golden export)
│   ├── prove_exactness.py
│   └── export_golden_csv.py
├── golden/                   # Approved golden outputs + manifest
│   ├── manifest.json
│   └── *.csv
├── 2024q4/                   # Sample XBRL data files
│   ├── sub.txt              # Submission index
│   ├── num.txt              # Numeric facts
│   ├── pre.txt              # Presentation structure
│   ├── tag.txt              # Tag definitions
│   └── readme.htm           # SEC documentation
├── requirements.txt
├── README.md
└── .gitignore
```

## Installation

### Prerequisites
- Python 3.9+
- pip

### Setup

1. Clone or extract the project:
```bash
cd /Users/prabhutejachintala/Documents/SEC_Financial_Statement_Reconstruction_Engine
```

2. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Quick Start

```python
from pathlib import Path
from src.core.engine import FinancialStatementEngine

# Initialize engine with XBRL data directory
engine = FinancialStatementEngine(Path('2024q4'))

# Get all companies
companies = engine.get_all_companies()
print(companies)

# Get filings for a specific company
cik = '789460'  # World Kinect Corp
filings = engine.get_filings_for_company(cik)
print(filings)

# Get filing metadata
adsh = '0001628280-24-043777'
metadata = engine.get_filing_metadata(adsh)
print(metadata)
```

### Parser Examples

#### Submission Parser
```python
from src.parsers.submission_parser import SubmissionParser
from pathlib import Path

parser = SubmissionParser(Path('2024q4/sub.txt'))

# Get all submissions
all_subs = parser.get_all_submissions()

# Get company filings
company_filings = parser.get_company_filings('789460')

# Filter by form type
ten_ks = parser.filter_by_form_type('10-K')

# Filter by date range
recent = parser.filter_by_date_range('20240101', '20241231')
```

#### Numeric Parser
```python
from src.parsers.numeric_parser import NumericParser
from pathlib import Path

parser = NumericParser(Path('2024q4/num.txt'))

# Get all numeric facts
all_facts = parser.get_all_facts()

# Get facts for a filing
facts = parser.get_facts_by_adsh('0001628280-24-043777')

# Get balance sheet items (instant facts)
bs_items = parser.get_latest_balance_sheet_items('0001628280-24-043777')

# Get unit distribution
units = parser.get_units_used()
```

#### Presentation Parser
```python
from src.parsers.presentation_parser import PresentationParser
from pathlib import Path

parser = PresentationParser(Path('2024q4/pre.txt'))

# Get statement types available
statements = parser.get_statement_types_available('0001628280-24-043777')

# Get balance sheet structure
bs_structure = parser.get_statement_structure('0001628280-24-043777', 'BS')

# Get concept hierarchy path
path = parser.get_concept_path('0001628280-24-043777', 'Assets')
```

#### Tag Parser
```python
from src.parsers.tag_parser import TagParser
from pathlib import Path

parser = TagParser(Path('2024q4/tag.txt'))

# Get tag definition
definition = parser.get_tag_definition('Assets')

# Get tag label
label = parser.get_tag_label('Assets')

# Get numeric tags only
numeric = parser.get_numeric_tags()

# Check if debit or credit
is_debit = parser.is_debit_account('Assets')
```

### Statement Reconstruction

```python
from src.core.engine import FinancialStatementEngine
from src.core.reconstructor import StatementReconstructor
from pathlib import Path

engine = FinancialStatementEngine(Path('2024q4'))

# Get company
company = engine.get_company_info('789460')

# Create reconstructor
reconstructor = StatementReconstructor(
    engine.numeric_parser,
    engine.presentation_parser,
    engine.tag_parser
)

# Reconstruct statements
adsh = '0001628280-24-043777'
balance_sheet = reconstructor.reconstruct_balance_sheet(adsh, company)
income_statement = reconstructor.reconstruct_income_statement(adsh, company)
cash_flow = reconstructor.reconstruct_cash_flow_statement(adsh, company)

# Full statement package
full_statement = reconstructor.reconstruct_full_statement(
    adsh, 
    company,
    '2024-10-25'
)

# Access data
print(balance_sheet.assets)
print(income_statement.revenues)
print(cash_flow.operating_activities)
```

### Row-Accurate Statement Tables (Recommended for exports/analytics)

```python
from pathlib import Path
from src.core.engine import FinancialStatementEngine

engine = FinancialStatementEngine(Path("2024q4"))
adsh = "0001628280-24-043777"

# Reconstruct a single statement table in pre.txt line order
bs_table = engine.reconstruct_statement_table(adsh, "BS")
print(bs_table[["report", "line", "inpth", "label", "formatted_value"]].head(10))

# Reconstruct the full filing package (BS, IS, CF, EQ, CI)
tables = engine.reconstruct_filing_tables(adsh)
print(tables.keys())
```

### Validation, Excel Export, and PostgreSQL Persistence

```python
from pathlib import Path
from src.core.engine import FinancialStatementEngine

engine = FinancialStatementEngine(Path("2024q4"))
adsh = "0001628280-24-043777"

# Validation report with coverage + diagnostics
report = engine.validate_filing_reconstruction(adsh)
print(report["summary"])

# Excel export (requires openpyxl)
workbook = engine.export_filing_to_excel(adsh, "SEC_FULL_STRUCTURED.xlsx")
print(workbook)

# Optional PostgreSQL persistence (requires psycopg2-binary + running DB)
db_config = {
    "dbname": "sec_recon",
    "user": "postgres",
    "host": "localhost",
    "port": "5432",
    # "password": "your-password",
}

result = engine.persist_filing_to_postgres(adsh, db_config=db_config, schema="public")
print(result)
```

## Proving Exactness (Validation Evidence Workflow)

To support the specification requirement of reconstructing statements "exactly as presented,"
the project now includes a proof workflow:

1. Run core/unit tests
2. Run multi-filing validation scorecards
3. Create approved "golden" CSVs for specific filings/statements
4. Run golden regression tests to detect future mismatches

### Commands

```bash
# Core tests
pytest tests/ -v

# Multi-filing proof scorecard
python tools/prove_exactness.py --limit 10 --unique-cik --save-per-filing

# Export candidate golden files (example)
python tools/export_golden_csv.py --adsh 0001628280-24-043777 --stmt BS

# Golden regression (after approving CSVs and updating golden/manifest.json)
pytest tests/test_golden_regression.py -v
```

Generated proof artifacts:
- `proof_reports/summary_scoreboard.json`
- `proof_reports/batch_report.json`
- `proof_reports/filings/*.json` (if `--save-per-filing` is used)

### Current Verification Snapshot (Local)

- Core test suite: `22 passed`
- Golden regression: passing for `13` approved statement tables across `3` filings
- Multi-filing proof scorecard example run (`10` filings): `pass=3`, `warn=6`, `fail=1`

This supports a strong claim of multi-filing correctness with regression protection, while still
being honest that universal coverage across all SEC filings requires continued expansion of the
golden set and proof runs.

## Data Models

### Company
Represents company information from SEC filings.

```python
Company(
    cik="789460",
    name="WORLD KINECT CORP",
    sic="5172",
    country="US",
    state="FL",
    ein="592459427",
    fiscal_year_end="1231"
)
```

### Financial Statements
Structured representations of financial statements.

```python
# Balance Sheet
balance_sheet = BalanceSheet(
    company=company,
    as_of_date=date(2024, 9, 30),
    assets={"Current Assets": 1000000, ...},
    liabilities={"Current Liabilities": 500000, ...},
    equity={"Common Stock": 500000, ...}
)

# Income Statement
income_statement = IncomeStatement(
    company=company,
    period_start=date(2024, 1, 1),
    period_end=date(2024, 9, 30),
    revenues={"Total Revenues": 5000000, ...},
    expenses={"Operating Expenses": 3000000, ...},
    income={"Net Income": 2000000, ...}
)

# Cash Flow Statement
cash_flow = CashFlowStatement(
    company=company,
    period_start=date(2024, 1, 1),
    period_end=date(2024, 9, 30),
    operating_activities={"Cash from Operations": 1000000, ...},
    investing_activities={"Capital Expenditures": -500000, ...},
    financing_activities={"Debt Repayment": -200000, ...}
)
```

## Testing

Run tests with pytest:

```bash
pytest tests/
pytest tests/ -v  # Verbose
pytest tests/ --cov=src  # With coverage
```

## SEC XBRL Data Format

### File Descriptions

- **sub.txt**: Submission index - metadata about all companies and filings
- **num.txt**: Numeric instance - all numeric facts and values
- **pre.txt**: Presentation linkbase - shows how concepts are presented in statements
- **tag.txt**: Tag definitions - metadata about all XBRL concepts

### Key Concepts

- **ADSH**: Accession number - unique identifier for each filing
- **CIK**: Central Index Key - unique identifier for each company
- **Tag/Concept**: XBRL concept name (e.g., Assets, NetIncomeLoss)
- **Context**: Defines the period and entity for a fact (instant vs duration)
- **Unit**: Measurement unit for a fact (USD, shares, pure number)
- **Negating**: Whether a concept value should be negated (e.g., expenses)

## Performance Considerations

- For large datasets (>1GB), consider filtering data before loading
- The numeric parser may take time on first parse - consider caching
- Use `.copy()` on returned DataFrames to avoid unintended mutations

## Extending the Engine

### Add Custom Analysis

```python
from src.core.engine import FinancialStatementEngine

class FinancialAnalyzer:
    def __init__(self, engine: FinancialStatementEngine):
        self.engine = engine
    
    def calculate_ratios(self, statement):
        # Your custom ratio calculations
        pass
```

### Custom Parsers

Extend the base parser classes in `src/parsers/` for additional file formats or custom processing.

## Troubleshooting

### File Not Found Errors
Ensure all required .txt files are in the data directory.

### Memory Issues
For large datasets, process filings one at a time rather than loading all at once.

### Data Inconsistencies
Run `validate_filing_integrity()` to identify data quality issues.

## Contributing

To contribute improvements:

1. Create a feature branch
2. Add tests for new functionality
3. Ensure all tests pass
4. Submit pull request

## License

[Specify your license here]

## Contact

[Your contact information]

## References

- SEC XBRL Documentation: https://www.sec.gov/cgi-bin/viewer
- XBRL International: https://www.xbrl.org/
- SEC Form Definitions: https://www.sec.gov/cgi-bin/browse-edgar
# SEC_Financial_Statement_Reconstruction_Engine
