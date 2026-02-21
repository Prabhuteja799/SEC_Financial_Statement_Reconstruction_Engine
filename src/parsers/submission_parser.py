"""Parser for submission index files (sub.txt)."""

import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime


class SubmissionParser:
    """
    Parses submission index files (sub.txt) from SEC XBRL filing packages.
    
    Contains metadata about all companies and their filings in the submission set.
    """
    
    # Standard field names from SEC XBRL documentation
    REQUIRED_FIELDS = [
        'adsh', 'cik', 'name', 'sic', 'countryba', 'stprba', 'cityba', 'zipba',
        'bas1', 'bas2', 'baph', 'countryma', 'stprma', 'cityma', 'zipma',
        'mas1', 'mas2', 'countryinc', 'stprinc', 'ein', 'former', 'changed',
        'afs', 'wksi', 'fye', 'form', 'period', 'fy', 'fp', 'filed', 'accepted',
        'prevrpt', 'detail', 'instance', 'nciks', 'aciks'
    ]
    
    def __init__(self, file_path: Path):
        """
        Initialize parser with submission file path.
        
        Args:
            file_path: Path to sub.txt file
        """
        self.file_path = Path(file_path)
        self.data = None
        self._parse()
    
    def _parse(self):
        """Load and parse the submission file."""
        self.data = pd.read_csv(
            self.file_path,
            sep='\t',
            dtype=str,
            low_memory=False
        )
    
    def get_all_submissions(self) -> pd.DataFrame:
        """
        Get all submission records.
        
        Returns:
            DataFrame with all submissions
        """
        return self.data.copy()
    
    def get_company_filings(self, cik: str) -> pd.DataFrame:
        """
        Get all filings for a specific company.
        
        Args:
            cik: Central Index Key
            
        Returns:
            DataFrame with company's filings
        """
        return self.data[self.data['cik'] == cik].copy()
    
    def get_filing_by_adsh(self, adsh: str) -> Optional[Dict]:
        """
        Get a specific filing by ADSH (accession number).
        
        Args:
            adsh: Accession number
            
        Returns:
            Dictionary with filing details or None
        """
        result = self.data[self.data['adsh'] == adsh]
        if not result.empty:
            return result.iloc[0].to_dict()
        return None
    
    def get_instance_files(self) -> Dict[str, str]:
        """
        Get mapping of ADSH to instance file names.
        
        Returns:
            Dictionary mapping ADSH to instance filename
        """
        return dict(zip(self.data['adsh'], self.data['instance']))
    
    def get_unique_companies(self) -> pd.DataFrame:
        """
        Get unique companies from submission data.
        
        Returns:
            DataFrame with unique companies
        """
        return self.data[['cik', 'name', 'sic', 'countryinc']].drop_duplicates()
    
    def filter_by_form_type(self, form_type: str) -> pd.DataFrame:
        """
        Filter submissions by form type.
        
        Args:
            form_type: Form type (e.g., '10-K', '10-Q')
            
        Returns:
            Filtered DataFrame
        """
        return self.data[self.data['form'].str.contains(form_type, na=False)].copy()
    
    def filter_by_date_range(self, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Filter submissions by filing date range.
        
        Args:
            start_date: Start date (YYYYMMDD format)
            end_date: End date (YYYYMMDD format)
            
        Returns:
            Filtered DataFrame
        """
        mask = (self.data['filed'] >= start_date) & (self.data['filed'] <= end_date)
        return self.data[mask].copy()
