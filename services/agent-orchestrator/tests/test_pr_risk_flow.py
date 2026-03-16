"""Tests for PR risk LangGraph flow.

Covers: PRRiskState schema, build_pr_risk_graph compilation, run_pr_risk execution,
node wrapper functions, stability wrappers (CircuitBreaker + run_with_retry),
degraded mode, and package exports.
"""



# ---------------------------------------------------------------------------
# PRRiskState schema
# ---------------------------------------------------------------------------


class TestPRRiskState:
    """PRRiskState TypedDict shape."""

    def test_has_diff_key(self):
        from app.workflows.pr_risk_flow import PRRiskState

        assert "diff" in PRRiskState.__annotations__

    def test_has_report_key(self):
        from app.workflows.pr_risk_flow import PRRiskState

        assert "report" in PRRiskState.__annotations__

    def test_has_errors_key(self):
        from app.workflows.pr_risk_flow import PRRiskState

        assert "errors" in PRRiskState.__annotations__

    def test_has_degraded_key(self):
        from app.workflows.pr_risk_flow import PRRiskState

        assert "degraded" in PRRiskState.__annotations__

    def test_has_retry_summary_key(self):
        from app.workflows.pr_risk_flow import PRRiskState

        assert "retry_summary" in PRRiskState.__annotations__


# ---------------------------------------------------------------------------
# build_pr_risk_graph
# ---------------------------------------------------------------------------


class TestBuildPRRiskGraph:
    """build_pr_risk_graph returns a compiled LangGraph."""

    def test_returns_compiled_graph(self):
        from langgraph.graph.state import CompiledStateGraph

        from app.workflows.pr_risk_flow import build_pr_risk_graph

        graph = build_pr_risk_graph()
        assert isinstance(graph, CompiledStateGraph)

    def test_graph_has_expected_nodes(self):
        from app.workflows.pr_risk_flow import build_pr_risk_graph

        graph = build_pr_risk_graph()
        node_names = set(graph.nodes.keys())
        assert "diff_parser" in node_names
        assert "risk_analyst" in node_names
        assert "summarizer" in node_names

    def test_graph_is_deterministic(self):
        """Building twice yields equivalent graphs."""
        from app.workflows.pr_risk_flow import build_pr_risk_graph

        g1 = build_pr_risk_graph()
        g2 = build_pr_risk_graph()
        assert set(g1.nodes.keys()) == set(g2.nodes.keys())


# ---------------------------------------------------------------------------
# run_pr_risk (end-to-end, no LLM)
# ---------------------------------------------------------------------------


class TestRunPRRisk:
    """run_pr_risk orchestrates the full pipeline and returns risk report."""

    async def test_returns_dict(self):
        from app.workflows.pr_risk_flow import run_pr_risk

        result = await run_pr_risk({"diff": "diff --git a/x b/x", "context": {}})
        assert isinstance(result, dict)

    async def test_result_has_report(self):
        from app.models.review import PRRiskReport
        from app.workflows.pr_risk_flow import run_pr_risk

        result = await run_pr_risk({"diff": "diff --git a/x b/x", "context": {}})
        assert "report" in result
        assert isinstance(result["report"], PRRiskReport)

    async def test_report_has_valid_risk_level(self):
        from app.workflows.pr_risk_flow import run_pr_risk

        result = await run_pr_risk({"diff": "diff --git a/x b/x", "context": {}})
        assert result["report"].risk_level in ("low", "medium", "high", "critical")

    async def test_result_has_analysis(self):
        from app.workflows.pr_risk_flow import run_pr_risk

        result = await run_pr_risk({"diff": "diff --git a/x b/x", "context": {}})
        assert "analysis" in result

    async def test_result_has_summary(self):
        from app.models.review import ReviewSummary
        from app.workflows.pr_risk_flow import run_pr_risk

        result = await run_pr_risk({"diff": "diff --git a/x b/x", "context": {}})
        assert "summary" in result
        assert isinstance(result["summary"], ReviewSummary)

    async def test_result_preserves_diff(self):
        from app.workflows.pr_risk_flow import run_pr_risk

        diff_text = "diff --git a/file.py b/file.py"
        result = await run_pr_risk({"diff": diff_text})
        assert result.get("diff") == diff_text


# ---------------------------------------------------------------------------
# Stability wrappers (degraded mode)
# ---------------------------------------------------------------------------


class TestPRRiskStability:
    """Stability: retry + circuit breaker + degraded mode."""

    async def test_force_fail_returns_degraded(self):
        from app.workflows.pr_risk_flow import run_pr_risk

        result = await run_pr_risk({"diff": "diff", "context": {}, "force_fail": "diff_parser"})
        assert result["degraded"] is True
        assert len(result["errors"]) > 0

    async def test_force_fail_error_has_node_info(self):
        from app.workflows.pr_risk_flow import run_pr_risk

        result = await run_pr_risk({"diff": "diff", "context": {}, "force_fail": "diff_parser"})
        err = result["errors"][0]
        assert "node" in err
        assert "message" in err

    async def test_circuit_breaker_open_returns_degraded(self):
        from app.workflows.pr_risk_flow import run_pr_risk

        result = await run_pr_risk({"diff": "diff", "context": {}, "simulate_breaker": True})
        assert result["degraded"] is True
        assert any(e.get("error_type") == "dependency" for e in result["errors"])

    async def test_retry_summary_present(self):
        from app.workflows.pr_risk_flow import run_pr_risk

        result = await run_pr_risk({"diff": "diff --git a/x b/x", "context": {}})
        assert "retry_summary" in result


# ---------------------------------------------------------------------------
# Package-level exports
# ---------------------------------------------------------------------------


class TestPRRiskExports:
    """Verify new symbols are exported from workflows package."""

    def test_run_pr_risk_importable_from_workflows(self):
        from app.workflows import run_pr_risk
        from app.workflows.pr_risk_flow import run_pr_risk as direct

        assert run_pr_risk is direct

    def test_build_pr_risk_graph_importable_from_workflows(self):
        from app.workflows import build_pr_risk_graph
        from app.workflows.pr_risk_flow import build_pr_risk_graph as direct

        assert build_pr_risk_graph is direct
