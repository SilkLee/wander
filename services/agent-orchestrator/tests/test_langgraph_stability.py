import asyncio
import importlib.util
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import cast


def load_run_langgraph() -> Callable[
    [dict[str, object]], Coroutine[object, object, dict[str, object]]
]:
    module_path = Path(__file__).resolve().parents[1] / "app" / "workflows" / "langgraph_flow.py"
    import sys
    import types

    if "app.agents" not in sys.modules:
        fake_agents = types.ModuleType("app.agents")
        setattr(fake_agents, "__path__", [])
        fake_roles = types.ModuleType("app.agents.roles")
        fake_review_roles = types.ModuleType("app.agents.review_roles")
        fake_incident_roles = types.ModuleType("app.agents.incident_roles")

        async def parse_log(inputs: dict[str, object]) -> object:
            return types.SimpleNamespace(error_signatures=["x"])

        async def diagnose(parsed: object) -> object:
            return types.SimpleNamespace(confidence=0.5)

        async def retrieve_evidence(diagnosis: object) -> object:
            return types.SimpleNamespace()

        async def remediate(diagnosis: object, evidence: object) -> object:
            return types.SimpleNamespace()

        async def diff_parser(inputs: dict[str, object]) -> object:
            return types.SimpleNamespace(diff_summary="ok")

        async def risk_analyst(inputs: dict[str, object]) -> object:
            return types.SimpleNamespace(risk_score=0.1)

        async def summarizer(inputs: dict[str, object]) -> object:
            return types.SimpleNamespace(summary="ok")

        async def reviewer(inputs: dict[str, object]) -> object:
            return types.SimpleNamespace(summary="ok")

        async def metrics_analyzer(inputs: dict[str, object]) -> object:
            return types.SimpleNamespace(error_rate=0.0, latency_p99_ms=0.0, anomalies=[])

        async def change_impact(inputs: dict[str, object]) -> object:
            return types.SimpleNamespace(files_changed=[], risk_level="low", summary="ok")

        async def coordinator(inputs: dict[str, object]) -> object:
            return types.SimpleNamespace(
                root_cause="ok",
                evidence=["ok"],
                remediation=["ok"],
                rollback=["ok"],
            )

        setattr(fake_roles, "parse_log", parse_log)
        setattr(fake_roles, "diagnose", diagnose)
        setattr(fake_roles, "retrieve_evidence", retrieve_evidence)
        setattr(fake_roles, "remediate", remediate)
        setattr(fake_review_roles, "diff_parser", diff_parser)
        setattr(fake_review_roles, "reviewer", reviewer)
        setattr(fake_review_roles, "risk_analyst", risk_analyst)
        setattr(fake_review_roles, "summarizer", summarizer)
        setattr(fake_incident_roles, "metrics_analyzer", metrics_analyzer)
        setattr(fake_incident_roles, "change_impact", change_impact)
        setattr(fake_incident_roles, "coordinator", coordinator)
        setattr(fake_agents, "roles", fake_roles)
        sys.modules["app.agents"] = fake_agents
        sys.modules["app.agents.roles"] = fake_roles
        sys.modules["app.agents.review_roles"] = fake_review_roles
        sys.modules["app.agents.incident_roles"] = fake_incident_roles
    module_name = "langgraph_flow_module"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load langgraph flow module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return cast(
        Callable[[dict[str, object]], Coroutine[object, object, dict[str, object]]],
        module.run_langgraph,
    )


def test_langgraph_returns_errors_on_failure():
    run_langgraph = load_run_langgraph()
    result = asyncio.run(run_langgraph({"log_content": "err", "force_fail": "diagnose"}))
    assert "errors" in result
    assert result["errors"], "Expected error metadata"
