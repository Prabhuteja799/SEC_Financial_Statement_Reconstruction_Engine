"""Example usage of the SEC Financial Statement Reconstruction Engine."""

from pathlib import Path
from src.core.engine import FinancialStatementEngine
from src.core.reconstructor import StatementReconstructor


def main():
    # Initialize the engine with the 2024 Q4 data
    data_dir = Path(__file__).parent / '2024q4'
    engine = FinancialStatementEngine(data_dir)
    
    print("=" * 60)
    print("SEC Financial Statement Reconstruction Engine - Examples")
    print("=" * 60)
    
    # Example 1: Get all companies
    print("\n[Example 1] Get all unique companies in the dataset")
    print("-" * 60)
    companies = engine.get_all_companies()
    print(f"Found {len(companies)} unique companies")
    print("\nFirst 5 companies:")
    print(companies.head())
    
    # Example 2: Get company info
    print("\n[Example 2] Get info for World Kinect Corp (CIK: 789460)")
    print("-" * 60)
    company = engine.get_company_info('789460')
    if company:
        print(f"Company: {company.name}")
        print(f"CIK: {company.cik}")
        print(f"SIC: {company.sic}")
        print(f"Country: {company.country}, State: {company.state}")
        print(f"Fiscal Year End: {company.fiscal_year_end}")
    
    # Example 3: Get company filings
    print("\n[Example 3] Get all filings for World Kinect Corp")
    print("-" * 60)
    filings = engine.get_filings_for_company('789460')
    print(f"Found {len(filings)} filings")
    if not filings.empty:
        print("\nFiling details:")
        print(filings[['adsh', 'form', 'filed', 'instance']].head())
    
    # Example 4: Filter by form type
    print("\n[Example 4] Filter all 10-Q filings (quarterly reports)")
    print("-" * 60)
    ten_qs = engine.filter_filings_by_form('10-Q')
    print(f"Found {len(ten_qs)} 10-Q filings")
    print("\nCompanies with 10-Q filings:")
    print(ten_qs[['name', 'form', 'filed']].drop_duplicates().head())
    
    # Example 5: Get specific filing metadata
    print("\n[Example 5] Get metadata for specific filing")
    print("-" * 60)
    adsh = '0001628280-24-043777'  # World Kinect Q3 2024
    filing_info = engine.get_filing_metadata(adsh)
    if filing_info:
        print(f"Filing Accession: {filing_info['adsh']}")
        print(f"Company: {filing_info['name']} ({filing_info['cik']})")
        print(f"Form Type: {filing_info['form']}")
        print(f"Period: {filing_info['period']}")
        print(f"Filed: {filing_info['filed']}")
        print(f"Instance File: {filing_info['instance']}")
    
    # Example 6: Get numeric facts
    print("\n[Example 6] Get numeric facts for the filing")
    print("-" * 60)
    facts = engine.get_numeric_facts(adsh)
    if not facts.empty:
        print(f"Total numeric facts: {len(facts)}")
        print("\nFact distribution by unit:")
        print(facts['uom'].value_counts().head())
        print("\nSample facts:")
        print(facts[['tag', 'uom', 'value', 'qtrs']].head(10))
    
    # Example 7: Reconstruct financial statements
    print("\n[Example 7] Reconstruct financial statements")
    print("-" * 60)
    if engine.numeric_parser and engine.presentation_parser and engine.tag_parser:
        reconstructor = StatementReconstructor(
            engine.numeric_parser,
            engine.presentation_parser,
            engine.tag_parser
        )
        
        # Reconstruct balance sheet
        bs = reconstructor.reconstruct_balance_sheet(adsh, company)
        if bs:
            print("Balance Sheet reconstructed successfully")
            print(f"Number of assets: {len(bs.assets)}")
            print(f"Number of liabilities: {len(bs.liabilities)}")
            print(f"Number of equity items: {len(bs.equity)}")
            if bs.assets:
                print("\nTop 5 assets:")
                for i, (label, value) in enumerate(sorted(
                    bs.assets.items(),
                    key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
                    reverse=True
                )[:5]):
                    print(f"  {i+1}. {label}: ${value:,.0f}")
        
        # Reconstruct income statement
        is_stmt = reconstructor.reconstruct_income_statement(adsh, company)
        if is_stmt:
            print("\n\nIncome Statement reconstructed successfully")
            print(f"Number of revenue items: {len(is_stmt.revenues)}")
            print(f"Number of expense items: {len(is_stmt.expenses)}")
            print(f"Number of income items: {len(is_stmt.income)}")
            if is_stmt.revenues:
                print("\nRevenues:")
                for label, value in is_stmt.revenues.items():
                    print(f"  {label}: ${value:,.0f}")
    
    # Example 8: Data validation
    print("\n[Example 8] Validate filing integrity")
    print("-" * 60)
    validation = engine.validate_filing_integrity(adsh)
    if validation:
        for check_name, issues in validation.items():
            print(f"\n{check_name.upper()}:")
            for issue in issues:
                print(f"  - {issue}")


if __name__ == "__main__":
    main()
