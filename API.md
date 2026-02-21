# API Documentation

## Core Classes

### FinancialStatementEngine

Main orchestration class for SEC XBRL data processing.

#### Initialization

```python
from pathlib import Path
from src.core.engine import FinancialStatementEngine

engine = FinancialStatementEngine(Path('2024q4'))
```

**Parameters:**
- `data_dir` (Path): Directory containing XBRL data files

**Attributes:**
- `submission_parser` (SubmissionParser): Parser for submission metadata
- `numeric_parser` (NumericParser): Parser for numeric facts
- `presentation_parser` (PresentationParser): Parser for presentation structure
- `tag_parser` (TagParser): Parser for tag definitions

#### Methods

##### get_company_info(cik: str) -> Optional[Company]

Get company information from CIK.

```python
company = engine.get_company_info('789460')
```

**Parameters:**
- `cik` (str): Central Index Key

**Returns:**
- `Company` object or None

##### get_filings_for_company(cik: str) -> pd.DataFrame

Get all filings for a company.

```python
filings = engine.get_filings_for_company('789460')
```

**Parameters:**
- `cik` (str): Central Index Key

**Returns:**
- DataFrame with company's filings

##### get_filing_metadata(adsh: str) -> Optional[Dict]

Get metadata for a specific filing.

```python
metadata = engine.get_filing_metadata('0001628280-24-043777')
```

**Parameters:**
- `adsh` (str): Accession number

**Returns:**
- Dictionary with filing metadata or None

##### get_numeric_facts(adsh: str) -> pd.DataFrame

Get all numeric facts for a filing.

```python
facts = engine.get_numeric_facts('0001628280-24-043777')
```

**Parameters:**
- `adsh` (str): Accession number

**Returns:**
- DataFrame with numeric facts

##### get_statement_facts(adsh: str, fstype: str) -> pd.DataFrame

Get facts for a specific statement type.

```python
bs_facts = engine.get_statement_facts('0001628280-24-043777', 'BS')
```

**Parameters:**
- `adsh` (str): Accession number
- `fstype` (str): Statement type ('BS', 'IS', 'CF', etc.)

**Returns:**
- DataFrame with statement facts

##### get_concept_label(tag: str) -> Optional[str]

Get human-readable label for a concept.

```python
label = engine.get_concept_label('Assets')
```

**Parameters:**
- `tag` (str): Concept tag

**Returns:**
- Label string or None

##### get_all_companies() -> pd.DataFrame

Get all unique companies.

```python
companies = engine.get_all_companies()
```

**Returns:**
- DataFrame with unique companies

##### filter_filings_by_form(form_type: str) -> pd.DataFrame

Filter filings by form type.

```python
ten_ks = engine.filter_filings_by_form('10-K')
```

**Parameters:**
- `form_type` (str): Form type (e.g., '10-K', '10-Q')

**Returns:**
- Filtered DataFrame

##### filter_filings_by_date(start_date: str, end_date: str) -> pd.DataFrame

Filter filings by date range.

```python
recent = engine.filter_filings_by_date('20240101', '20241231')
```

**Parameters:**
- `start_date` (str): Start date (YYYYMMDD)
- `end_date` (str): End date (YYYYMMDD)

**Returns:**
- Filtered DataFrame

---

### StatementReconstructor

Reconstructs traditional financial statements from XBRL facts.

#### Initialization

```python
from src.core.reconstructor import StatementReconstructor

reconstructor = StatementReconstructor(
    numeric_parser=engine.numeric_parser,
    presentation_parser=engine.presentation_parser,
    tag_parser=engine.tag_parser
)
```

**Parameters:**
- `numeric_parser` (NumericParser): Numeric facts parser
- `presentation_parser` (PresentationParser): Presentation parser
- `tag_parser` (TagParser): Tag definitions parser

#### Methods

##### reconstruct_balance_sheet(adsh, company, as_of_date=None) -> Optional[BalanceSheet]

Reconstruct balance sheet.

```python
bs = reconstructor.reconstruct_balance_sheet(
    adsh='0001628280-24-043777',
    company=company,
    as_of_date='2024-09-30'
)
```

**Parameters:**
- `adsh` (str): Accession number
- `company` (Company): Company object
- `as_of_date` (str, optional): Balance sheet date

**Returns:**
- BalanceSheet object or None

**Example output:**
```python
{
    'company': Company(...),
    'as_of_date': date(2024, 9, 30),
    'assets': {'Current Assets': 1000000, ...},
    'liabilities': {'Current Liabilities': 500000, ...},
    'equity': {'Common Stock': 500000, ...}
}
```

##### reconstruct_income_statement(adsh, company, period_start=None, period_end=None) -> Optional[IncomeStatement]

Reconstruct income statement.

```python
is_stmt = reconstructor.reconstruct_income_statement(
    adsh='0001628280-24-043777',
    company=company,
    period_start='2024-07-01',
    period_end='2024-09-30'
)
```

**Parameters:**
- `adsh` (str): Accession number
- `company` (Company): Company object
- `period_start` (str, optional): Period start
- `period_end` (str, optional): Period end

**Returns:**
- IncomeStatement object or None

##### reconstruct_cash_flow_statement(adsh, company, period_start=None, period_end=None) -> Optional[CashFlowStatement]

Reconstruct cash flow statement.

```python
cf = reconstructor.reconstruct_cash_flow_statement(
    adsh='0001628280-24-043777',
    company=company
)
```

**Parameters:**
- `adsh` (str): Accession number
- `company` (Company): Company object
- `period_start` (str, optional): Period start
- `period_end` (str, optional): Period end

**Returns:**
- CashFlowStatement object or None

##### reconstruct_full_statement(adsh, company, filing_date) -> Optional[FinancialStatement]

Reconstruct complete statement package.

```python
full = reconstructor.reconstruct_full_statement(
    adsh='0001628280-24-043777',
    company=company,
    filing_date='2024-10-25'
)
```

**Parameters:**
- `adsh` (str): Accession number
- `company` (Company): Company object
- `filing_date` (str): Filing date

**Returns:**
- FinancialStatement object or None

---

## Parsers

### SubmissionParser

Parses submission index files (sub.txt).

#### Methods

```python
parser = SubmissionParser(Path('2024q4/sub.txt'))

# Get all submissions
all_subs = parser.get_all_submissions()

# Get company filings
company_filings = parser.get_company_filings('789460')

# Get specific filing
filing = parser.get_filing_by_adsh('0001628280-24-043777')

# Get instance files mapping
instances = parser.get_instance_files()

# Get unique companies
companies = parser.get_unique_companies()

# Filter by form type
ten_qs = parser.filter_by_form_type('10-Q')

# Filter by date range
recent = parser.filter_by_date_range('20240101', '20241231')
```

### NumericParser

Parses numeric instance files (num.txt).

#### Methods

```python
parser = NumericParser(Path('2024q4/num.txt'))

# Get all facts
all_facts = parser.get_all_facts()

# Get facts for filing
facts = parser.get_facts_by_adsh('0001628280-24-043777')

# Get facts by tag
assets = parser.get_facts_by_tag('Assets')

# Get concept values
values = parser.get_concept_values('0001628280-24-043777', 'Assets')

# Get balance sheet items
bs_items = parser.get_latest_balance_sheet_items('0001628280-24-043777')

# Get period facts
period_facts = parser.get_period_facts('0001628280-24-043777', qtrs=1)

# Aggregate by tag
summary = parser.aggregate_by_tag()

# Get units used
units = parser.get_units_used()

# Validate integrity
issues = parser.validate_integrity()
```

### PresentationParser

Parses presentation linkbase files (pre.txt).

#### Methods

```python
parser = PresentationParser(Path('2024q4/pre.txt'))

# Get all relationships
relationships = parser.get_all_relationships()

# Get filing relationships
filing_rels = parser.get_relationships_by_adsh('0001628280-24-043777')

# Get children of parent
children = parser.get_children_of_concept('0001628280-24-043777', 'Assets')

# Get concept path
path = parser.get_concept_path('0001628280-24-043777', 'Assets')

# Get statement structure
bs_structure = parser.get_statement_structure('0001628280-24-043777', 'BS')

# Get available statement types
statements = parser.get_statement_types_available('0001628280-24-043777')

# Get tag label
label = parser.get_label_for_tag('0001628280-24-043777', 'Assets')

# Check if negating
is_neg = parser.is_negating_concept('0001628280-24-043777', 'Expense')
```

### TagParser

Parses tag definition files (tag.txt).

#### Methods

```python
parser = TagParser(Path('2024q4/tag.txt'))

# Get all tags
all_tags = parser.get_all_tags()

# Get tag definition
definition = parser.get_tag_definition('Assets')

# Get tag label
label = parser.get_tag_label('Assets')

# Get tag datatype
datatype = parser.get_tag_datatype('Assets')

# Get custom tags
custom = parser.get_custom_tags()

# Get standard tags
standard = parser.get_standard_tags()

# Get abstract tags
abstract = parser.get_abstract_tags()

# Get numeric tags
numeric = parser.get_numeric_tags()

# Get string tags
strings = parser.get_string_tags()

# Get tags by datatype
decimal_tags = parser.get_tags_by_datatype('xsd:decimal')

# Check if debit account
is_debit = parser.is_debit_account('Assets')

# Get documentation
doc = parser.get_documentation('Assets')
```

---

## Data Models

### Company

```python
from src.models import Company

company = Company(
    cik="789460",
    name="WORLD KINECT CORP",
    ticker="WKC",
    sic="5172",
    country="US",
    state="FL",
    ein="592459427",
    fiscal_year_end="1231"
)
```

### BalanceSheet

```python
from src.models import BalanceSheet

bs = BalanceSheet(
    company=company,
    as_of_date=date(2024, 9, 30),
    assets={'Current Assets': 1000000, ...},
    liabilities={'Current Liabilities': 500000, ...},
    equity={'Common Stock': 500000, ...}
)
```

### IncomeStatement

```python
from src.models import IncomeStatement

is_stmt = IncomeStatement(
    company=company,
    period_start=date(2024, 1, 1),
    period_end=date(2024, 9, 30),
    revenues={'Total Revenues': 5000000, ...},
    expenses={'Operating Expenses': 3000000, ...},
    income={'Net Income': 2000000, ...}
)
```

### CashFlowStatement

```python
from src.models import CashFlowStatement

cf = CashFlowStatement(
    company=company,
    period_start=date(2024, 1, 1),
    period_end=date(2024, 9, 30),
    operating_activities={'Cash from Operations': 1000000, ...},
    investing_activities={'Capital Expenditures': -500000, ...},
    financing_activities={'Debt Repayment': -200000, ...}
)
```

### FinancialStatement

```python
from src.models import FinancialStatement

statement = FinancialStatement(
    company=company,
    period="2024-Q3",
    filing_date=date(2024, 10, 25),
    balance_sheet=bs,
    income_statement=is_stmt,
    cash_flow_statement=cf,
    metadata={'adsh': '0001628280-24-043777'}
)
```

---

## Common Workflows

### Get Company Financial Data

```python
from pathlib import Path
from src.core.engine import FinancialStatementEngine

# Initialize
engine = FinancialStatementEngine(Path('2024q4'))

# Get company
company = engine.get_company_info('789460')

# Get filings
filings = engine.get_filings_for_company('789460')

# Get latest filing
latest = filings[filings['filed'].str.max() == filings['filed']].iloc[0]
adsh = latest['adsh']

# Get facts
facts = engine.get_numeric_facts(adsh)
```

### Reconstruct Full Financial Statements

```python
from src.core.reconstructor import StatementReconstructor

# Create reconstructor
reconstructor = StatementReconstructor(
    engine.numeric_parser,
    engine.presentation_parser,
    engine.tag_parser
)

# Reconstruct
full_statement = reconstructor.reconstruct_full_statement(
    adsh,
    company,
    latest['filed']
)

# Access statements
bs = full_statement.balance_sheet
is_stmt = full_statement.income_statement
cf = full_statement.cash_flow_statement
```

### Query Specific Concepts

```python
# Get all facts for a concept
asset_facts = parser.numeric_parser.get_facts_by_tag('Assets')

# Get concept label
label = engine.get_concept_label('Assets')

# Get concept definition
definition = parser.tag_parser.get_tag_definition('Assets')
```

---

## Error Handling

```python
try:
    company = engine.get_company_info('999999')
    if company is None:
        print("Company not found")
except Exception as e:
    print(f"Error: {e}")
```

## Performance Tips

1. Cache parsers if processing multiple filings
2. Filter data before loading large DataFrames
3. Use specific queries rather than loading all data
4. Consider chunking numeric data for very large files
