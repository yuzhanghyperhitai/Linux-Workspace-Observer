"""Pydantic schemas for AI Agent structured output."""

from typing import List
from pydantic import BaseModel, Field


class AnomalyAnalysis(BaseModel):
    """AI Agent analysis result schema."""
    
    situation: str = Field(
        description="Brief description of what the user is currently doing"
    )
    issue: str = Field(
        description="Main problem identified"
    )
    root_cause: str = Field(
        description="Likely root cause of the issue"
    )
    analysis: str = Field(
        description="Detailed analysis of the situation"
    )
    suggestions: List[str] = Field(
        description="Specific actionable suggestions to resolve the issue"
    )
    confidence: float = Field(
        description="Confidence score from 0.0 to 1.0",
        ge=0.0,
        le=1.0
    )
