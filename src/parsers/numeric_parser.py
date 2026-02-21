"""Parser for numeric instance files (num.txt)."""

from pathlib import Path
from typing import Dict, List

import pandas as pd


class NumericParser:
    """
    Parses numeric instance files (num.txt) from SEC XBRL filing packages.
    
    Contains all numeric facts with their contexts, units, and values.
    """
    
    REQUIRED_FIELDS = [
        "adsh",
        "tag",
        "version",
        "ddate",
        "qtrs",
        "uom",
        "segments",
        "coreg",
        "value",
        "footnote",
    ]
    
    def __init__(self, file_path: Path):
        """
        Initialize parser with numeric file path.
        
        Args:
            file_path: Path to num.txt file
        """
        self.file_path = Path(file_path)
        self.data = None
        self._parse()
    
    def _parse(self):
        """Load and parse the numeric file."""
        self.data = pd.read_csv(
            self.file_path,
            sep="\t",
            dtype={"adsh": str, "tag": str, "ddate": str, "value": str},
            low_memory=False,
            na_values=[""],
        )

        # Convert value to numeric where possible
        self.data["value"] = pd.to_numeric(self.data["value"], errors="coerce")
        self.data["qtrs"] = pd.to_numeric(self.data["qtrs"], errors="coerce").astype("Int64")
    
    def get_all_facts(self) -> pd.DataFrame:
        """
        Get all numeric facts.
        
        Returns:
            DataFrame with all facts
        """
        return self.data.copy()
    
    def get_facts_by_adsh(self, adsh: str) -> pd.DataFrame:
        """
        Get all facts for a specific filing.
        
        Args:
            adsh: Accession number
            
        Returns:
            DataFrame with facts for that filing
        """
        return self.data[self.data['adsh'] == adsh].copy()
    
    def get_facts_by_tag(self, tag: str) -> pd.DataFrame:
        """
        Get all facts for a specific XBRL tag.
        
        Args:
            tag: XBRL tag name
            
        Returns:
            DataFrame with facts matching the tag
        """
        return self.data[self.data['tag'] == tag].copy()
    
    def get_concept_values(self, adsh: str, tag: str) -> List[Dict]:
        """
        Get all values for a specific concept in a filing.
        
        Args:
            adsh: Accession number
            tag: XBRL tag/concept name
            
        Returns:
            List of dictionaries with value information
        """
        mask = (self.data['adsh'] == adsh) & (self.data['tag'] == tag)
        facts = self.data[mask]
        return facts.to_dict("records")
    
    def get_latest_balance_sheet_items(self, adsh: str) -> pd.DataFrame:
        """
        Extract balance sheet items (instant facts) from a filing.
        
        Args:
            adsh: Accession number
            
        Returns:
            DataFrame with balance sheet items
        """
        filing_data = self.get_facts_by_adsh(adsh)
        # qtrs = 0 typically indicates balance sheet (instant) facts
        return filing_data[filing_data["qtrs"] == 0].copy()
    
    def get_period_facts(self, adsh: str, qtrs: int) -> pd.DataFrame:
        """
        Get facts for a specific reporting period.
        
        Args:
            adsh: Accession number
            qtrs: Quarter count (0 for instant, 1-4 for quarters, 40+ for yearly)
            
        Returns:
            DataFrame with facts for that period
        """
        filing_data = self.get_facts_by_adsh(adsh)
        return filing_data[filing_data["qtrs"] == qtrs].copy()
    
    def aggregate_by_tag(self) -> pd.DataFrame:
        """
        Aggregate numeric values by tag across all filings.
        
        Returns:
            DataFrame with count and statistics by tag
        """
        return self.data.groupby("tag")["value"].agg([
            "count", "sum", "mean", "min", "max", "std"
        ]).reset_index()
    
    def get_units_used(self) -> Dict[str, int]:
        """
        Get all unique units and their frequencies.
        
        Returns:
            Dictionary with units as keys and counts as values
        """
        return self.data["uom"].value_counts().to_dict()
    
    def validate_integrity(self) -> Dict[str, List[str]]:
        """
        Validate data integrity and report issues.
        
        Returns:
            Dictionary with validation results
        """
        issues = {
            "missing_values": [],
            "invalid_values": [],
            "warnings": [],
        }

        # Check for required fields
        for field in self.REQUIRED_FIELDS:
            if field not in self.data.columns:
                issues["missing_values"].append(f"Missing required field: {field}")

        # Check for invalid numeric values
        if "value" in self.data.columns and self.data["value"].isna().sum() > 0:
            issues["warnings"].append(
                f"Found {self.data['value'].isna().sum()} null values in numeric data"
            )

        return issues
