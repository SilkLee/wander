from __future__ import annotations

import logging
import time
import traceback
from typing import Any, Dict, cast

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
from app.workflows.pr_risk_flow import run_pr_risk
from app.workflows.code_review_flow import run_code_review
from app.agents.langchain_tools_agent import run_tool_agent
from app.workflows.incident_response_flow import run_incident_response

router = APIRouter(prefix="/workflows", tags=["workflows"])
logger = logging.getLogger(__name__)


def _maybe_model_dump(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value


def _maybe_get_attr(value: Any, attr: str) -> Any | None:
    if hasattr(value, attr):
        return getattr(value, attr)
    return None


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
        root_cause_desc = analysis.root_causes[0].description if analysis.root_causes else "Unknown"

        intermediate_summary = {
            "severity": severity_str,
            "confidence_score": analysis.confidence.score,
            "root_cause_count": len(analysis.root_causes),
            "is_actionable": analysis.is_actionable(),
            "is_critical": analysis.is_critical(),
        }

        if result.langgraph_result is not None:
            langgraph_result = cast(dict[str, Any], result.langgraph_result)
            parsed = langgraph_result.get("parsed")
            diagnosis = langgraph_result.get("diagnosis")
            evidence = langgraph_result.get("evidence")
            remediation = langgraph_result.get("remediation")
            parsed_dump = _maybe_model_dump(parsed)
            diagnosis_dump = _maybe_model_dump(diagnosis)
            evidence_dump = _maybe_model_dump(evidence)
            remediation_dump = _maybe_model_dump(remediation)
            enriched_summary: Dict[str, Any] = {
                "parsed": parsed_dump,
                "diagnosis": diagnosis_dump,
                "evidence": evidence_dump,
                "remediation": remediation_dump,
                "errors": langgraph_result.get("errors", []),
                "retry_summary": langgraph_result.get("retry_summary", {}),
                "degraded": langgraph_result.get("degraded", False),
            }
            diagnosis_confidence = _maybe_get_attr(diagnosis, "confidence")
            if diagnosis_confidence is not None:
                enriched_summary["diagnosis_confidence"] = diagnosis_confidence
            parsed_source = _maybe_get_attr(parsed, "source")
            if parsed_source is not None:
                enriched_summary["parsed_source"] = parsed_source
            error_signatures = _maybe_get_attr(parsed, "error_signatures")
            if error_signatures is not None:
                enriched_summary["error_signatures"] = error_signatures
            remediation_steps = _maybe_get_attr(remediation, "steps")
            if remediation_steps is not None:
                enriched_summary["remediation_steps"] = remediation_steps
            evidence_citations = _maybe_get_attr(evidence, "citations")
            if evidence_citations is not None:
                enriched_summary["evidence_citations"] = evidence_citations
            intermediate_summary.update(enriched_summary)

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
                import json

                async for chunk in agent.llm.astream(prompt):
                    token = chunk
                    full_text += str(token)

                    # Send token event
                    yield f"event: token\n"
                    yield f'data: {{"token": {json.dumps(token)}}}\n\n'

                # Send done event
                yield f"event: done\n"
                yield f'data: {{"full_text": {json.dumps(full_text)}}}\n\n'

            except Exception as e:
                # Send error event
                import json

                yield f"event: error\n"
                yield f'data: {{"error": {json.dumps(str(e))}}}\n\n'

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

        elif request.workflow_type == "pr_risk":
            result = await run_pr_risk(request.inputs)

        elif request.workflow_type == "code_review":
            result = await run_code_review(request.inputs)

        elif request.workflow_type == "langchain_tool_agent":
            result = await run_tool_agent(request.inputs)

        elif request.workflow_type == "incident_response":
            result = await run_incident_response(request.inputs)
        elif request.workflow_type == "metrics_calculation":
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
                "type": "pr_risk",
                "name": "PR Risk Assessment",
                "description": "Assess risk level of a pull request",
                "status": "available",
                "inputs": ["diff", "context", "coding_standards"],
            },
            {
                "type": "code_review",
                "name": "Code Review",
                "description": "AI-powered PR review",
                "status": "available",
                "inputs": ["diff", "context", "coding_standards"],
            },
            {
                "type": "langchain_tool_agent",
                "name": "LangChain Tool Agent",
                "description": "Code-change analysis using ReAct agent with tools",
                "status": "available",
                "inputs": ["diff", "context"],
            },
            {
                "type": "incident_response",
                "name": "Incident Response",
                "description": "Automated incident triage with log parsing, metrics analysis, impact assessment, and remediation",
                "status": "available",
                "inputs": ["log_content", "alerts", "deploy_context"],
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
