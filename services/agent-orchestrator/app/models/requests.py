"""Request and response models for Agent Orchestrator API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(description="Service status")
    service: str = Field(description="Service name")
    version: str = Field(description="Service version")
    redis_connected: bool = Field(description="Redis connection status")
    elasticsearch_connected: bool = Field(description="Elasticsearch connection status")


class LogAnalysisRequest(BaseModel):
    """Request for log analysis workflow."""

    log_content: str = Field(description="Log content to analyze")
    log_type: str = Field(default="build", description="Type of log (build/deploy/runtime)")
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional context (repo, commit, etc.)",
    )


class LogAnalysisResponse(BaseModel):
    """Response from log analysis workflow."""

    analysis_id: str = Field(description="Unique analysis ID")
    root_cause: str = Field(description="Identified root cause")
    severity: str = Field(description="Issue severity (critical/high/medium/low)")
    suggested_fixes: List[str] = Field(description="List of suggested fixes")
    references: List[str] = Field(
        default_factory=list,
        description="Related documentation/issues",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence score of analysis",
    )


class WorkflowExecutionRequest(BaseModel):
    """Generic workflow execution request."""

    workflow_type: str = Field(description="Type of workflow to execute")
    inputs: Dict[str, Any] = Field(description="Workflow input parameters")
    options: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Execution options",
    )


class WorkflowExecutionResponse(BaseModel):
    """Generic workflow execution response."""

    execution_id: str = Field(description="Unique execution ID")
    status: str = Field(description="Execution status (running/completed/failed)")
    outputs: Dict[str, Any] = Field(description="Workflow outputs")
    execution_time: float = Field(description="Execution time in seconds")
    error: Optional[str] = Field(default=None, description="Error message if failed")
