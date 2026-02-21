"""Test suite for SEC Financial Statement Reconstruction Engine."""

import pytest
from pathlib import Path
import pandas as pd

from src.parsers import (
    SubmissionParser,
    NumericParser,
    PresentationParser,
    TagParser,
)
from src.core.engine import FinancialStatementEngine

DATA_DIR = Path(__file__).resolve().parents[1] / "2024q4"


class TestSubmissionParser:
    """Tests for submission parser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return SubmissionParser(DATA_DIR / "sub.txt")
    
    def test_parser_initialization(self, parser):
        """Test that parser initializes correctly."""
        assert parser.data is not None
        assert len(parser.data) > 0
    
    def test_get_all_submissions(self, parser):
        """Test getting all submissions."""
        subs = parser.get_all_submissions()
        assert isinstance(subs, pd.DataFrame)
        assert len(subs) > 0
    
    def test_get_company_filings(self, parser):
        """Test getting filings for a company."""
        filings = parser.get_company_filings('789460')
        assert isinstance(filings, pd.DataFrame)
        assert len(filings) > 0
        assert all(filings['cik'] == '789460')
    
    def test_get_filing_by_adsh(self, parser):
        """Test getting specific filing."""
        adsh = '0001628280-24-043777'
        filing = parser.get_filing_by_adsh(adsh)
        assert filing is not None
        assert filing['adsh'] == adsh


class TestNumericParser:
    """Tests for numeric parser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        return NumericParser(DATA_DIR / "num.txt")
    
    def test_parser_initialization(self, parser):
        """Test that parser initializes correctly."""
        assert parser.data is not None
        assert len(parser.data) > 0
    
    def test_get_all_facts(self, parser):
        """Test getting all facts."""
        facts = parser.get_all_facts()
        assert isinstance(facts, pd.DataFrame)
        assert len(facts) > 0
        assert 'tag' in facts.columns
        assert 'value' in facts.columns


class TestPresentationParser:
    """Tests for presentation parser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        if not (DATA_DIR / "pre.txt").exists():
            pytest.skip("Presentation file not available")
        return PresentationParser(DATA_DIR / "pre.txt")
    
    def test_parser_initialization(self, parser):
        """Test that parser initializes correctly."""
        assert parser.data is not None
        assert len(parser.data) > 0


class TestTagParser:
    """Tests for tag parser."""
    
    @pytest.fixture
    def parser(self):
        """Create parser instance."""
        if not (DATA_DIR / "tag.txt").exists():
            pytest.skip("Tag file not available")
        return TagParser(DATA_DIR / "tag.txt")
    
    def test_parser_initialization(self, parser):
        """Test that parser initializes correctly."""
        assert parser.data is not None
        assert len(parser.data) > 0


class TestFinancialStatementEngine:
    """Tests for main engine."""
    
    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return FinancialStatementEngine(DATA_DIR)
    
    def test_engine_initialization(self, engine):
        """Test that engine initializes correctly."""
        assert engine.submission_parser is not None
        assert engine.numeric_parser is not None
    
    def test_get_company_info(self, engine):
        """Test getting company information."""
        company = engine.get_company_info('789460')
        assert company is not None
        assert company.cik == '789460'
        assert 'WORLD KINECT' in company.name.upper()
    
    def test_get_all_companies(self, engine):
        """Test getting all companies."""
        companies = engine.get_all_companies()
        assert isinstance(companies, pd.DataFrame)
        assert len(companies) > 0
    
    def test_filter_filings_by_form(self, engine):
        """Test filtering filings by form type."""
        ten_qs = engine.filter_filings_by_form('10-Q')
        assert isinstance(ten_qs, pd.DataFrame)
        if len(ten_qs) > 0:
            assert all('10-Q' in form for form in ten_qs['form'])

    def test_reconstruct_statement_table(self, engine):
        """Test statement table reconstruction preserves structure."""
        adsh = '0001628280-24-043777'
        table = engine.reconstruct_statement_table(adsh, 'BS')
        assert isinstance(table, pd.DataFrame)
        assert len(table) > 0
        assert {'line', 'inpth', 'tag', 'label', 'value', 'has_value'}.issubset(table.columns)

        structure = engine.presentation_parser.get_statement_structure(adsh, 'BS')
        assert len(table) == len(structure)
        assert table[['report', 'line']].reset_index(drop=True).equals(
            structure[['report', 'line']].reset_index(drop=True)
        )

    def test_reconstruct_filing_tables(self, engine):
        """Test reconstructing multiple statements for one filing."""
        adsh = '0001628280-24-043777'
        tables = engine.reconstruct_filing_tables(adsh)
        assert isinstance(tables, dict)
        for code in ['BS', 'IS', 'CF', 'EQ', 'CI']:
            assert code in tables
            assert isinstance(tables[code], pd.DataFrame)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
