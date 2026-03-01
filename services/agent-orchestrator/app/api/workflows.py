"""Workflow execution API endpoints."""

import logging
import time
import traceback
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.models.requests import (
    LogAnalysisRequest,
    LogAnalysisResponse,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
)
from app.dependencies import get_analyze_log_use_case
from app.application.use_cases.analyze_log import AnalyzeLogUseCase
from app.agents.analyzer import LogAnalyzerAgent

router = APIRouter(prefix="/workflows", tags=["workflows"])
logger = logging.getLogger(__name__)



@router.post("/analyze-log", response_model=LogAnalysisResponse)
async def analyze_log(
    request: LogAnalysisRequest,
    use_case: AnalyzeLogUseCase = Depends(get_analyze_log_use_case),
) -> LogAnalysisResponse:
    """
    Analyze build/deploy logs using AI agent.
    
    This endpoint:
    1. Accepts use case via dependency injection
    2. Calls use_case.execute() with log content
    3. Converts domain model to response DTO
    4. Returns structured analysis results
    
    Args:
        request: Log analysis request with log content and context
        use_case: AnalyzeLogUseCase injected by FastAPI
        
    Returns:
        Structured analysis with root cause, fixes, and references
        
    Raises:
        HTTPException: If analysis fails
    """
    try:
        start_time = time.time()
        
        # Execute analysis via use case (with DI)
        analysis = await use_case.execute(request.log_content)
        
        execution_time = time.time() - start_time
        
        # Convert domain model to response DTO
        suggested_fixes = analysis.get_remediation_steps()
        severity_str = analysis.severity.name.lower()
        root_cause_desc = (
            analysis.root_causes[0].description if analysis.root_causes else "Unknown"
        )
        
        response = LogAnalysisResponse(
            analysis_id=str(analysis.id),
            root_cause=root_cause_desc,
            severity=severity_str,
            suggested_fixes=suggested_fixes,
            references=[],  # TODO: Extract from root causes or external source
            confidence=analysis.confidence.score,
        )
        
        return response
        
    except ValueError as e:
        error_msg = f"Log analysis validation error: {str(e)}"
        error_trace = traceback.format_exc()
        logger.error(f"{error_msg}\n{error_trace}")
        print(f"[ERROR] {error_msg}", flush=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    except Exception as e:
        error_msg = f"Log analysis failed: {str(e)}"
        error_trace = traceback.format_exc()
        logger.error(f"{error_msg}\n{error_trace}")
        print(f"[ERROR] {error_msg}", flush=True)
        print(error_trace, flush=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{error_msg}\n{error_trace}",
        )

@router.post("/analyze-log/stream")
async def analyze_log_stream(request: LogAnalysisRequest):
    """
    Analyze build/deploy logs with streaming response (SSE).
    
    Returns real-time analysis progress as tokens are generated.
    Useful for long-running analysis to provide immediate feedback.
    
    Args:
        request: Log analysis request with log content and context
        
    Returns:
        Server-Sent Events stream with analysis tokens
    """
    try:
        async def event_generator():
            """Generate SSE events for streaming analysis."""
            try:
                # Create agent
                agent = LogAnalyzerAgent()
                
                # Build analysis prompt
                prompt = f"""Analyze the following {request.log_type} log and identify:
1. Root cause of failure
2. Severity level (low/medium/high/critical)
3. Suggested fixes
4. References to documentation

Log content:
{request.log_content}"""
                
                # Stream LLM response
                full_text = ""
                async for chunk in agent.llm.astream(prompt):
                    token = chunk
                    full_text += token
                    
                    # Send token event
                    import json
                    yield f"event: token\n"
                    yield f"data: {{\"token\": {json.dumps(token)}}}\n\n"
                
                # Send done event
                yield f"event: done\n"
                yield f"data: {{\"full_text\": {json.dumps(full_text)}}}\n\n"
                
            except Exception as e:
                # Send error event
                import json
                yield f"event: error\n"
                yield f"data: {{\"error\": {json.dumps(str(e))}}}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Streaming log analysis failed: {str(e)}",
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
