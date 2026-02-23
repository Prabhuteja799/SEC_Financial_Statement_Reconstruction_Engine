# SEC Financial Statement Reconstruction Engine - Quick Reference

## ⚡ Quick Start (30 seconds)

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python quickstart.py
```

## ✅ Proof Workflow (Recommended)

```bash
# Core tests
pytest tests/ -v

# Multi-filing validation scorecard
python tools/prove_exactness.py --limit 10 --unique-cik --save-per-filing

# Strict golden regression (after approving golden CSVs)
pytest tests/test_golden_regression.py -v
```

## 📚 Documentation Map

| Document | Purpose |
|----------|---------|
| **README.md** | Complete project guide |
| **SETUP.md** | Installation instructions |
| **API.md** | Complete API reference |
| **golden/README.md** | Golden-file proof workflow |
| **examples.py** | Working code examples |
| **quickstart.py** | Verify installation |

## 🔧 Main Classes

### FinancialStatementEngine
```python
from src.core.engine import FinancialStatementEngine
engine = FinancialStatementEngine(Path('2024q4'))

companies = engine.get_all_companies()
company = engine.get_company_info('789460')
filings = engine.get_filings_for_company('789460')
facts = engine.get_numeric_facts(adsh)
report = engine.validate_filing_reconstruction(adsh)
tables = engine.reconstruct_filing_tables(adsh)
```

### StatementReconstructor
```python
from src.core.reconstructor import StatementReconstructor
reconstructor = StatementReconstructor(...)

bs = reconstructor.reconstruct_balance_sheet(adsh, company)
is_stmt = reconstructor.reconstruct_income_statement(adsh, company)
cf = reconstructor.reconstruct_cash_flow_statement(adsh, company)
```

## 📊 Parsers

- **SubmissionParser** - Parse sub.txt (company/filing metadata)
- **NumericParser** - Parse num.txt (financial values)
- **PresentationParser** - Parse pre.txt (statement structure)
- **TagParser** - Parse tag.txt (concept definitions)

## 🎯 Common Tasks

```python
# Get Company Data
company = engine.get_company_info('789460')
filings = engine.get_filings_for_company('789460')

# Filter Filings
ten_qs = engine.filter_filings_by_form('10-Q')
recent = engine.filter_filings_by_date('20240101', '20241231')

# Get Financial Data
facts = engine.get_numeric_facts(adsh)
label = engine.get_concept_label('Assets')

# Reconstruct Statements
full = reconstructor.reconstruct_full_statement(adsh, company, date)
print(full.balance_sheet.assets)
print(full.income_statement.revenues)
```

## 🚀 Data Models

- **Company** - Company information
- **BalanceSheet** - Assets, liabilities, equity
- **IncomeStatement** - Revenues, expenses, income
- **CashFlowStatement** - Operating, investing, financing
- **FinancialStatement** - Complete package

## ✅ What Works

- Parse SEC XBRL files
- Query companies and filings
- Filter by multiple criteria
- Extract financial facts
- Reconstruct financial statements
- Reconstruct row-accurate statement tables (BS/IS/CF/EQ/CI)
- Validate filings across multiple filings (proof scorecards)
- Golden regression against approved outputs
- Type-safe data access
- Comprehensive documentation

## 📞 Need Help?

1. **Installation?** → SETUP.md
2. **How to use?** → examples.py or README.md
3. **API details?** → API.md
4. **Quick test?** → `python quickstart.py`
5. **Proof workflow?** → `golden/README.md` + `tools/prove_exactness.py`

## 🎯 Next Steps

1. Run `python quickstart.py`
2. Run `pytest tests/ -v`
3. Run `python tools/prove_exactness.py --limit 10 --unique-cik --save-per-filing`
4. Review `README.md` and `golden/README.md`
5. Start expanding golden coverage
