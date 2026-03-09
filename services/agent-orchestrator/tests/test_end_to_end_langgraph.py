import json
from pathlib import Path

from app.workflows.langgraph_flow import run_langgraph


class TestEndToEndLanggraph:
    async def test_end_to_end_with_payload(self):
        repo_root = Path(__file__).resolve().parents[3]
        payload_path = repo_root / "test-payload.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))

        result = await run_langgraph(payload)

        assert result["diagnosis"].root_cause_candidates
