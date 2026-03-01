"""Response DTO for log analysis endpoint.

Serializes domain models to API-appropriate format with graceful
handling of optional/nullable fields.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.models.confidence import Confidence
from app.domain.models.log_analysis import LogAnalysis
from app.domain.models.root_cause import RootCause
from app.domain.models.severity import Severity


class RootCauseDTO(BaseModel):
    """DTO for root cause information.
    
    Serializes RootCause domain value object to API response format.
    """

    description: str = Field(
        ...,
        description="Human-readable description of the root cause"
    )
    component: str = Field(
        ...,
        description="System component where root cause was identified"
    )
    remediation: str = Field(
        ...,
        description="Recommended action to fix the root cause"
    )

    @classmethod
    def from_domain(cls, root_cause: RootCause) -> "RootCauseDTO":
        """Convert domain RootCause to DTO.
        
        Args:
            root_cause: RootCause value object from domain
            
        Returns:
            RootCauseDTO instance
        """
        return cls(
            description=root_cause.description,
            component=root_cause.component,
            remediation=root_cause.remediation,
        )


class LogAnalysisResponse(BaseModel):
    """Response DTO for log analysis results.
    
    Serializes LogAnalysis domain model to JSON-safe format suitable
    for HTTP responses. Handles optional/None fields gracefully.
    
    Attributes:
        id: Unique analysis identifier
        severity: Severity level (LOW/MEDIUM/HIGH/CRITICAL)
        confidence: Confidence percentage (0-100%)
        root_causes: List of identified root causes
        summary: Human-readable findings summary
        is_actionable: Whether analysis warrants action (high confidence + fixes)
        is_critical: Whether issues are critical severity
        is_resolved: Whether identified issues have been resolved
        remediation_steps: Ordered list of recommended fixes
    """

    id: str = Field(
        ...,
        description="Unique identifier for this analysis"
    )
    severity: str = Field(
        ...,
        description="Severity level: LOW, MEDIUM, HIGH, CRITICAL"
    )
    confidence: str = Field(
        ...,
        description="Confidence percentage (e.g., '85.5%')"
    )
    root_causes: list = Field(
        default_factory=list,
        description="Identified root causes"
    )
    summary: Optional[str] = Field(
        None,
        description="Human-readable analysis summary"
    )
    is_actionable: bool = Field(
        ...,
        description="True if confidence > 70% and has fixes"
    )
    is_critical: bool = Field(
        ...,
        description="True if severity is HIGH or CRITICAL"
    )
    is_resolved: bool = Field(
        default=False,
        description="Whether identified issues have been resolved"
    )
    remediation_steps: list = Field(
        default_factory=list,
        description="Ordered remediation recommendations"
    )

    @classmethod
    def from_domain(cls, analysis: Optional["LogAnalysis"]) -> Optional["LogAnalysisResponse"]:
        """Convert domain LogAnalysis to DTO.
        
        Gracefully handles None input and None optional fields,
        ensuring safe serialization to JSON.
        
        Args:
            analysis: LogAnalysis domain model, or None
            
        Returns:
            LogAnalysisResponse instance, or None if input is None
            
        Example:
            >>> domain_obj = LogAnalysis(...)
            >>> dto = LogAnalysisResponse.from_domain(domain_obj)
            >>> json_str = dto.model_dump_json()
        """
        if analysis is None:
            return None

        return cls(
            id=str(analysis.id),
            severity=analysis.severity.name,
            confidence=str(analysis.confidence),
            root_causes=[
                RootCauseDTO.from_domain(rc)
                for rc in analysis.root_causes
            ],
            summary=analysis.summary if analysis.summary else None,
            is_actionable=analysis.is_actionable(),
            is_critical=analysis.is_critical(),
            is_resolved=analysis.is_resolved,
            remediation_steps=analysis.get_remediation_steps(),
        )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "severity": "HIGH",
                "confidence": "92.3%",
                "root_causes": [
                    {
                        "description": "Database connection pool exhausted",
                        "component": "DatabaseService",
                        "remediation": "Increase connection pool size to 100"
                    }
                ],
                "summary": "High-severity database connectivity issue detected",
                "is_actionable": True,
                "is_critical": True,
                "is_resolved": False,
                "remediation_steps": [
                    "Increase connection pool size to 100",
                ]
            }
        }
