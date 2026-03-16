from typing import List

from pydantic import BaseModel, Field, field_validator


class IncidentReport(BaseModel):
    root_cause: str
    evidence: List[str]
    remediation: List[str]
    rollback: List[str]

    @field_validator("root_cause")
    @classmethod
    def root_cause_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("root_cause must not be empty")
        return v

    @field_validator("evidence")
    @classmethod
    def evidence_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("evidence must contain at least one item")
        return v

    @field_validator("remediation")
    @classmethod
    def remediation_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("remediation must contain at least one item")
        return v

    @field_validator("rollback")
    @classmethod
    def rollback_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("rollback must contain at least one item")
        return v


class MetricsSummary(BaseModel):
    error_rate: float = Field(default=0.0, ge=0.0)
    latency_p99_ms: float = Field(default=0.0, ge=0.0)
    anomalies: List[str] = Field(default_factory=list)


class ChangeImpact(BaseModel):
    files_changed: List[str] = Field(default_factory=list)
    risk_level: str = Field(pattern=r"^(low|medium|high|critical)$")
    summary: str

    @field_validator("summary")
    @classmethod
    def summary_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("summary must not be empty")
        return v
