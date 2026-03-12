"""Tests for code review LangGraph flow.

Covers: CodeReviewState schema, build_code_review_graph compilation,
run_code_review execution, node wrapper functions, stability wrappers
(CircuitBreaker + run_with_retry), degraded mode, and package exports.
"""

import pytest


# ---------------------------------------------------------------------------
# CodeReviewState schema
# ---------------------------------------------------------------------------


class TestCodeReviewState:
    """CodeReviewState TypedDict shape."""

    def test_has_diff_key(self):
        from app.workflows.code_review_flow import CodeReviewState

        assert "diff" in CodeReviewState.__annotations__

    def test_has_comments_key(self):
        from app.workflows.code_review_flow import CodeReviewState

        assert "comments" in CodeReviewState.__annotations__

    def test_has_summary_key(self):
        from app.workflows.code_review_flow import CodeReviewState

        assert "summary" in CodeReviewState.__annotations__

    def test_has_errors_key(self):
        from app.workflows.code_review_flow import CodeReviewState

        assert "errors" in CodeReviewState.__annotations__

    def test_has_degraded_key(self):
        from app.workflows.code_review_flow import CodeReviewState

        assert "degraded" in CodeReviewState.__annotations__

    def test_has_retry_summary_key(self):
        from app.workflows.code_review_flow import CodeReviewState

        assert "retry_summary" in CodeReviewState.__annotations__


# ---------------------------------------------------------------------------
# build_code_review_graph
# ---------------------------------------------------------------------------


class TestBuildCodeReviewGraph:
    """build_code_review_graph returns a compiled LangGraph."""

    def test_returns_compiled_graph(self):
        from langgraph.graph.state import CompiledStateGraph

        from app.workflows.code_review_flow import build_code_review_graph

        graph = build_code_review_graph()
        assert isinstance(graph, CompiledStateGraph)

    def test_graph_has_expected_nodes(self):
        from app.workflows.code_review_flow import build_code_review_graph

        graph = build_code_review_graph()
        node_names = set(graph.nodes.keys())
        assert "diff_parser" in node_names
        assert "reviewer" in node_names
        assert "summarizer" in node_names

    def test_graph_is_deterministic(self):
        """Building twice yields equivalent graphs."""
        from app.workflows.code_review_flow import build_code_review_graph

        g1 = build_code_review_graph()
        g2 = build_code_review_graph()
        assert set(g1.nodes.keys()) == set(g2.nodes.keys())


# ---------------------------------------------------------------------------
# run_code_review (end-to-end, no LLM)
# ---------------------------------------------------------------------------


class TestRunCodeReview:
    """run_code_review orchestrates the full pipeline and returns review."""

    async def test_returns_dict(self):
        from app.workflows.code_review_flow import run_code_review

        result = await run_code_review({"diff": "diff --git a/x b/x", "context": {}})
        assert isinstance(result, dict)

    async def test_result_has_comments(self):
        from app.models.review import ReviewComment
        from app.workflows.code_review_flow import run_code_review

        result = await run_code_review({"diff": "diff --git a/x b/x", "context": {}})
        assert "comments" in result
        assert isinstance(result["comments"], list)
        assert all(isinstance(c, ReviewComment) for c in result["comments"])

    async def test_result_has_summary(self):
        from app.models.review import ReviewSummary
        from app.workflows.code_review_flow import run_code_review

        result = await run_code_review({"diff": "diff --git a/x b/x", "context": {}})
        assert "summary" in result
        assert isinstance(result["summary"], ReviewSummary)

    async def test_result_has_analysis(self):
        from app.workflows.code_review_flow import run_code_review

        result = await run_code_review({"diff": "diff --git a/x b/x", "context": {}})
        assert "analysis" in result

    async def test_result_preserves_diff(self):
        from app.workflows.code_review_flow import run_code_review

        diff_text = "diff --git a/file.py b/file.py"
        result = await run_code_review({"diff": diff_text})
        assert result.get("diff") == diff_text


# ---------------------------------------------------------------------------
# Stability wrappers (degraded mode)
# ---------------------------------------------------------------------------


class TestCodeReviewStability:
    """Stability: retry + circuit breaker + degraded mode."""

    async def test_force_fail_returns_degraded(self):
        from app.workflows.code_review_flow import run_code_review

        result = await run_code_review({"diff": "diff", "context": {}, "force_fail": "diff_parser"})
        assert result["degraded"] is True
        assert len(result["errors"]) > 0

    async def test_force_fail_error_has_node_info(self):
        from app.workflows.code_review_flow import run_code_review

        result = await run_code_review({"diff": "diff", "context": {}, "force_fail": "diff_parser"})
        err = result["errors"][0]
        assert "node" in err
        assert "message" in err

    async def test_circuit_breaker_open_returns_degraded(self):
        from app.workflows.code_review_flow import run_code_review

        result = await run_code_review({"diff": "diff", "context": {}, "simulate_breaker": True})
        assert result["degraded"] is True
        assert any(e.get("error_type") == "dependency" for e in result["errors"])

    async def test_retry_summary_present(self):
        from app.workflows.code_review_flow import run_code_review

        result = await run_code_review({"diff": "diff --git a/x b/x", "context": {}})
        assert "retry_summary" in result


# ---------------------------------------------------------------------------
# Package-level exports
# ---------------------------------------------------------------------------


class TestCodeReviewExports:
    """Verify new symbols are exported from workflows package."""

    def test_run_code_review_importable_from_workflows(self):
        from app.workflows import run_code_review
        from app.workflows.code_review_flow import run_code_review as direct

        assert run_code_review is direct

    def test_build_code_review_graph_importable_from_workflows(self):
        from app.workflows import build_code_review_graph
        from app.workflows.code_review_flow import build_code_review_graph as direct

        assert build_code_review_graph is direct
