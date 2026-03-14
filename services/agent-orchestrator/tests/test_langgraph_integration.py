"""Integration tests for LangGraph wiring into the log analysis workflow.

Tests cover:
- LanggraphPort protocol conformance
- AnalysisResult dataclass behavior
- AnalyzeLogUseCase with and without langgraph
- analyze-log endpoint intermediate_summary enrichment
- Dependency injection wiring
"""

from typing import Any, Dict, Optional

import pytest
from unittest.mock import AsyncMock

from app.application.ports import AgentPort, LanggraphPort, ParserPort
from app.application.use_cases.analyze_log import AnalysisResult, AnalyzeLogUseCase
from app.domain.models.confidence import Confidence
from app.domain.models.log_analysis import LogAnalysis
from app.domain.models.root_cause import RootCause
from app.domain.models.severity import Severity
from app.infrastructure.events import MemoryEventBus
from app.infrastructure.repositories.memory_analysis_repo import MemoryAnalysisRepository
from app.models.intermediate import Diagnosis, EvidenceBundle, ParsedLog, Remediation
from app.models.requests import LogAnalysisRequest


def _fake_agent_result() -> Dict[str, Any]:
    return {
        "root_cause": "Connection timeout to database",
        "severity": "high",
        "suggested_fixes": ["Increase connection pool size"],
        "references": [],
        "confidence": 0.85,
        "summary": "DB connection timeout",
    }


def _fake_langgraph_result() -> Dict[str, Any]:
    return {
        "raw_log": "ERROR: connection refused at db:5432",
        "parsed": ParsedLog(
            source="build",
            error_signatures=["connection refused at db:5432"],
            stack_fragments=[],
            environment={"repository": ""},
        ),
        "diagnosis": Diagnosis(
            root_cause_candidates=["connection refused at db:5432"],
            confidence=0.6,
            reasoning="Stub diagnosis based on error signatures",
        ),
        "evidence": EvidenceBundle(
            citations=["https://docs.example.com/stub"],
            snippets=["Stub evidence for: connection refused at db:5432"],
            relevance_scores=[0.5],
        ),
        "remediation": Remediation(
            steps=["Review error: connection refused at db:5432"],
            risk_notes=["Stub remediation - verify before applying"],
            verification_commands=["echo stub-verification"],
        ),
    }


def _make_mock_agent(result: Optional[Dict[str, Any]] = None) -> AgentPort:
    agent = AsyncMock(spec=AgentPort)
    agent.analyze_logs.return_value = result or _fake_agent_result()
    return agent


def _make_mock_parser() -> ParserPort:
    parser = AsyncMock(spec=ParserPort)
    parser.parse_analysis_result.return_value = (
        Severity.HIGH,
        Confidence(score=0.85),
        [
            RootCause(
                description="Connection timeout",
                component="database",
                remediation="Increase pool size",
            )
        ],
    )
    return parser


def _make_mock_langgraph(result: Optional[Dict[str, Any]] = None) -> LanggraphPort:
    lg = AsyncMock(spec=LanggraphPort)
    lg.run.return_value = result or _fake_langgraph_result()
    return lg


def _mock_optional_deps():
    import sys
    from unittest.mock import MagicMock

    sys.modules.setdefault("redis", MagicMock())
    sys.modules.setdefault("redis.asyncio", MagicMock())
    sys.modules.setdefault("redis.exceptions", MagicMock())
    sys.modules.setdefault("elasticsearch", MagicMock())
    sys.modules.setdefault("langchain", MagicMock())
    sys.modules.setdefault("langchain.tools", MagicMock())
    sys.modules.setdefault("langchain_community", MagicMock())
    sys.modules.setdefault("langchain_openai", MagicMock())


class TestLanggraphPortProtocol:
    def test_importable_from_ports(self):
        from app.application.ports import LanggraphPort

        assert hasattr(LanggraphPort, "run")

    def test_protocol_has_run_method(self):
        import inspect

        members = dict(inspect.getmembers(LanggraphPort))
        assert "run" in members


class TestAnalysisResult:
    def test_importable(self):
        from app.application.use_cases.analyze_log import AnalysisResult

        assert AnalysisResult is not None

    def test_has_analysis_field(self):
        analysis = LogAnalysis(
            log_content="test",
            severity=Severity.LOW,
            confidence=Confidence(score=0.5),
            root_causes=[RootCause(description="x", component="y", remediation="z")],
        )
        result = AnalysisResult(analysis=analysis)
        assert result.analysis is analysis

    def test_langgraph_result_defaults_to_none(self):
        analysis = LogAnalysis(
            log_content="test",
            severity=Severity.LOW,
            confidence=Confidence(score=0.5),
            root_causes=[RootCause(description="x", component="y", remediation="z")],
        )
        result = AnalysisResult(analysis=analysis)
        assert result.langgraph_result is None

    def test_langgraph_result_populated(self):
        analysis = LogAnalysis(
            log_content="test",
            severity=Severity.LOW,
            confidence=Confidence(score=0.5),
            root_causes=[RootCause(description="x", component="y", remediation="z")],
        )
        lg_result = _fake_langgraph_result()
        result = AnalysisResult(analysis=analysis, langgraph_result=lg_result)
        assert result.langgraph_result is lg_result
        assert "parsed" in result.langgraph_result
        assert "diagnosis" in result.langgraph_result


class TestAnalyzeLogEndpointIntermediateSummary:
    async def test_intermediate_summary_contains_langgraph_fields(self):
        _mock_optional_deps()
        from app.api.workflows import analyze_log

        agent = _make_mock_agent()
        parser = _make_mock_parser()
        repo = MemoryAnalysisRepository()
        bus = MemoryEventBus()
        lg = _make_mock_langgraph()

        use_case = AnalyzeLogUseCase(
            agent=agent, parser=parser, repository=repo, event_bus=bus, langgraph=lg
        )

        request = LogAnalysisRequest(log_content="ERROR: connection refused at db:5432")
        response = await analyze_log(request, use_case)

        assert "parsed" in response.intermediate_summary
        assert "diagnosis" in response.intermediate_summary
        assert "evidence" in response.intermediate_summary
        assert "remediation" in response.intermediate_summary


class TestBackwardCompatibility:
    async def test_execute_without_langgraph(self):
        agent = _make_mock_agent()
        parser = _make_mock_parser()
        repo = MemoryAnalysisRepository()
        bus = MemoryEventBus()

        uc = AnalyzeLogUseCase(agent=agent, parser=parser, repository=repo, event_bus=bus)
        result = await uc.execute("ERROR: connection refused at db:5432")

        assert result.langgraph_result is None
        assert isinstance(result.analysis, LogAnalysis)


# ---------------------------------------------------------------------------
# AnalyzeLogUseCase accepts optional langgraph port
# ---------------------------------------------------------------------------


class TestUseCaseAcceptsLanggraphPort:
    """AnalyzeLogUseCase constructor accepts optional langgraph parameter."""

    @pytest.mark.asyncio
    async def test_constructor_accepts_langgraph_kwarg(self):
        agent = _make_mock_agent()
        parser = _make_mock_parser()
        repo = MemoryAnalysisRepository()
        bus = MemoryEventBus()
        lg = _make_mock_langgraph()

        uc = AnalyzeLogUseCase(
            agent=agent,
            parser=parser,
            repository=repo,
            event_bus=bus,
            langgraph=lg,
        )
        assert uc.langgraph is lg

    @pytest.mark.asyncio
    async def test_constructor_langgraph_defaults_to_none(self):
        agent = _make_mock_agent()
        parser = _make_mock_parser()
        repo = MemoryAnalysisRepository()
        bus = MemoryEventBus()

        uc = AnalyzeLogUseCase(
            agent=agent,
            parser=parser,
            repository=repo,
            event_bus=bus,
        )
        assert uc.langgraph is None


# ---------------------------------------------------------------------------
# AnalyzeLogUseCase.execute returns AnalysisResult
# ---------------------------------------------------------------------------


class TestUseCaseExecuteReturnsAnalysisResult:
    """execute() returns AnalysisResult with analysis and langgraph_result."""

    async def test_returns_analysis_result_type(self):
        uc = AnalyzeLogUseCase(
            agent=_make_mock_agent(),
            parser=_make_mock_parser(),
            repository=MemoryAnalysisRepository(),
            event_bus=MemoryEventBus(),
            langgraph=_make_mock_langgraph(),
        )
        result = await uc.execute("ERROR: connection refused at db:5432")
        assert isinstance(result, AnalysisResult)

    async def test_result_contains_analysis(self):
        uc = AnalyzeLogUseCase(
            agent=_make_mock_agent(),
            parser=_make_mock_parser(),
            repository=MemoryAnalysisRepository(),
            event_bus=MemoryEventBus(),
            langgraph=_make_mock_langgraph(),
        )
        result = await uc.execute("ERROR: connection refused at db:5432")
        assert isinstance(result.analysis, LogAnalysis)
        assert result.analysis.severity == Severity.HIGH

    async def test_result_contains_langgraph_result(self):
        uc = AnalyzeLogUseCase(
            agent=_make_mock_agent(),
            parser=_make_mock_parser(),
            repository=MemoryAnalysisRepository(),
            event_bus=MemoryEventBus(),
            langgraph=_make_mock_langgraph(),
        )
        result = await uc.execute("ERROR: connection refused at db:5432")
        assert result.langgraph_result is not None
        assert "parsed" in result.langgraph_result
        assert "diagnosis" in result.langgraph_result

    async def test_langgraph_called_with_log_content(self):
        lg = _make_mock_langgraph()
        uc = AnalyzeLogUseCase(
            agent=_make_mock_agent(),
            parser=_make_mock_parser(),
            repository=MemoryAnalysisRepository(),
            event_bus=MemoryEventBus(),
            langgraph=lg,
        )
        await uc.execute("ERROR: connection refused at db:5432")
        lg.run.assert_awaited_once_with({"log_content": "ERROR: connection refused at db:5432"})

    async def test_langgraph_failure_does_not_break_analysis(self):
        lg = _make_mock_langgraph()
        lg.run.side_effect = RuntimeError("langgraph down")
        uc = AnalyzeLogUseCase(
            agent=_make_mock_agent(),
            parser=_make_mock_parser(),
            repository=MemoryAnalysisRepository(),
            event_bus=MemoryEventBus(),
            langgraph=lg,
        )
        result = await uc.execute("ERROR: connection refused at db:5432")
        assert isinstance(result, AnalysisResult)
        assert result.langgraph_result is None


# ---------------------------------------------------------------------------
# Backward compatibility: use case without langgraph
# ---------------------------------------------------------------------------


class TestUseCaseWithoutLanggraph:
    """execute() still works when langgraph is not provided."""

    async def test_returns_analysis_result_with_none_langgraph(self):
        uc = AnalyzeLogUseCase(
            agent=_make_mock_agent(),
            parser=_make_mock_parser(),
            repository=MemoryAnalysisRepository(),
            event_bus=MemoryEventBus(),
        )
        result = await uc.execute("ERROR: something failed")
        assert isinstance(result, AnalysisResult)
        assert result.langgraph_result is None
        assert isinstance(result.analysis, LogAnalysis)


# ---------------------------------------------------------------------------
# Endpoint: intermediate_summary includes langgraph data
# ---------------------------------------------------------------------------


def _endpoint_test_with_langgraph(check_fn):
    """Helper: POST to analyze-log with mock use case returning langgraph data."""
    _mock_optional_deps()
    from fastapi.testclient import TestClient
    from app.main import app
    from app.dependencies import get_analyze_log_use_case

    analysis = LogAnalysis(
        log_content="ERROR: connection refused",
        severity=Severity.HIGH,
        confidence=Confidence(score=0.85),
        root_causes=[
            RootCause(
                description="Connection timeout",
                component="database",
                remediation="Increase pool size",
            )
        ],
        summary="DB connection timeout",
    )
    lg_result = _fake_langgraph_result()
    result = AnalysisResult(analysis=analysis, langgraph_result=lg_result)

    mock_uc = AsyncMock(spec=AnalyzeLogUseCase)
    mock_uc.execute.return_value = result
    app.dependency_overrides[get_analyze_log_use_case] = lambda: mock_uc

    try:
        client = TestClient(app, raise_server_exceptions=False)
        resp = client.post(
            "/workflows/analyze-log",
            json={"log_content": "ERROR: connection refused at db:5432"},
        )
        check_fn(resp)
    finally:
        app.dependency_overrides.clear()


class TestEndpointIntermediateSummary:
    """analyze-log endpoint enriches intermediate_summary with langgraph data."""

    def test_endpoint_returns_200(self):
        def check(resp):
            assert resp.status_code == 200

        _endpoint_test_with_langgraph(check)

    def test_intermediate_summary_has_diagnosis_confidence(self):
        def check(resp):
            data = resp.json()
            assert "diagnosis_confidence" in data["intermediate_summary"]
            assert data["intermediate_summary"]["diagnosis_confidence"] == 0.6

        _endpoint_test_with_langgraph(check)

    def test_intermediate_summary_has_parsed_source(self):
        def check(resp):
            data = resp.json()
            assert data["intermediate_summary"]["parsed_source"] == "build"

        _endpoint_test_with_langgraph(check)

    def test_intermediate_summary_has_error_signatures(self):
        def check(resp):
            data = resp.json()
            assert "error_signatures" in data["intermediate_summary"]
            assert (
                "connection refused at db:5432" in data["intermediate_summary"]["error_signatures"]
            )

        _endpoint_test_with_langgraph(check)

    def test_intermediate_summary_has_remediation_steps(self):
        def check(resp):
            data = resp.json()
            assert "remediation_steps" in data["intermediate_summary"]
            assert len(data["intermediate_summary"]["remediation_steps"]) > 0

        _endpoint_test_with_langgraph(check)

    def test_intermediate_summary_has_evidence_citations(self):
        def check(resp):
            data = resp.json()
            assert "evidence_citations" in data["intermediate_summary"]
            assert (
                "https://docs.example.com/stub"
                in data["intermediate_summary"]["evidence_citations"]
            )

        _endpoint_test_with_langgraph(check)


# ---------------------------------------------------------------------------
# Endpoint: without langgraph (backward compat)
# ---------------------------------------------------------------------------


class TestEndpointWithoutLanggraph:
    """Endpoint still works when langgraph_result is None."""

    def test_intermediate_summary_still_has_base_fields(self):
        _mock_optional_deps()
        from fastapi.testclient import TestClient
        from app.main import app
        from app.dependencies import get_analyze_log_use_case

        analysis = LogAnalysis(
            log_content="ERROR: something",
            severity=Severity.HIGH,
            confidence=Confidence(score=0.85),
            root_causes=[RootCause(description="x", component="y", remediation="z")],
        )
        result = AnalysisResult(analysis=analysis, langgraph_result=None)
        mock_uc = AsyncMock(spec=AnalyzeLogUseCase)
        mock_uc.execute.return_value = result

        app.dependency_overrides[get_analyze_log_use_case] = lambda: mock_uc

        try:
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.post(
                "/workflows/analyze-log",
                json={"log_content": "ERROR: something"},
            )
            data = resp.json()
            summary = data["intermediate_summary"]
            assert "severity" in summary
            assert "confidence_score" in summary
            assert "root_cause_count" in summary
            assert "is_actionable" in summary
            assert "is_critical" in summary
            # langgraph-specific keys should NOT be present
            assert "diagnosis_confidence" not in summary
        finally:
            app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# DI: get_langgraph returns adapter
# ---------------------------------------------------------------------------


class TestDependencyInjection:
    """Dependency injection wiring for langgraph port."""

    def test_get_langgraph_returns_adapter(self):
        from app.dependencies import get_langgraph

        adapter = get_langgraph()
        assert hasattr(adapter, "run")
