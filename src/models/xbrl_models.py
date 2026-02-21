"""XBRL-specific data models."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import date


class XBRLUnit(BaseModel):
    """XBRL Unit element."""
    
    unit_id: str = Field(..., description="Unit identifier")
    measure: str = Field(..., description="Measurement unit (e.g., 'xbrli:pure', 'iso4217:USD')")


class XBRLContext(BaseModel):
    """XBRL Context element."""
    
    context_id: str = Field(..., description="Context identifier")
    entity: str = Field(..., description="Entity identifier (CIK)")
    period_type: Optional[str] = Field(None, description="Duration or instant")
    period_start: Optional[date] = Field(None, description="Start date for duration")
    period_end: Optional[date] = Field(None, description="End date or instant date")
    scenario: Optional[str] = Field(None, description="Scenario dimension")


class XBRLFact(BaseModel):
    """XBRL Fact element."""
    
    concept: str = Field(..., description="XBRL concept name")
    context_id: str = Field(..., description="Reference to context")
    unit_id: Optional[str] = Field(None, description="Reference to unit")
    value: Optional[str] = Field(None, description="Fact value")
    decimals: Optional[int] = Field(None, description="Number of decimals")
    xml_attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional XML attributes")


class XBRLInstance(BaseModel):
    """Complete XBRL instance document."""
    
    filename: str = Field(..., description="Instance document filename")
    contexts: Dict[str, XBRLContext] = Field(default_factory=dict)
    units: Dict[str, XBRLUnit] = Field(default_factory=dict)
    facts: Dict[str, list[XBRLFact]] = Field(default_factory=dict)
    metadata: Dict[str, str] = Field(default_factory=dict)
