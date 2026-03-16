import pytest


class TestIncidentState:
    def test_has_raw_log_key(self):
        from app.workflows.incident_response_flow import IncidentState

        assert "raw_log" in IncidentState.__annotations__

    def test_has_alerts_key(self):
        from app.workflows.incident_response_flow import IncidentState

        assert "alerts" in IncidentState.__annotations__

    def test_has_deploy_context_key(self):
        from app.workflows.incident_response_flow import IncidentState

        assert "deploy_context" in IncidentState.__annotations__

    def test_has_parsed_key(self):
        from app.workflows.incident_response_flow import IncidentState

        assert "parsed" in IncidentState.__annotations__

    def test_has_metrics_key(self):
        from app.workflows.incident_response_flow import IncidentState

        assert "metrics" in IncidentState.__annotations__

    def test_has_impact_key(self):
        from app.workflows.incident_response_flow import IncidentState

        assert "impact" in IncidentState.__annotations__

    def test_has_evidence_key(self):
        from app.workflows.incident_response_flow import IncidentState

        assert "evidence" in IncidentState.__annotations__

    def test_has_report_key(self):
        from app.workflows.incident_response_flow import IncidentState

        assert "report" in IncidentState.__annotations__

    def test_has_errors_key(self):
        from app.workflows.incident_response_flow import IncidentState

        assert "errors" in IncidentState.__annotations__

    def test_has_degraded_key(self):
        from app.workflows.incident_response_flow import IncidentState

        assert "degraded" in IncidentState.__annotations__

    def test_has_retry_summary_key(self):
        from app.workflows.incident_response_flow import IncidentState

        assert "retry_summary" in IncidentState.__annotations__


class TestBuildIncidentResponseGraph:
    def test_returns_compiled_graph(self):
        from langgraph.graph.state import CompiledStateGraph

        from app.workflows.incident_response_flow import build_incident_response_graph

        graph = build_incident_response_graph()
        assert isinstance(graph, CompiledStateGraph)

    def test_graph_has_expected_nodes(self):
        from app.workflows.incident_response_flow import build_incident_response_graph

        graph = build_incident_response_graph()
        node_names = set(graph.nodes.keys())
        assert "log_parser" in node_names
        assert "metrics_analyzer" in node_names
        assert "change_impact" in node_names
        assert "evidence_gatherer" in node_names
        assert "coordinator" in node_names

    def test_graph_is_deterministic(self):
        """Building twice yields equivalent graphs."""
        from app.workflows.incident_response_flow import build_incident_response_graph

        g1 = build_incident_response_graph()
        g2 = build_incident_response_graph()
        assert set(g1.nodes.keys()) == set(g2.nodes.keys())


class TestLogParserNode:
    async def test_returns_parsed_key(self):
        from app.workflows.incident_response_flow import log_parser_node

        result = await log_parser_node({"raw_log": "ERROR: connection refused"})
        assert "parsed" in result

    async def test_parsed_is_parsed_log(self):
        from app.models.intermediate import ParsedLog
        from app.workflows.incident_response_flow import log_parser_node

        result = await log_parser_node({"raw_log": "ERROR: connection refused"})
        assert isinstance(result["parsed"], ParsedLog)

    async def test_force_fail_raises(self):
        from app.workflows.incident_response_flow import log_parser_node

        with pytest.raises(RuntimeError, match="forced log_parser failure"):
            await log_parser_node({"raw_log": "x", "force_fail": "log_parser"})


class TestMetricsAnalyzerNode:
    async def test_returns_metrics_key(self):
        from app.workflows.incident_response_flow import metrics_analyzer_node

        state = {"parsed": _make_parsed_log(), "alerts": ["5xx spike"], "deploy_context": {}}
        result = await metrics_analyzer_node(state)
        assert "metrics" in result

    async def test_metrics_is_metrics_summary(self):
        from app.models.incident import MetricsSummary
        from app.workflows.incident_response_flow import metrics_analyzer_node

        state = {"parsed": _make_parsed_log(), "alerts": ["spike"], "deploy_context": {}}
        result = await metrics_analyzer_node(state)
        assert isinstance(result["metrics"], MetricsSummary)

    async def test_force_fail_raises(self):
        from app.workflows.incident_response_flow import metrics_analyzer_node

        state = {"parsed": _make_parsed_log(), "force_fail": "metrics_analyzer"}
        with pytest.raises(RuntimeError, match="forced metrics_analyzer failure"):
            await metrics_analyzer_node(state)


class TestChangeImpactNode:
    async def test_returns_impact_key(self):
        from app.workflows.incident_response_flow import change_impact_node

        state = {"parsed": _make_parsed_log(), "deploy_context": _make_deploy_context()}
        result = await change_impact_node(state)
        assert "impact" in result

    async def test_impact_is_change_impact(self):
        from app.models.incident import ChangeImpact
        from app.workflows.incident_response_flow import change_impact_node

        state = {"parsed": _make_parsed_log(), "deploy_context": _make_deploy_context()}
        result = await change_impact_node(state)
        assert isinstance(result["impact"], ChangeImpact)

    async def test_force_fail_raises(self):
        from app.workflows.incident_response_flow import change_impact_node

        state = {"deploy_context": {}, "force_fail": "change_impact"}
        with pytest.raises(RuntimeError, match="forced change_impact failure"):
            await change_impact_node(state)


class TestEvidenceGathererNode:
    async def test_returns_evidence_key(self):
        from app.workflows.incident_response_flow import evidence_gatherer_node

        state = {
            "parsed": _make_parsed_log(),
            "metrics": _make_metrics_summary(),
            "impact": _make_change_impact(),
        }
        result = await evidence_gatherer_node(state)
        assert "evidence" in result

    async def test_evidence_is_evidence_bundle(self):
        from app.models.intermediate import EvidenceBundle
        from app.workflows.incident_response_flow import evidence_gatherer_node

        state = {
            "parsed": _make_parsed_log(),
            "metrics": _make_metrics_summary(),
            "impact": _make_change_impact(),
        }
        result = await evidence_gatherer_node(state)
        assert isinstance(result["evidence"], EvidenceBundle)

    async def test_force_fail_raises(self):
        from app.workflows.incident_response_flow import evidence_gatherer_node

        state = {
            "parsed": _make_parsed_log(),
            "metrics": _make_metrics_summary(),
            "impact": _make_change_impact(),
            "force_fail": "evidence_gatherer",
        }
        with pytest.raises(RuntimeError, match="forced evidence_gatherer failure"):
            await evidence_gatherer_node(state)


class TestCoordinatorNode:
    async def test_returns_report_key(self):
        from app.workflows.incident_response_flow import coordinator_node

        state = {
            "metrics": _make_metrics_summary(),
            "impact": _make_change_impact(),
            "evidence": _make_evidence_bundle(),
        }
        result = await coordinator_node(state)
        assert "report" in result

    async def test_report_is_incident_report(self):
        from app.models.incident import IncidentReport
        from app.workflows.incident_response_flow import coordinator_node

        state = {
            "metrics": _make_metrics_summary(),
            "impact": _make_change_impact(),
            "evidence": _make_evidence_bundle(),
        }
        result = await coordinator_node(state)
        assert isinstance(result["report"], IncidentReport)

    async def test_force_fail_raises(self):
        from app.workflows.incident_response_flow import coordinator_node

        state = {
            "metrics": _make_metrics_summary(),
            "impact": _make_change_impact(),
            "evidence": _make_evidence_bundle(),
            "force_fail": "coordinator",
        }
        with pytest.raises(RuntimeError, match="forced coordinator failure"):
            await coordinator_node(state)


class TestRunIncidentResponse:
    async def test_returns_dict(self):
        from app.workflows.incident_response_flow import run_incident_response

        result = await run_incident_response(_make_incident_inputs())
        assert isinstance(result, dict)

    async def test_result_has_report(self):
        from app.models.incident import IncidentReport
        from app.workflows.incident_response_flow import run_incident_response

        result = await run_incident_response(_make_incident_inputs())
        assert "report" in result
        assert isinstance(result["report"], IncidentReport)

    async def test_result_has_parsed(self):
        from app.models.intermediate import ParsedLog
        from app.workflows.incident_response_flow import run_incident_response

        result = await run_incident_response(_make_incident_inputs())
        assert "parsed" in result
        assert isinstance(result["parsed"], ParsedLog)

    async def test_result_has_metrics(self):
        from app.models.incident import MetricsSummary
        from app.workflows.incident_response_flow import run_incident_response

        result = await run_incident_response(_make_incident_inputs())
        assert "metrics" in result
        assert isinstance(result["metrics"], MetricsSummary)

    async def test_result_has_impact(self):
        from app.models.incident import ChangeImpact
        from app.workflows.incident_response_flow import run_incident_response

        result = await run_incident_response(_make_incident_inputs())
        assert "impact" in result
        assert isinstance(result["impact"], ChangeImpact)

    async def test_result_has_evidence(self):
        from app.models.intermediate import EvidenceBundle
        from app.workflows.incident_response_flow import run_incident_response

        result = await run_incident_response(_make_incident_inputs())
        assert "evidence" in result
        assert isinstance(result["evidence"], EvidenceBundle)

    async def test_report_fields_not_empty(self):
        from app.workflows.incident_response_flow import run_incident_response

        result = await run_incident_response(_make_incident_inputs())
        report = result["report"]
        assert report.root_cause.strip() != ""
        assert len(report.evidence) >= 1
        assert len(report.remediation) >= 1
        assert len(report.rollback) >= 1

    async def test_not_degraded_on_success(self):
        from app.workflows.incident_response_flow import run_incident_response

        result = await run_incident_response(_make_incident_inputs())
        assert result.get("degraded") is False
        assert result.get("errors") == []

    async def test_preserves_raw_log(self):
        from app.workflows.incident_response_flow import run_incident_response

        inputs = _make_incident_inputs()
        result = await run_incident_response(inputs)
        assert result.get("raw_log") == inputs["log_content"]


class TestIncidentResponseStability:
    async def test_force_fail_returns_degraded(self):
        from app.workflows.incident_response_flow import run_incident_response

        result = await run_incident_response(
            {**_make_incident_inputs(), "force_fail": "log_parser"}
        )
        assert result["degraded"] is True
        assert len(result["errors"]) > 0

    async def test_force_fail_error_has_node_info(self):
        from app.workflows.incident_response_flow import run_incident_response

        result = await run_incident_response(
            {**_make_incident_inputs(), "force_fail": "log_parser"}
        )
        err = result["errors"][0]
        assert "node" in err
        assert "message" in err

    async def test_circuit_breaker_open_returns_degraded(self):
        from app.workflows.incident_response_flow import run_incident_response

        result = await run_incident_response({**_make_incident_inputs(), "simulate_breaker": True})
        assert result["degraded"] is True
        assert any(e.get("error_type") == "dependency" for e in result["errors"])

    async def test_retry_summary_present(self):
        from app.workflows.incident_response_flow import run_incident_response

        result = await run_incident_response(_make_incident_inputs())
        assert "retry_summary" in result


class TestIncidentResponseExports:
    def test_run_incident_response_importable_from_workflows(self):
        from app.workflows import run_incident_response
        from app.workflows.incident_response_flow import run_incident_response as direct

        assert run_incident_response is direct

    def test_build_incident_response_graph_importable_from_workflows(self):
        from app.workflows import build_incident_response_graph
        from app.workflows.incident_response_flow import (
            build_incident_response_graph as direct,
        )

        assert build_incident_response_graph is direct


def _make_parsed_log():
    from app.models.intermediate import ParsedLog

    return ParsedLog(
        source="build",
        error_signatures=["connection refused"],
        stack_fragments=["redis.py:42"],
        environment={"repository": "test-repo"},
    )


def _make_metrics_summary():
    from app.models.incident import MetricsSummary

    return MetricsSummary(
        error_rate=0.25,
        latency_p99_ms=800.0,
        anomalies=["5xx spike"],
    )


def _make_change_impact():
    from app.models.incident import ChangeImpact

    return ChangeImpact(
        files_changed=["src/redis.py"],
        risk_level="high",
        summary="Modified Redis connection handling",
    )


def _make_evidence_bundle():
    from app.models.intermediate import EvidenceBundle

    return EvidenceBundle(
        citations=["https://docs.example.com/redis"],
        snippets=["Redis connection timeout fix"],
        relevance_scores=[0.85],
    )


def _make_deploy_context():
    return {
        "deploy_id": "deploy-42",
        "files_changed": ["src/redis.py", "src/config.py"],
        "commit_message": "update redis pool settings",
    }


def _make_incident_inputs():
    return {
        "log_content": "ERROR: connection refused at redis.py:42",
        "alerts": ["5xx spike", "latency threshold breach"],
        "deploy_context": {
            "deploy_id": "deploy-42",
            "files_changed": ["src/redis.py"],
            "commit_message": "update redis pool",
            "error_rate": 0.25,
            "latency_p99_ms": 800.0,
        },
    }
