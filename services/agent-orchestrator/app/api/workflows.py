"""Workflow execution API endpoints."""

import time
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, status

from app.models.requests import (
    LogAnalysisRequest,
    LogAnalysisResponse,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
)
from app.agents.analyzer import LogAnalyzerAgent

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/analyze-log", response_model=LogAnalysisResponse)
async def analyze_log(request: LogAnalysisRequest) -> LogAnalysisResponse:
    """
    Analyze build/deploy logs using AI agent.
    
    This endpoint:
    1. Creates a LogAnalyzerAgent
    2. Executes analysis workflow with RAG search
    3. Returns structured analysis results
    
    Args:
        request: Log analysis request with log content and context
        
    Returns:
        Structured analysis with root cause, fixes, and references
        
    Raises:
        HTTPException: If analysis fails
    """
    try:
        start_time = time.time()
        
        # Create agent
        agent = LogAnalyzerAgent()
        
        # Execute analysis
        result = await agent.execute({
            "log_content": request.log_content,
            "log_type": request.log_type,
            "context": request.context or {},
        })
        
        execution_time = time.time() - start_time
        
        # Build response
        response = LogAnalysisResponse(
            analysis_id=result["analysis_id"],
            root_cause=result["root_cause"],
            severity=result["severity"],
            suggested_fixes=result["suggested_fixes"],
            references=result["references"],
            confidence=result["confidence"],
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Log analysis failed: {str(e)}",
        )


@router.post("/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(request: WorkflowExecutionRequest) -> WorkflowExecutionResponse:
    """
    Execute generic workflow by type.
    
    Supports multiple workflow types:
    - log_analysis: Build/deploy log analysis
    - code_review: PR review workflow (future)
    - metrics_calculation: DORA metrics (future)
    
    Args:
        request: Workflow execution request with type and inputs
        
    Returns:
        Workflow execution results
        
    Raises:
        HTTPException: If workflow type unsupported or execution fails
    """
    import uuid
    
    start_time = time.time()
    execution_id = str(uuid.uuid4())
    
    try:
        # Route by workflow type
        if request.workflow_type == "log_analysis":
            result = await _execute_log_analysis_workflow(request.inputs)
            
        elif request.workflow_type == "code_review":
            # Future implementation
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Code review workflow not yet implemented",
            )
            
        elif request.workflow_type == "metrics_calculation":
            # Future implementation
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Metrics calculation workflow not yet implemented",
            )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown workflow type: {request.workflow_type}",
            )
        
        execution_time = time.time() - start_time
        
        return WorkflowExecutionResponse(
            execution_id=execution_id,
            status="completed",
            outputs=result,
            execution_time=execution_time,
            error=None,
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        execution_time = time.time() - start_time
        
        return WorkflowExecutionResponse(
            execution_id=execution_id,
            status="failed",
            outputs={},
            execution_time=execution_time,
            error=str(e),
        )


async def _execute_log_analysis_workflow(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute log analysis workflow.
    
    Args:
        inputs: Must contain log_content, optionally log_type and context
        
    Returns:
        Analysis results
        
    Raises:
        ValueError: If required inputs missing
    """
    if "log_content" not in inputs:
        raise ValueError("Missing required input: log_content")
    
    agent = LogAnalyzerAgent()
    result = await agent.execute(inputs)
    
    return result


@router.get("/types")
async def list_workflow_types() -> Dict[str, Any]:
    """
    List available workflow types.
    
    Returns:
        Dictionary of workflow types and their descriptions
    """
    return {
        "workflows": [
            {
                "type": "log_analysis",
                "name": "Log Analysis",
                "description": "Analyze build/deploy logs for failures",
                "status": "available",
                "inputs": ["log_content", "log_type", "context"],
            },
            {
                "type": "code_review",
                "name": "Code Review",
                "description": "AI-powered PR review",
                "status": "planned",
                "inputs": ["pr_diff", "metadata"],
            },
            {
                "type": "metrics_calculation",
                "name": "DORA Metrics",
                "description": "Calculate DORA metrics from events",
                "status": "planned",
                "inputs": ["time_range", "repository"],
            },
        ]
    }
