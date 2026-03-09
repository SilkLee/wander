import asyncio
import importlib.util
from pathlib import Path


def load_run_langgraph():
    module_path = Path(__file__).resolve().parents[1] / "app" / "workflows" / "langgraph_flow.py"
    import sys
    import types
    if "app.agents" not in sys.modules:
        fake_agents = types.ModuleType("app.agents")
        fake_roles = types.ModuleType("app.agents.roles")
        async def parse_log(inputs):
            return types.SimpleNamespace(error_signatures=["x"])
        async def diagnose(parsed):
            return types.SimpleNamespace(confidence=0.5)
        async def retrieve_evidence(diagnosis):
            return types.SimpleNamespace()
        async def remediate(diagnosis, evidence):
            return types.SimpleNamespace()
        fake_roles.parse_log = parse_log
        fake_roles.diagnose = diagnose
        fake_roles.retrieve_evidence = retrieve_evidence
        fake_roles.remediate = remediate
        fake_agents.roles = fake_roles
        sys.modules["app.agents"] = fake_agents
        sys.modules["app.agents.roles"] = fake_roles
    module_name = "langgraph_flow_module"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load langgraph flow module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module.run_langgraph


def test_langgraph_returns_errors_on_failure():
    run_langgraph = load_run_langgraph()
    result = asyncio.get_event_loop().run_until_complete(
        run_langgraph({"log_content": "err", "force_fail": "diagnose"})
    )
    assert "errors" in result
    assert result["errors"], "Expected error metadata"
