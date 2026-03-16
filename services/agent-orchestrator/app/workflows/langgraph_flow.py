import logging
from typing import Any, Dict

from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.roles import diagnose, parse_log, remediate, retrieve_evidence
from app.models.intermediate import Diagnosis, EvidenceBundle, ParsedLog, Remediation
from app.workflows.stability import CircuitBreaker, run_with_retry

logger = logging.getLogger(__name__)


class TriageState(TypedDict, total=False):
    raw_log: str
    parsed: ParsedLog
    diagnosis: Diagnosis
    evidence: EvidenceBundle
    remediation: Remediation
    errors: list[dict[str, Any]]
    retry_summary: dict[str, int]
    degraded: bool

async def parse_log_node(state: Dict[str, Any]) -> Dict[str, Any]:
    raw_log: str = state.get("raw_log", "")
    logger.info("parse_log_node: parsing %d chars", len(raw_log))
    payload = {"log_content": raw_log, "log_type": "build", "context": {}}
    if state.get("force_fail") == "parse":
        raise RuntimeError("forced parse failure")
    parsed = await parse_log(payload)
    return {"parsed": parsed}

async def diagnose_node(state: Dict[str, Any]) -> Dict[str, Any]:
    parsed: ParsedLog = state["parsed"]
    logger.info("diagnose_node: %d error signatures", len(parsed.error_signatures))
    if state.get("force_fail") == "diagnose":
        raise RuntimeError("forced diagnose failure")
    diagnosis = await diagnose(parsed)
    return {"diagnosis": diagnosis}


async def gather_evidence_node(state: Dict[str, Any]) -> Dict[str, Any]:
    diagnosis: Diagnosis = state["diagnosis"]
    logger.info("gather_evidence_node: confidence=%.2f", diagnosis.confidence)
    if state.get("force_fail") == "gather_evidence":
        raise RuntimeError("forced evidence failure")
    evidence = await retrieve_evidence(diagnosis)
    return {"evidence": evidence}

async def remediate_node(state: Dict[str, Any]) -> Dict[str, Any]:
    diagnosis: Diagnosis = state["diagnosis"]
    logger.info("remediate_node: generating remediation")
    if state.get("force_fail") == "remediate":
        raise RuntimeError("forced remediate failure")
    remediation = await remediate(diagnosis, state["evidence"])
    return {"remediation": remediation}


async def severity_router(state: Dict[str, Any]) -> str:
    return "gather_evidence"

def build_triage_graph() -> Any:
    graph = StateGraph(TriageState)

    # Register nodes
    graph.add_node("parse_log", parse_log_node)
    graph.add_node("diagnose", diagnose_node)
    graph.add_node("gather_evidence", gather_evidence_node)
    graph.add_node("remediate", remediate_node)

    # Edges
    graph.add_edge(START, "parse_log")
    graph.add_edge("parse_log", "diagnose")
    graph.add_conditional_edges("diagnose", severity_router, ["gather_evidence"])
    graph.add_edge("gather_evidence", "remediate")
    graph.add_edge("remediate", END)

    return graph.compile()


def build_langgraph_flow() -> Dict[str, Any]:
    return {
        "parse_log": parse_log,
        "diagnose": diagnose,
        "retrieve_evidence": retrieve_evidence,
        "remediate": remediate,
    }


_TRIAGE_BREAKER = CircuitBreaker(threshold=2, cooldown_seconds=30.0)


async def run_langgraph(inputs: Dict[str, Any]) -> Dict[str, Any]:
    compiled = build_triage_graph()
    raw_log = inputs.get("log_content", "")
    base_state: Dict[str, Any] = {
        "raw_log": raw_log,
        "errors": [],
        "retry_summary": {},
        "degraded": False,
        "force_fail": inputs.get("force_fail"),
    }
    result: Dict[str, Any] = dict(base_state)

    retries = 1
    timeout_seconds = 1.0

    if inputs.get("simulate_breaker"):
        _TRIAGE_BREAKER.record_failure()
    if _TRIAGE_BREAKER.is_open():
        result["retry_summary"]["triage"] = 0
        result["errors"].append(
            {
                "node": "triage",
                "error_type": "dependency",
                "message": "circuit breaker open",
                "retry_attempts": 0,
                "degraded": True,
            }
        )
        result["degraded"] = True
        return result

    if base_state["force_fail"]:
        result["retry_summary"]["triage"] = retries
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

    async def invoke():
        return await compiled.ainvoke(base_state)

    node_result, error = await run_with_retry(invoke, retries=retries, timeout_seconds=timeout_seconds)
    if error is not None:
        _TRIAGE_BREAKER.record_failure()
        result["retry_summary"]["triage"] = retries
        result["errors"].append(
            {
                "node": "triage",
                "error_type": "unknown",
                "message": str(error),
                "retry_attempts": retries,
                "degraded": True,
            }
        )
        result["degraded"] = True
        return result

    _TRIAGE_BREAKER.record_success()
    result["retry_summary"]["triage"] = 0
    result.update(dict(node_result))
    return result
