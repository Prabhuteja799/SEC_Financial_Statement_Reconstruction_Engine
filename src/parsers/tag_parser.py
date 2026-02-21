"""Parser for tag definition files (tag.txt)."""

import pandas as pd
from typing import Dict, List, Optional
from pathlib import Path


class TagParser:
    """
    Parses tag definition files (tag.txt) from SEC XBRL filing packages.
    
    Contains definitions and metadata for all XBRL concepts/tags.
    """
    
    REQUIRED_FIELDS = [
        'tag', 'version', 'custom', 'abstract', 'datatype', 'iord', 'crdr',
        'tlabel', 'doc'
    ]
    
    def __init__(self, file_path: Path):
        """
        Initialize parser with tag definition file path.
        
        Args:
            file_path: Path to tag.txt file
        """
        self.file_path = Path(file_path)
        self.data = None
        self._parse()
    
    def _parse(self):
        """Load and parse the tag file."""
        self.data = pd.read_csv(
            self.file_path,
            sep='\t',
            dtype=str,
            low_memory=False
        )
    
    def get_all_tags(self) -> pd.DataFrame:
        """
        Get all tag definitions.
        
        Returns:
            DataFrame with all tags
        """
        return self.data.copy()
    
    def get_tag_definition(self, tag: str) -> Optional[Dict]:
        """
        Get definition for a specific tag.
        
        Args:
            tag: Tag/concept name
            
        Returns:
            Dictionary with tag definition or None
        """
        rows = self.data[self.data['tag'] == tag]
        if not rows.empty:
            return rows.iloc[0].to_dict()
        return None
    
    def get_tag_label(self, tag: str) -> Optional[str]:
        """
        Get human-readable label for a tag.
        
        Args:
            tag: Tag/concept name
            
        Returns:
            Label string or None
        """
        rows = self.data[self.data['tag'] == tag]
        if not rows.empty:
            return rows.iloc[0]['tlabel']
        return None
    
    def get_tag_datatype(self, tag: str) -> Optional[str]:
        """
        Get datatype for a tag.
        
        Args:
            tag: Tag/concept name
            
        Returns:
            Datatype string (e.g., 'xsd:decimal', 'xsd:string') or None
        """
        rows = self.data[self.data['tag'] == tag]
        if not rows.empty:
            return rows.iloc[0]['datatype']
        return None
    
    def get_custom_tags(self) -> pd.DataFrame:
        """
        Get all custom (company-specific) tags.
        
        Returns:
            DataFrame with custom tags
        """
        return self.data[self.data['custom'] == '1'].copy()
    
    def get_standard_tags(self) -> pd.DataFrame:
        """
        Get all standard XBRL tags.
        
        Returns:
            DataFrame with standard tags
        """
        return self.data[self.data['custom'] == '0'].copy()
    
    def get_abstract_tags(self) -> pd.DataFrame:
        """
        Get all abstract tags (used for hierarchy structure).
        
        Returns:
            DataFrame with abstract tags
        """
        return self.data[self.data['abstract'] == '1'].copy()
    
    def get_numeric_tags(self) -> pd.DataFrame:
        """
        Get tags that represent numeric concepts.
        
        Returns:
            DataFrame with numeric tags
        """
        numeric_types = ['xsd:decimal', 'xsd:integer', 'xsd:float', 'xsd:double']
        mask = self.data['datatype'].isin(numeric_types)
        return self.data[mask].copy()
    
    def get_string_tags(self) -> pd.DataFrame:
        """
        Get tags that represent string/text concepts.
        
        Returns:
            DataFrame with string tags
        """
        return self.data[self.data['datatype'] == 'xsd:string'].copy()
    
    def get_tags_by_datatype(self, datatype: str) -> pd.DataFrame:
        """
        Get tags for a specific datatype.
        
        Args:
            datatype: Datatype string
            
        Returns:
            DataFrame with tags of that datatype
        """
        return self.data[self.data['datatype'] == datatype].copy()
    
    def is_debit_account(self, tag: str) -> Optional[bool]:
        """
        Check if a tag represents a debit account.
        
        Args:
            tag: Tag/concept name
            
        Returns:
            True for debit, False for credit, None if not found
        """
        definition = self.get_tag_definition(tag)
        if definition:
            return definition.get('crdr') == 'D'
        return None
    
    def get_documentation(self, tag: str) -> Optional[str]:
        """
        Get documentation/description for a tag.
        
        Args:
            tag: Tag/concept name
            
        Returns:
            Documentation string or None
        """
        rows = self.data[self.data['tag'] == tag]
        if not rows.empty:
            return rows.iloc[0]['doc']
        return None
