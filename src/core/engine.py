"""Main engine for financial statement reconstruction."""

from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

from src.parsers import (
    SubmissionParser,
    NumericParser,
    PresentationParser,
    TagParser,
)
from src.models import Company, FinancialStatement
from src.core.reconstructor import StatementReconstructor


class FinancialStatementEngine:
    """
    Main engine for processing SEC XBRL filing packages and reconstructing
    financial statements.
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize the engine with a directory containing XBRL data files.
        
        Args:
            data_dir: Path to directory containing sub.txt, num.txt, pre.txt, tag.txt
        """
        self.data_dir = Path(data_dir)
        self.submission_parser = None
        self.numeric_parser = None
        self.presentation_parser = None
        self.tag_parser = None
        self._load_parsers()
    
    def _load_parsers(self):
        """Load and initialize all parsers."""
        sub_file = self.data_dir / 'sub.txt'
        num_file = self.data_dir / 'num.txt'
        pre_file = self.data_dir / 'pre.txt'
        tag_file = self.data_dir / 'tag.txt'
        
        if sub_file.exists():
            self.submission_parser = SubmissionParser(sub_file)
        
        if num_file.exists():
            self.numeric_parser = NumericParser(num_file)
        
        if pre_file.exists():
            self.presentation_parser = PresentationParser(pre_file)
        
        if tag_file.exists():
            self.tag_parser = TagParser(tag_file)
    
    def get_company_info(self, cik: str) -> Optional[Company]:
        """
        Get company information from submission data.
        
        Args:
            cik: Central Index Key
            
        Returns:
            Company object or None
        """
        if not self.submission_parser:
            return None
        
        filings = self.submission_parser.get_company_filings(cik)
        if filings.empty:
            return None
        
        first_filing = filings.iloc[0]
        
        return Company(
            cik=first_filing['cik'],
            name=first_filing['name'],
            sic=first_filing['sic'],
            country=first_filing['countryinc'],
            state=first_filing['stprinc'],
            ein=first_filing['ein'],
            fiscal_year_end=first_filing['fye']
        )
    
    def get_filings_for_company(self, cik: str) -> pd.DataFrame:
        """
        Get all filings for a company.
        
        Args:
            cik: Central Index Key
            
        Returns:
            DataFrame with company's filings
        """
        if not self.submission_parser:
            return pd.DataFrame()
        
        return self.submission_parser.get_company_filings(cik)
    
    def get_filing_metadata(self, adsh: str) -> Optional[Dict]:
        """
        Get metadata for a specific filing.
        
        Args:
            adsh: Accession number
            
        Returns:
            Dictionary with filing metadata or None
        """
        if not self.submission_parser:
            return None
        
        return self.submission_parser.get_filing_by_adsh(adsh)
    
    def get_numeric_facts(self, adsh: str) -> pd.DataFrame:
        """
        Get all numeric facts for a filing.
        
        Args:
            adsh: Accession number
            
        Returns:
            DataFrame with numeric facts
        """
        if not self.numeric_parser:
            return pd.DataFrame()
        
        return self.numeric_parser.get_facts_by_adsh(adsh)
    
    def get_statement_facts(self, adsh: str, stmt_code: str) -> pd.DataFrame:
        """
        Get facts for a specific financial statement type.
        
        Args:
            adsh: Accession number
            stmt_code: Statement type code ('BS', 'IS', 'CF')
            
        Returns:
            DataFrame with facts for that statement
        """
        if not self.presentation_parser:
            return pd.DataFrame()
        
        return self.presentation_parser.get_statement_structure(adsh, stmt_code)
    
    def get_concept_label(self, tag: str) -> Optional[str]:
        """
        Get human-readable label for a concept.
        
        Args:
            tag: Concept tag
            
        Returns:
            Label string or None
        """
        if self.tag_parser:
            return self.tag_parser.get_tag_label(tag)
        return None
    
    def validate_filing_integrity(self, adsh: str) -> Dict[str, List[str]]:
        """
        Validate integrity of a specific filing.
        
        Args:
            adsh: Accession number
            
        Returns:
            Dictionary with validation results
        """
        issues = {}
        
        if self.numeric_parser:
            issues['numeric'] = self.numeric_parser.validate_integrity()
        
        return issues
    
    def get_all_companies(self) -> pd.DataFrame:
        """
        Get all unique companies from submission data.
        
        Returns:
            DataFrame with unique companies
        """
        if not self.submission_parser:
            return pd.DataFrame()
        
        return self.submission_parser.get_unique_companies()
    
    def filter_filings_by_form(self, form_type: str) -> pd.DataFrame:
        """
        Filter filings by form type.
        
        Args:
            form_type: Form type (e.g., '10-K', '10-Q')
            
        Returns:
            DataFrame with matching filings
        """
        if not self.submission_parser:
            return pd.DataFrame()
        
        return self.submission_parser.filter_by_form_type(form_type)
    
    def filter_filings_by_date(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Filter filings by date range.
        
        Args:
            start_date: Start date (YYYYMMDD format)
            end_date: End date (YYYYMMDD format)
            
        Returns:
            DataFrame with filings in date range
        """
        if not self.submission_parser:
            return pd.DataFrame()
        
        return self.submission_parser.filter_by_date_range(start_date, end_date)

    def reconstruct_statement_table(
        self,
        adsh: str,
        stmt_code: str,
        ddate: Optional[str] = None,
        qtrs: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Reconstruct a single statement table from one filing.

        Args:
            adsh: Accession number
            stmt_code: Statement code ('BS', 'IS', 'CF', 'EQ', 'CI')
            ddate: Optional context end date (YYYYMMDD)
            qtrs: Optional context quarter count

        Returns:
            DataFrame preserving pre.txt order and indentation with mapped values
        """
        if not self.numeric_parser or not self.presentation_parser or not self.tag_parser:
            return pd.DataFrame()

        reconstructor = StatementReconstructor(
            self.numeric_parser,
            self.presentation_parser,
            self.tag_parser,
        )
        return reconstructor.reconstruct_statement_table(adsh, stmt_code, ddate=ddate, qtrs=qtrs)

    def reconstruct_filing_tables(
        self, adsh: str, statement_codes: Optional[List[str]] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Reconstruct multiple statement tables for a filing.

        Args:
            adsh: Accession number
            statement_codes: Optional list of statement codes

        Returns:
            Dictionary mapping statement code to reconstructed DataFrame
        """
        if not self.numeric_parser or not self.presentation_parser or not self.tag_parser:
            return {}

        reconstructor = StatementReconstructor(
            self.numeric_parser,
            self.presentation_parser,
            self.tag_parser,
        )
        return reconstructor.reconstruct_filing_tables(adsh, statement_codes=statement_codes)

    def get_statement_coverage(self, adsh: str, stmt_code: str) -> Dict[str, object]:
        """
        Get statement mapping coverage metrics for one filing/statement.
        """
        if not self.numeric_parser or not self.presentation_parser or not self.tag_parser:
            return {
                "stmt": stmt_code,
                "rows_total": 0,
                "rows_with_values": 0,
                "rows_missing_values": 0,
                "coverage_ratio": 0.0,
                "missing_tags": [],
            }

        reconstructor = StatementReconstructor(
            self.numeric_parser,
            self.presentation_parser,
            self.tag_parser,
        )
        return reconstructor.get_statement_coverage(adsh, stmt_code)
