import logging
from typing import Any

from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.incident_roles import (
    change_impact as _change_impact_fn,
    coordinator as _coordinator_fn,
    metrics_analyzer as _metrics_analyzer_fn,
)
from app.agents.roles import parse_log, retrieve_evidence
from app.models.incident import ChangeImpact, IncidentReport, MetricsSummary
from app.models.intermediate import Diagnosis, EvidenceBundle, ParsedLog
from app.workflows.stability import CircuitBreaker, run_with_retry

logger = logging.getLogger(__name__)


class IncidentState(TypedDict, total=False):
    raw_log: str
    alerts: list[str]
    deploy_context: dict[str, Any]
    parsed: ParsedLog
    metrics: MetricsSummary
    impact: ChangeImpact
    evidence: EvidenceBundle
    report: IncidentReport
    errors: list[dict[str, Any]]
    retry_summary: dict[str, int]
    degraded: bool
    force_fail: str


async def log_parser_node(state: IncidentState) -> dict[str, Any]:
    raw_log: str = state.get("raw_log", "")
    logger.info("log_parser_node: parsing %d chars", len(raw_log))
    if state.get("force_fail") == "log_parser":
        raise RuntimeError("forced log_parser failure")
    payload = {"log_content": raw_log, "log_type": "incident", "context": {}}
    parsed = await parse_log(payload)
    return {"parsed": parsed}


async def metrics_analyzer_node(state: IncidentState) -> dict[str, Any]:
    logger.info("metrics_analyzer_node: analysing metrics")
    if state.get("force_fail") == "metrics_analyzer":
        raise RuntimeError("forced metrics_analyzer failure")
    deploy_ctx: dict[str, Any] = state.get("deploy_context", {})
    payload = {
        "alerts": state.get("alerts", []),
        "error_rate": deploy_ctx.get("error_rate", 0.0),
        "latency_p99_ms": deploy_ctx.get("latency_p99_ms", 0.0),
    }
    metrics = await _metrics_analyzer_fn(payload)
    return {"metrics": metrics}


async def change_impact_node(state: IncidentState) -> dict[str, Any]:
    logger.info("change_impact_node: evaluating change impact")
    if state.get("force_fail") == "change_impact":
        raise RuntimeError("forced change_impact failure")
    deploy_ctx: dict[str, Any] = state.get("deploy_context", {})
    payload = {
        "deploy_id": deploy_ctx.get("deploy_id", "unknown"),
        "files_changed": deploy_ctx.get("files_changed", []),
        "commit_message": deploy_ctx.get("commit_message", "unknown change"),
    }
    impact = await _change_impact_fn(payload)
    return {"impact": impact}


async def evidence_gatherer_node(state: IncidentState) -> dict[str, Any]:
    logger.info("evidence_gatherer_node: gathering evidence")
    if state.get("force_fail") == "evidence_gatherer":
        raise RuntimeError("forced evidence_gatherer failure")
    parsed: ParsedLog = state["parsed"]
    # Build a lightweight diagnosis from parsed log to feed into retrieve_evidence
    diagnosis = Diagnosis(
        root_cause_candidates=parsed.error_signatures or ["unknown"],
        confidence=0.5,
        reasoning="Auto-diagnosis from incident log parsing",
    )
    evidence = await retrieve_evidence(diagnosis)
    return {"evidence": evidence}


async def coordinator_node(state: IncidentState) -> dict[str, Any]:
    logger.info("coordinator_node: producing incident report")
    if state.get("force_fail") == "coordinator":
        raise RuntimeError("forced coordinator failure")
    metrics: MetricsSummary = state["metrics"]
    impact: ChangeImpact = state["impact"]
    report = await _coordinator_fn(metrics, impact)
    return {"report": report}


def build_incident_response_graph() -> Any:
    graph = StateGraph(IncidentState)

    graph.add_node("log_parser", log_parser_node)
    graph.add_node("metrics_analyzer", metrics_analyzer_node)
    graph.add_node("change_impact", change_impact_node)
    graph.add_node("evidence_gatherer", evidence_gatherer_node)
    graph.add_node("coordinator", coordinator_node)

    graph.add_edge(START, "log_parser")
    graph.add_edge("log_parser", "metrics_analyzer")
    graph.add_edge("metrics_analyzer", "change_impact")
    graph.add_edge("change_impact", "evidence_gatherer")
    graph.add_edge("evidence_gatherer", "coordinator")
    graph.add_edge("coordinator", END)

    return graph.compile()


_INCIDENT_BREAKER = CircuitBreaker(threshold=2, cooldown_seconds=30.0)


async def run_incident_response(inputs: dict[str, Any]) -> dict[str, Any]:
    compiled = build_incident_response_graph()
    raw_log = inputs.get("log_content", "")
    base_state: IncidentState = {
        "raw_log": raw_log,
        "alerts": inputs.get("alerts", []),
        "deploy_context": inputs.get("deploy_context", {}),
        "errors": [],
        "retry_summary": {},
        "degraded": False,
        "force_fail": inputs.get("force_fail"),
    }
    result: dict[str, Any] = dict(base_state)

    retries = 1
    timeout_seconds = 2.0

    # Circuit breaker check
    if inputs.get("simulate_breaker"):
        for _ in range(_INCIDENT_BREAKER.threshold):
            _INCIDENT_BREAKER.record_failure()
    if _INCIDENT_BREAKER.is_open():
        result["retry_summary"]["incident_response"] = 0
        result["errors"].append(
            {
                "node": "incident_response",
                "error_type": "dependency",
                "message": "circuit breaker open",
                "retry_attempts": 0,
                "degraded": True,
            }
        )
        result["degraded"] = True
        return result

    # Fast-path for forced failures (testing)
    if base_state["force_fail"]:
        result["retry_summary"]["incident_response"] = retries
        result["errors"].append(
            {
                "node": base_state["force_fail"],
                "error_type": "unknown",
                "message": "forced failure",
                "retry_attempts": retries,
                "degraded": True,
            }
        )
        result["degraded"] = True
        return result

    async def invoke() -> dict[str, Any]:
        return await compiled.ainvoke(base_state)

    node_result, error = await run_with_retry(
        invoke, retries=retries, timeout_seconds=timeout_seconds
    )
    if error is not None:
        _INCIDENT_BREAKER.record_failure()
        result["retry_summary"]["incident_response"] = retries
        result["errors"].append(
            {
                "node": "incident_response",
                "error_type": "unknown",
                "message": str(error),
                "retry_attempts": retries,
                "degraded": True,
            }
        )
        result["degraded"] = True
        return result

    _INCIDENT_BREAKER.record_success()
    result["retry_summary"]["incident_response"] = 0
    result.update(dict(node_result))
    return result
