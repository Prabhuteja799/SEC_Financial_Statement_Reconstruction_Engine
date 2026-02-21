"""Parser for presentation linkbase files (pre.txt)."""

from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd


class PresentationParser:
    """
    Parses presentation linkbase files (pre.txt) from SEC XBRL filing packages.
    
    Contains the presentation hierarchy showing how concepts are organized
    in financial statements (balance sheet, income statement, etc).
    """
    
    REQUIRED_FIELDS = [
        "adsh",
        "report",
        "line",
        "stmt",
        "inpth",
        "rfile",
        "tag",
        "version",
        "plabel",
        "negating",
    ]
    
    def __init__(self, file_path: Path):
        """
        Initialize parser with presentation file path.
        
        Args:
            file_path: Path to pre.txt file
        """
        self.file_path = Path(file_path)
        self.data = None
        self._parse()
    
    def _parse(self):
        """Load and parse the presentation file."""
        self.data = pd.read_csv(
            self.file_path,
            sep="\t",
            dtype=str,
            low_memory=False,
        )
        self.data["line"] = pd.to_numeric(self.data["line"], errors="coerce")
        self.data["report"] = pd.to_numeric(self.data["report"], errors="coerce")
        self.data["inpth"] = pd.to_numeric(self.data["inpth"], errors="coerce")
    
    def get_all_relationships(self) -> pd.DataFrame:
        """
        Get all presentation relationships.
        
        Returns:
            DataFrame with all relationships
        """
        return self.data.copy()
    
    def get_relationships_by_adsh(self, adsh: str) -> pd.DataFrame:
        """
        Get presentation relationships for a specific filing.
        
        Args:
            adsh: Accession number
            
        Returns:
            DataFrame with relationships for that filing
        """
        return self.data[self.data['adsh'] == adsh].copy()
    
    def get_children_of_concept(self, adsh: str, parent_tag: str) -> pd.DataFrame:
        """
        Get all immediate children of a parent concept.
        
        Args:
            adsh: Accession number
            parent_tag: Parent concept tag
            
        Returns:
            DataFrame with child concepts
        """
        filing_data = self.get_relationships_by_adsh(adsh)
        concept_rows = filing_data[filing_data["tag"] == parent_tag]
        if concept_rows.empty:
            return pd.DataFrame(columns=self.data.columns)

        parent_row = concept_rows.sort_values(["report", "line"]).iloc[0]
        report = parent_row["report"]
        parent_line = parent_row["line"]
        parent_depth = parent_row["inpth"]
        if pd.isna(parent_depth):
            parent_depth = 0

        report_rows = filing_data[filing_data["report"] == report].sort_values("line")
        following_rows = report_rows[report_rows["line"] > parent_line]

        child_rows = []
        for _, row in following_rows.iterrows():
            depth = row["inpth"]
            if pd.isna(depth):
                continue
            if depth <= parent_depth:
                break
            if depth == parent_depth + 1:
                child_rows.append(row)

        if not child_rows:
            return pd.DataFrame(columns=self.data.columns)
        return pd.DataFrame(child_rows).reset_index(drop=True)
    
    def get_concept_path(self, adsh: str, tag: str) -> List[Tuple[str, int]]:
        """
        Get the path from a concept to its root in the presentation hierarchy.
        
        Args:
            adsh: Accession number
            tag: Starting concept tag
            
        Returns:
            List of tuples (tag, depth) representing an inferred path.
        """
        filing_data = self.get_relationships_by_adsh(adsh)
        concept_rows = filing_data[filing_data["tag"] == tag]
        if concept_rows.empty:
            return []

        row = concept_rows.sort_values(["report", "line"]).iloc[0]
        report = row["report"]
        line = row["line"]
        depth = row["inpth"]

        if pd.isna(depth):
            return [(tag, 0)]

        report_rows = filing_data[filing_data["report"] == report].sort_values("line")
        prior_rows = report_rows[report_rows["line"] <= line]

        path: List[Tuple[str, int]] = []
        expected_depth = int(depth)
        for _, current_row in prior_rows.iloc[::-1].iterrows():
            current_depth = current_row["inpth"]
            if pd.isna(current_depth):
                continue
            current_depth = int(current_depth)
            if current_depth == expected_depth:
                path.append((current_row["tag"], current_depth))
                expected_depth -= 1
                if expected_depth < 0:
                    break
        path.reverse()
        return path
    
    def get_statement_structure(self, adsh: str, stmt: str) -> pd.DataFrame:
        """
        Get the presentation structure for a specific statement type.
        
        Args:
            adsh: Accession number
            stmt: Financial statement code (e.g., 'BS', 'IS', 'CF')
            
        Returns:
            DataFrame with statement structure
        """
        mask = (self.data["adsh"] == adsh) & (self.data["stmt"] == stmt)
        result = self.data[mask].copy()
        result = result.sort_values(["report", "line"])
        return result
    
    def get_statement_types_available(self, adsh: str) -> List[str]:
        """
        Get all statement types available for a filing.
        
        Args:
            adsh: Accession number
            
        Returns:
            List of statement type codes
        """
        filing_data = self.get_relationships_by_adsh(adsh)
        return filing_data["stmt"].dropna().unique().tolist()
    
    def get_label_for_tag(self, adsh: str, tag: str) -> Optional[str]:
        """
        Get the presentation label for a tag.
        
        Args:
            adsh: Accession number
            tag: Concept tag
            
        Returns:
            Label string or None
        """
        mask = (self.data["adsh"] == adsh) & (self.data["tag"] == tag)
        rows = self.data[mask]
        if not rows.empty:
            return rows.iloc[0]["plabel"]
        return None
    
    def is_negating_concept(self, adsh: str, tag: str) -> bool:
        """
        Check if a concept value should be negated (e.g., expenses in income statement).
        
        Args:
            adsh: Accession number
            tag: Concept tag
            
        Returns:
            True if concept should be negated, False otherwise
        """
        mask = (self.data["adsh"] == adsh) & (self.data["tag"] == tag)
        rows = self.data[mask]
        if not rows.empty:
            return rows.iloc[0]["negating"] == "1"
        return False
