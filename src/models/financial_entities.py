"""Financial statement entity models."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import date


class Company(BaseModel):
    """Company information model."""
    
    cik: str = Field(..., description="Central Index Key")
    name: str = Field(..., description="Company name")
    ticker: Optional[str] = Field(None, description="Stock ticker symbol")
    sic: Optional[str] = Field(None, description="Standard Industrial Classification")
    country: Optional[str] = Field(None, description="Country of incorporation")
    state: Optional[str] = Field(None, description="State of incorporation")
    ein: Optional[str] = Field(None, description="Employer Identification Number")
    fiscal_year_end: Optional[str] = Field(None, description="Fiscal year end month (e.g., '1231')")


class FinancialFact(BaseModel):
    """Individual financial fact/data point."""
    
    concept: str = Field(..., description="XBRL concept identifier")
    value: Optional[float] = Field(None, description="Numeric value")
    unit: Optional[str] = Field(None, description="Unit of measurement (e.g., 'USD', 'shares')")
    context: Optional[str] = Field(None, description="XBRL context identifier")
    period_start: Optional[date] = Field(None, description="Period start date")
    period_end: Optional[date] = Field(None, description="Period end date")
    instant: Optional[date] = Field(None, description="Instant date for point-in-time facts")


class BalanceSheet(BaseModel):
    """Balance sheet statement."""
    
    company: Company
    as_of_date: date
    assets: Dict[str, float] = Field(default_factory=dict, description="Asset line items")
    liabilities: Dict[str, float] = Field(default_factory=dict, description="Liability line items")
    equity: Dict[str, float] = Field(default_factory=dict, description="Equity line items")
    facts: List[FinancialFact] = Field(default_factory=list)


class IncomeStatement(BaseModel):
    """Income statement."""
    
    company: Company
    period_start: date
    period_end: date
    revenues: Dict[str, float] = Field(default_factory=dict, description="Revenue line items")
    expenses: Dict[str, float] = Field(default_factory=dict, description="Expense line items")
    income: Dict[str, float] = Field(default_factory=dict, description="Income line items")
    facts: List[FinancialFact] = Field(default_factory=list)


class CashFlowStatement(BaseModel):
    """Cash flow statement."""
    
    company: Company
    period_start: date
    period_end: date
    operating_activities: Dict[str, float] = Field(default_factory=dict)
    investing_activities: Dict[str, float] = Field(default_factory=dict)
    financing_activities: Dict[str, float] = Field(default_factory=dict)
    facts: List[FinancialFact] = Field(default_factory=list)


class FinancialStatement(BaseModel):
    """Consolidated financial statement container."""
    
    company: Company
    period: str = Field(..., description="Reporting period (e.g., 'Q3-2024', 'FY-2024')")
    filing_date: date
    balance_sheet: Optional[BalanceSheet] = None
    income_statement: Optional[IncomeStatement] = None
    cash_flow_statement: Optional[CashFlowStatement] = None
    metadata: Dict[str, str] = Field(default_factory=dict)
