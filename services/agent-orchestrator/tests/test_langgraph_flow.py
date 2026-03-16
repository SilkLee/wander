"""Tests for LangGraph triage workflow and agent roles.

Covers: AgentRole enum, build_triage_graph compilation, run_langgraph execution,
TriageState schema, node functions, edge routing, and package exports.
"""

from typing import Dict

from app.agents.roles import AgentRole
from app.workflows.langgraph_flow import (
    TriageState,
    build_langgraph_flow,
    build_triage_graph,
    run_langgraph,
    parse_log_node,
    diagnose_node,
    gather_evidence_node,
    remediate_node,
    severity_router,
)


# ---------------------------------------------------------------------------
# AgentRole enum
# ---------------------------------------------------------------------------


class TestAgentRole:
    """AgentRole enum values and membership."""

    def test_has_parser_role(self):
        assert AgentRole.PARSER.value == "parser"

    def test_has_diagnostician_role(self):
        assert AgentRole.DIAGNOSTICIAN.value == "diagnostician"

    def test_has_retriever_role(self):
        assert AgentRole.RETRIEVER.value == "retriever"

    def test_has_remediator_role(self):
        assert AgentRole.REMEDIATOR.value == "remediator"

    def test_exactly_four_members(self):
        assert len(AgentRole) == 4

    def test_all_values_are_strings(self):
        for role in AgentRole:
            assert isinstance(role.value, str)

# ---------------------------------------------------------------------------
# build_triage_graph
# ---------------------------------------------------------------------------


class TestBuildTriageGraph:
    """build_triage_graph returns a compiled LangGraph."""

    def test_returns_compiled_graph(self):
        from langgraph.graph.state import CompiledStateGraph

        graph = build_triage_graph()
        assert isinstance(graph, CompiledStateGraph)


class TestBuildLanggraphFlow:
    def test_build_flow_returns_dict(self):
        flow = build_langgraph_flow()
        assert isinstance(flow, dict)
        assert "parse_log" in flow
        assert "diagnose" in flow
        assert "retrieve_evidence" in flow
        assert "remediate" in flow

    def test_graph_has_expected_nodes(self):
        graph = build_triage_graph()
        node_names = set(graph.nodes.keys())
        assert "parse_log" in node_names
        assert "diagnose" in node_names
        assert "gather_evidence" in node_names
        assert "remediate" in node_names

    def test_graph_is_deterministic(self):
        """Building twice yields equivalent graphs."""
        g1 = build_triage_graph()
        g2 = build_triage_graph()
        assert set(g1.nodes.keys()) == set(g2.nodes.keys())


# ---------------------------------------------------------------------------
# TriageState schema
# ---------------------------------------------------------------------------


class TestTriageState:
    """TriageState TypedDict shape."""

    def test_has_raw_log_key(self):
        assert "raw_log" in TriageState.__annotations__

    def test_has_parsed_key(self):
        assert "parsed" in TriageState.__annotations__

    def test_has_diagnosis_key(self):
        assert "diagnosis" in TriageState.__annotations__

    def test_has_evidence_key(self):
        assert "evidence" in TriageState.__annotations__

    def test_has_remediation_key(self):
        assert "remediation" in TriageState.__annotations__

# ---------------------------------------------------------------------------
# Individual node functions (stub behaviour - no LLM)
# ---------------------------------------------------------------------------


class TestParseLogNode:
    """parse_log_node returns a dict with parsed key containing a ParsedLog."""

    async def test_returns_parsed_key(self):
        from app.models.intermediate import ParsedLog

        state: Dict = {"raw_log": "ERROR: connection refused at db:5432"}
        result = await parse_log_node(state)
        assert "parsed" in result
        assert isinstance(result["parsed"], ParsedLog)

    async def test_parsed_has_source(self):
        state: Dict = {"raw_log": "some log"}
        result = await parse_log_node(state)
        assert result["parsed"].source != ""


class TestDiagnoseNode:
    """diagnose_node returns a dict with diagnosis key containing a Diagnosis."""

    async def test_returns_diagnosis_key(self):
        from app.models.intermediate import Diagnosis, ParsedLog

        state: Dict = {
            "raw_log": "ERROR: timeout",
            "parsed": ParsedLog(
                source="ci",
                error_signatures=["timeout"],
                stack_fragments=[],
                environment={},
            ),
        }
        result = await diagnose_node(state)
        assert "diagnosis" in result
        assert isinstance(result["diagnosis"], Diagnosis)

    async def test_diagnosis_confidence_in_range(self):
        from app.models.intermediate import ParsedLog

        state: Dict = {
            "raw_log": "FATAL: OOM killed",
            "parsed": ParsedLog(
                source="runtime",
                error_signatures=["OOM"],
                stack_fragments=["main.py:1"],
                environment={"node": "w1"},
            ),
        }
        result = await diagnose_node(state)
        assert 0.0 <= result["diagnosis"].confidence <= 1.0


class TestGatherEvidenceNode:
    """gather_evidence_node returns a dict with evidence key."""

    async def test_returns_evidence_key(self):
        from app.models.intermediate import Diagnosis, EvidenceBundle, ParsedLog

        state: Dict = {
            "raw_log": "log",
            "parsed": ParsedLog(
                source="ci",
                error_signatures=["err"],
                stack_fragments=[],
                environment={},
            ),
            "diagnosis": Diagnosis(
                root_cause_candidates=["network"],
                confidence=0.8,
                reasoning="timeout pattern",
            ),
        }
        result = await gather_evidence_node(state)
        assert "evidence" in result
        assert isinstance(result["evidence"], EvidenceBundle)

class TestRemediateNode:
    """remediate_node returns a dict with remediation key."""

    async def test_returns_remediation_key(self):
        from app.models.intermediate import (
            Diagnosis,
            EvidenceBundle,
            ParsedLog,
            Remediation,
        )

        state: Dict = {
            "raw_log": "log",
            "parsed": ParsedLog(
                source="ci",
                error_signatures=["err"],
                stack_fragments=[],
                environment={},
            ),
            "diagnosis": Diagnosis(
                root_cause_candidates=["network"],
                confidence=0.8,
                reasoning="timeout pattern",
            ),
            "evidence": EvidenceBundle(
                citations=["https://docs.example.com"],
                snippets=["relevant snippet"],
                relevance_scores=[0.9],
            ),
        }
        result = await remediate_node(state)
        assert "remediation" in result
        assert isinstance(result["remediation"], Remediation)


# ---------------------------------------------------------------------------
# severity_router
# ---------------------------------------------------------------------------


class TestSeverityRouter:
    """severity_router returns correct edge based on diagnosis confidence."""

    async def test_high_confidence_routes_to_gather(self):
        from app.models.intermediate import Diagnosis, ParsedLog

        state: Dict = {
            "raw_log": "log",
            "parsed": ParsedLog(
                source="ci",
                error_signatures=["err"],
                stack_fragments=[],
                environment={},
            ),
            "diagnosis": Diagnosis(
                root_cause_candidates=["known cause"],
                confidence=0.8,
                reasoning="clear pattern",
            ),
        }
        result = await severity_router(state)
        assert result == "gather_evidence"

    async def test_low_confidence_routes_to_gather(self):
        """Even low confidence proceeds to evidence gathering."""
        from app.models.intermediate import Diagnosis, ParsedLog

        state: Dict = {
            "raw_log": "log",
            "parsed": ParsedLog(
                source="ci",
                error_signatures=["err"],
                stack_fragments=[],
                environment={},
            ),
            "diagnosis": Diagnosis(
                root_cause_candidates=["maybe this"],
                confidence=0.3,
                reasoning="uncertain",
            ),
        }
        result = await severity_router(state)
        assert result == "gather_evidence"

# ---------------------------------------------------------------------------
# run_langgraph (end-to-end, no LLM)
# ---------------------------------------------------------------------------


class TestRunLanggraph:
    """run_langgraph orchestrates the full pipeline and returns intermediate DTOs."""

    async def test_returns_dict(self):
        result = await run_langgraph({"log_content": "ERROR: connection refused at db:5432"})
        assert isinstance(result, dict)

    async def test_result_has_parsed(self):
        from app.models.intermediate import ParsedLog

        result = await run_langgraph({"log_content": "ERROR: OOM killed"})
        assert "parsed" in result
        assert isinstance(result["parsed"], ParsedLog)

    async def test_result_has_diagnosis(self):
        from app.models.intermediate import Diagnosis

        result = await run_langgraph({"log_content": "FATAL: segfault in worker"})
        assert "diagnosis" in result
        assert isinstance(result["diagnosis"], Diagnosis)

    async def test_result_has_evidence(self):
        from app.models.intermediate import EvidenceBundle

        result = await run_langgraph({"log_content": "ERROR: timeout expired"})
        assert "evidence" in result
        assert isinstance(result["evidence"], EvidenceBundle)

    async def test_result_has_remediation(self):
        from app.models.intermediate import Remediation

        result = await run_langgraph({"log_content": "ERROR: disk full"})
        assert "remediation" in result
        assert isinstance(result["remediation"], Remediation)

    async def test_result_has_raw_log(self):
        raw = "ERROR: something went wrong"
        result = await run_langgraph({"log_content": raw})
        assert result["raw_log"] == raw


# ---------------------------------------------------------------------------
# Package-level exports
# ---------------------------------------------------------------------------


class TestPackageExports:
    """Verify new symbols are exported from their packages."""

    def test_agent_role_importable_from_agents(self):
        from app.agents import AgentRole as AR

        assert AR is AgentRole

    def test_build_triage_graph_importable_from_workflows(self):
        from app.workflows import build_triage_graph as btg

        assert btg is build_triage_graph

    def test_build_langgraph_flow_importable_from_workflows(self):
        from app.workflows import build_langgraph_flow as blf

        assert blf is build_langgraph_flow

    def test_run_langgraph_importable_from_workflows(self):
        from app.workflows import run_langgraph as rl

        assert rl is run_langgraph
