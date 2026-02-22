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
        assert {
            'line',
            'inpth',
            'tag',
            'label',
            'value',
            'display_value',
            'formatted_value',
            'has_value',
        }.issubset(table.columns)

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

        # CI fallback should produce rows from numeric facts even without CI pre.txt structure
        assert len(tables['CI']) > 0

    def test_formatted_negative_values(self, engine):
        """Negative display values should use financial parentheses format."""
        adsh = '0001628280-24-043777'
        cf_table = engine.reconstruct_statement_table(adsh, 'CF')
        negative_rows = cf_table[cf_table['display_value'] < 0]
        if not negative_rows.empty:
            assert negative_rows['formatted_value'].str.startswith('(').all()

    def test_statement_coverage(self, engine):
        """Coverage metrics should be available per statement."""
        adsh = '0001628280-24-043777'
        coverage = engine.get_statement_coverage(adsh, 'EQ')
        assert coverage['stmt'] == 'EQ'
        assert coverage['rows_total'] >= coverage['rows_with_values']
        assert 0.0 <= coverage['coverage_ratio'] <= 1.0

    def test_export_filing_to_excel(self, engine, tmp_path):
        """Workbook export should create all required statement sheets."""
        pytest.importorskip("openpyxl")

        adsh = '0001628280-24-043777'
        output_path = tmp_path / "SEC_FULL_STRUCTURED.xlsx"
        created = engine.export_filing_to_excel(adsh, output_path=output_path)

        assert created.exists()
        workbook = pd.ExcelFile(created)
        assert {'BS', 'IS', 'CF', 'EQ', 'CI'}.issubset(set(workbook.sheet_names))

        bs_sheet = pd.read_excel(created, sheet_name='BS')
        assert {'line_item', 'formatted_value', 'has_value'}.issubset(bs_sheet.columns)

    def test_validate_filing_reconstruction(self, engine):
        """Validation report should include per-statement and summary diagnostics."""
        adsh = '0001628280-24-043777'
        report = engine.validate_filing_reconstruction(adsh)

        assert report['adsh'] == adsh
        assert 'summary' in report
        assert 'statements' in report
        for code in ['BS', 'IS', 'CF', 'EQ', 'CI']:
            assert code in report['statements']
            stmt = report['statements'][code]
            assert 'coverage' in stmt
            assert 'context_coherence' in stmt
            assert 'duplicate_candidates' in stmt

        summary = report['summary']
        assert summary['rows_total'] >= summary['rows_with_values']
        assert 0.0 <= summary['overall_coverage_ratio'] <= 1.0
        assert 'conflicting_candidate_rows' in summary
        assert summary['status'] in {'pass', 'warn', 'fail'}
        # EQ supports multi-context patterns by design in phase 5.1.
        assert report['statements']['EQ']['context_coherence']['passed'] is True

    def test_validate_filings_batch(self, engine):
        """Batch validation should run across multiple filings."""
        submissions = engine.submission_parser.get_all_submissions()
        adsh_list = submissions['adsh'].dropna().head(2).tolist()
        report = engine.validate_filings_batch(adsh_list)

        assert report['count'] == len(adsh_list)
        assert set(report['status_counts'].keys()) == {'pass', 'warn', 'fail'}
        for adsh in adsh_list:
            assert adsh in report['results']
            assert 'summary' in report['results'][adsh]

    def test_multi_company_reconstruction_regression(self, engine):
        """Reconstruction should work across multiple companies without code changes."""
        submissions = engine.submission_parser.get_all_submissions()
        distinct = submissions[['cik', 'adsh']].dropna().drop_duplicates('cik').head(2)
        assert len(distinct) == 2

        for _, row in distinct.iterrows():
            adsh = row['adsh']
            tables = engine.reconstruct_filing_tables(adsh)
            assert isinstance(tables, dict)
            assert len(tables['BS']) > 0
            assert len(tables['IS']) > 0
            assert len(tables['CF']) > 0

    def test_validate_filings_batch_status_aggregation(self, engine):
        """Batch validation status counts should reconcile with filing count."""
        submissions = engine.submission_parser.get_all_submissions()
        adsh_list = submissions['adsh'].dropna().head(3).tolist()
        report = engine.validate_filings_batch(adsh_list)

        total_statuses = sum(report['status_counts'].values())
        assert total_statuses == report['count'] == len(adsh_list)

    def test_persist_filing_to_postgres_api(self, engine, monkeypatch):
        """PostgreSQL persistence should return write summary."""
        adsh = '0001628280-24-043777'

        class FakeStore:
            def __init__(self, config, schema="public"):
                self.config = config
                self.schema = schema

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return None

            def write_statement_tables(self, adsh, tables):
                assert 'BS' in tables
                return 123

            def write_validation_report(self, adsh, report):
                assert report['adsh'] == adsh

        monkeypatch.setattr("src.core.engine.PostgresStore", FakeStore)

        result = engine.persist_filing_to_postgres(
            adsh=adsh,
            db_config={"dbname": "sec_recon", "user": "tester", "host": "localhost", "port": "5432"},
            schema="public",
            include_validation_report=True,
        )
        assert result["adsh"] == adsh
        assert result["rows_written"] == 123
        assert result["validation_status"] in {"pass", "warn", "fail"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
