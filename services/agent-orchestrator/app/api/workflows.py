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
    try:
        # Execute analysis via use case (with DI)
        result = await use_case.execute(request.log_content)
        analysis = result.analysis
        
        # Convert domain model to response DTO
        suggested_fixes = analysis.get_remediation_steps()
        severity_str = analysis.severity.name.lower()
        root_cause_desc = (
            analysis.root_causes[0].description if analysis.root_causes else "Unknown"
        )
        
        intermediate_summary = {
            "severity": severity_str,
            "confidence_score": analysis.confidence.score,
            "root_cause_count": len(analysis.root_causes),
            "is_actionable": analysis.is_actionable(),
            "is_critical": analysis.is_critical(),
        }

        if result.langgraph_result is not None:
            parsed = result.langgraph_result.get("parsed")
            diagnosis = result.langgraph_result.get("diagnosis")
            evidence = result.langgraph_result.get("evidence")
            remediation = result.langgraph_result.get("remediation")
            intermediate_summary.update(
                {
                    "parsed": parsed.model_dump() if hasattr(parsed, "model_dump") else parsed,
                    "diagnosis": diagnosis.model_dump() if hasattr(diagnosis, "model_dump") else diagnosis,
                    "evidence": evidence.model_dump() if hasattr(evidence, "model_dump") else evidence,
                    "remediation": remediation.model_dump() if hasattr(remediation, "model_dump") else remediation,
                    "errors": result.langgraph_result.get("errors", []),
                    "retry_summary": result.langgraph_result.get("retry_summary", {}),
                    "degraded": result.langgraph_result.get("degraded", False),
                }
            )
            if hasattr(diagnosis, "confidence"):
                intermediate_summary["diagnosis_confidence"] = diagnosis.confidence
            if hasattr(parsed, "source"):
                intermediate_summary["parsed_source"] = parsed.source
            if hasattr(parsed, "error_signatures"):
                intermediate_summary["error_signatures"] = parsed.error_signatures
            if hasattr(remediation, "steps"):
                intermediate_summary["remediation_steps"] = remediation.steps
            if hasattr(evidence, "citations"):
                intermediate_summary["evidence_citations"] = evidence.citations

        response = LogAnalysisResponse(
            analysis_id=str(analysis.id),
            root_cause=root_cause_desc,
            severity=severity_str,
            suggested_fixes=suggested_fixes,
            references=[],  # TODO: Extract from root causes or external source
            confidence=analysis.confidence.score,
            intermediate_summary=intermediate_summary,
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
    try:
        async def event_generator():
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
    if "log_content" not in inputs:
        raise ValueError("Missing required input: log_content")
    
    agent = LogAnalyzerAgent()
    result = await agent.execute(inputs)
    
    return result


@router.get("/types")
async def list_workflow_types() -> Dict[str, Any]:
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
