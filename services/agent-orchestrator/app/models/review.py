from typing import Dict, List

from pydantic import BaseModel, Field


class PRRiskReport(BaseModel):
    risk_level: str = Field(pattern="^(low|medium|high|critical)$")
    impacted_areas: List[str] = Field(default_factory=list)
    checks: List[str] = Field(default_factory=list)
    rationale: str = Field(description="Reasoning for risk score")


class ReviewComment(BaseModel):
    file: str = Field(description="File path")
    line: int = Field(ge=1)
    severity: str = Field(pattern="^(info|warning|error)$")
    message: str = Field(description="Comment message")
    suggestion: str = Field(default="")


class ReviewSummary(BaseModel):
    summary: str = Field(description="Short overall summary")
    comments: List[ReviewComment] = Field(default_factory=list)
    severity_breakdown: Dict[str, int] = Field(default_factory=dict)
