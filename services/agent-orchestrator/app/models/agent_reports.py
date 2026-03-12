from typing import List

from pydantic import BaseModel, Field


class PRSummary(BaseModel):
    summary: str
    key_risks: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)


class RiskFinding(BaseModel):
    category: str
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    description: str


class DependencyRisk(BaseModel):
    package: str
    change_type: str = Field(pattern="^(upgrade|downgrade|add|remove)$")
    risk_level: str = Field(pattern="^(low|medium|high|critical)$")


class ImpactReport(BaseModel):
    services: List[str] = Field(default_factory=list)
    modules: List[str] = Field(default_factory=list)
    notes: str = ""
