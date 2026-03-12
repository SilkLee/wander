"""PR risk assessment LangGraph workflow.

Orchestrates: diff_parser → risk_analyst → summarizer with stability wrappers.
"""

import logging
from typing import Any, Dict

from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.review_roles import diff_parser, risk_analyst, summarizer
from app.models.review import PRRiskReport, ReviewSummary
from app.workflows.stability import CircuitBreaker, run_with_retry

logger = logging.getLogger(__name__)


class PRRiskState(TypedDict, total=False):
    diff: str
    context: dict[str, Any]
    coding_standards: str
    standards: str
    report: PRRiskReport
    summary: ReviewSummary
    analysis: str
    errors: list[dict[str, Any]]
    retry_summary: dict[str, int]
    degraded: bool
    force_fail: str


async def diff_parser_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("diff_parser_node: parsing diff (%d chars)", len(state.get("diff", "")))
    if state.get("force_fail") == "diff_parser":
        raise RuntimeError("forced diff_parser failure")
    result = await diff_parser(state)
    return result


async def risk_analyst_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("risk_analyst_node: analysing risk")
    if state.get("force_fail") == "risk_analyst":
        raise RuntimeError("forced risk_analyst failure")
    report = await risk_analyst(state)
    return {"report": report}


async def summarizer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("summarizer_node: generating summary")
    if state.get("force_fail") == "summarizer":
        raise RuntimeError("forced summarizer failure")
    result = await summarizer(state)
    return result


def build_pr_risk_graph() -> Any:
    graph = StateGraph(PRRiskState)

    graph.add_node("diff_parser", diff_parser_node)
    graph.add_node("risk_analyst", risk_analyst_node)
    graph.add_node("summarizer", summarizer_node)

    graph.add_edge(START, "diff_parser")
    graph.add_edge("diff_parser", "risk_analyst")
    graph.add_edge("risk_analyst", "summarizer")
    graph.add_edge("summarizer", END)

    return graph.compile()


_PR_RISK_BREAKER = CircuitBreaker(threshold=2, cooldown_seconds=30.0)


async def run_pr_risk(inputs: Dict[str, Any]) -> Dict[str, Any]:
    compiled = build_pr_risk_graph()
    base_state: Dict[str, Any] = {
        "diff": inputs.get("diff", ""),
        "context": inputs.get("context", {}),
        "coding_standards": inputs.get("coding_standards", ""),
        "errors": [],
        "retry_summary": {},
        "degraded": False,
        "force_fail": inputs.get("force_fail"),
    }
    result: Dict[str, Any] = dict(base_state)

    retries = 1
    timeout_seconds = 1.0

    if inputs.get("simulate_breaker"):
        for _ in range(_PR_RISK_BREAKER.threshold):
            _PR_RISK_BREAKER.record_failure()
    if _PR_RISK_BREAKER.is_open():
        result["retry_summary"]["pr_risk"] = 0
        result["errors"].append(
            {
                "node": "pr_risk",
                "error_type": "dependency",
                "message": "circuit breaker open",
                "retry_attempts": 0,
                "degraded": True,
            }
        )
        result["degraded"] = True
        return result

    if base_state["force_fail"]:
        result["retry_summary"]["pr_risk"] = retries
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

    node_result, error = await run_with_retry(
        invoke, retries=retries, timeout_seconds=timeout_seconds
    )
    if error is not None:
        _PR_RISK_BREAKER.record_failure()
        result["retry_summary"]["pr_risk"] = retries
        result["errors"].append(
            {
                "node": "pr_risk",
                "error_type": "unknown",
                "message": str(error),
                "retry_attempts": retries,
                "degraded": True,
            }
        )
        result["degraded"] = True
        return result

    _PR_RISK_BREAKER.record_success()
    result["retry_summary"]["pr_risk"] = 0
    result.update(dict(node_result))
    return result
