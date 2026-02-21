"""Quick start script to test the engine."""

from pathlib import Path
from src.core.engine import FinancialStatementEngine

# Initialize engine
data_dir = Path(__file__).parent / '2024q4'
print(f"Loading data from: {data_dir}")

engine = FinancialStatementEngine(data_dir)

# Get companies
companies = engine.get_all_companies()
print(f"\nTotal companies: {len(companies)}")
print("\nFirst 5 companies:")
print(companies.head())

# Get World Kinect info
company = engine.get_company_info('789460')
if company:
    print(f"\n{'=' * 50}")
    print(f"Company: {company.name}")
    print(f"CIK: {company.cik}")
    print(f"SIC: {company.sic}")
    print(f"EIN: {company.ein}")
    print(f"{'=' * 50}")

# Show filings for World Kinect
filings = engine.get_filings_for_company('789460')
print(f"\nWorld Kinect filings in dataset: {len(filings)}")
if not filings.empty:
    print("\nFiling Summary:")
    print(filings[['form', 'period', 'filed', 'instance']].to_string())

print("\n✓ Engine initialized successfully!")
print("\nNext steps:")
print("1. Run 'python examples.py' to see detailed examples")
print("2. Run 'pytest tests/' to run unit tests")
print("3. Import the engine in your own scripts to customize analysis")
