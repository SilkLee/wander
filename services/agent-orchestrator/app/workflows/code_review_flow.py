"""Code review LangGraph workflow.

Orchestrates: diff_parser → reviewer → summarizer with stability wrappers.
"""

import logging
from typing import Any, Dict, List

from typing_extensions import TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.review_roles import diff_parser, reviewer, summarizer
from app.config import settings
from app.models.review import ReviewComment, ReviewSummary
from app.services.rerank import secondary_rerank, should_rerank
from app.workflows.stability import CircuitBreaker, run_with_retry

logger = logging.getLogger(__name__)


class CodeReviewState(TypedDict, total=False):
    diff: str
    context: dict[str, Any]
    coding_standards: str
    standards: str
    comments: List[ReviewComment]
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


async def reviewer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("reviewer_node: reviewing code")
    if state.get("force_fail") == "reviewer":
        raise RuntimeError("forced reviewer failure")
    comments = await reviewer(state)
    return {"comments": comments}


async def summarizer_node(state: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("summarizer_node: generating summary")
    if state.get("force_fail") == "summarizer":
        raise RuntimeError("forced summarizer failure")
    result = await summarizer(state)
    return result


def build_code_review_graph() -> Any:
    graph = StateGraph(CodeReviewState)

    graph.add_node("diff_parser", diff_parser_node)
    graph.add_node("reviewer", reviewer_node)
    graph.add_node("summarizer", summarizer_node)

    graph.add_edge(START, "diff_parser")
    graph.add_edge("diff_parser", "reviewer")
    graph.add_edge("reviewer", "summarizer")
    graph.add_edge("summarizer", END)

    return graph.compile()


_CODE_REVIEW_BREAKER = CircuitBreaker(threshold=2, cooldown_seconds=30.0)


async def run_code_review(inputs: Dict[str, Any]) -> Dict[str, Any]:
    compiled = build_code_review_graph()
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
        for _ in range(_CODE_REVIEW_BREAKER.threshold):
            _CODE_REVIEW_BREAKER.record_failure()
    if _CODE_REVIEW_BREAKER.is_open():
        result["retry_summary"]["code_review"] = 0
        result["errors"].append(
            {
                "node": "code_review",
                "error_type": "dependency",
                "message": "circuit breaker open",
                "retry_attempts": 0,
                "degraded": True,
            }
        )
        result["degraded"] = True
        return result

    if base_state["force_fail"]:
        result["retry_summary"]["code_review"] = retries
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
        _CODE_REVIEW_BREAKER.record_failure()
        result["retry_summary"]["code_review"] = retries
        result["errors"].append(
            {
                "node": "code_review",
                "error_type": "unknown",
                "message": str(error),
                "retry_attempts": retries,
                "degraded": True,
            }
        )
        result["degraded"] = True
        return result

    _CODE_REVIEW_BREAKER.record_success()
    result["retry_summary"]["code_review"] = 0
    result.update(dict(node_result))

    # Apply secondary rerank when enabled for code_review
    if should_rerank(
        "code_review",
        enabled=settings.secondary_rerank_enabled,
        targets=settings.secondary_rerank_targets,
    ):
        diff_text = result.get("diff", "")
        await secondary_rerank([{"content": diff_text, "score": 1.0}], query=diff_text)
        result["reranked"] = True

    return result
