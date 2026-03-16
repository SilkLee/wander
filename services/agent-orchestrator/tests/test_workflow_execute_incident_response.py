from __future__ import annotations

from typing import cast
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

class TestWorkflowExecutionRequestSchemaIncidentResponse:
    def test_incident_response_type_accepted(self):
        from app.models.requests import WorkflowExecutionRequest

        req = WorkflowExecutionRequest(
            workflow_type="incident_response",
            inputs={"log_content": "ERROR: connection refused at redis.py:42"},
        )
        assert req.workflow_type == "incident_response"


class TestExecuteIncidentResponse:
    def _mock_result(self) -> dict[str, object]:
        return {
            "raw_log": "ERROR: connection refused at redis.py:42",
            "alerts": ["5xx spike"],
            "deploy_context": {},
            "parsed": {"source": "build", "error_signatures": ["connection refused"]},
            "metrics": {"error_rate": 0.25, "latency_p99_ms": 800.0, "anomalies": []},
            "impact": {"files_changed": [], "risk_level": "high", "summary": "Redis issue"},
            "evidence": {"citations": [], "snippets": [], "relevance_scores": []},
            "report": {
                "root_cause": "connection refused",
                "evidence": ["redis timeout"],
                "remediation": ["restart redis"],
                "rollback": ["revert deploy"],
            },
            "errors": [],
            "retry_summary": {"incident_response": 0},
            "degraded": False,
        }

    def test_incident_response_returns_200(self):
        with patch(
            "app.api.workflows.run_incident_response",
            new_callable=AsyncMock,
            return_value=self._mock_result(),
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "incident_response",
                    "inputs": {"log_content": "ERROR: connection refused at redis.py:42"},
                },
            )
        assert response.status_code == 200

    def test_incident_response_returns_completed_status(self):
        with patch(
            "app.api.workflows.run_incident_response",
            new_callable=AsyncMock,
            return_value=self._mock_result(),
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "incident_response",
                    "inputs": {"log_content": "ERROR: connection refused at redis.py:42"},
                },
            )
        data = cast(dict[str, object], response.json())
        assert data["status"] == "completed"

    def test_incident_response_returns_execution_id(self):
        with patch(
            "app.api.workflows.run_incident_response",
            new_callable=AsyncMock,
            return_value=self._mock_result(),
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "incident_response",
                    "inputs": {"log_content": "ERROR: connection refused at redis.py:42"},
                },
            )
        data = cast(dict[str, object], response.json())
        assert "execution_id" in data
        execution_id = data["execution_id"]
        assert isinstance(execution_id, str)
        assert len(execution_id) > 0

    def test_incident_response_returns_outputs(self):
        with patch(
            "app.api.workflows.run_incident_response",
            new_callable=AsyncMock,
            return_value=self._mock_result(),
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "incident_response",
                    "inputs": {"log_content": "ERROR: connection refused at redis.py:42"},
                },
            )
        data = cast(dict[str, object], response.json())
        assert "outputs" in data
        assert isinstance(data["outputs"], dict)

    def test_incident_response_returns_execution_time(self):
        with patch(
            "app.api.workflows.run_incident_response",
            new_callable=AsyncMock,
            return_value=self._mock_result(),
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "incident_response",
                    "inputs": {"log_content": "ERROR: connection refused at redis.py:42"},
                },
            )
        data = cast(dict[str, object], response.json())
        assert "execution_time" in data
        execution_time = data["execution_time"]
        assert isinstance(execution_time, (int, float))
        assert execution_time >= 0

    def test_incident_response_calls_run_incident_response_with_inputs(self):
        mock_fn = AsyncMock(return_value=self._mock_result())
        with patch("app.api.workflows.run_incident_response", mock_fn):
            _ = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "incident_response",
                    "inputs": {
                        "log_content": "ERROR: connection refused at redis.py:42",
                        "alerts": ["5xx spike"],
                    },
                },
            )
        mock_fn.assert_called_once_with(
            {
                "log_content": "ERROR: connection refused at redis.py:42",
                "alerts": ["5xx spike"],
            }
        )

    def test_incident_response_failure_returns_failed_status(self):
        mock_fn = AsyncMock(side_effect=RuntimeError("incident flow exploded"))
        with patch("app.api.workflows.run_incident_response", mock_fn):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "incident_response",
                    "inputs": {"log_content": "ERROR: connection refused"},
                },
            )
        data = cast(dict[str, object], response.json())
        assert data["status"] == "failed"
        error = data["error"]
        assert isinstance(error, str)
        assert "incident flow exploded" in error

    def test_incident_response_missing_log_content_returns_failed(self):
        mock_fn = AsyncMock(side_effect=ValueError("Missing required input: log_content"))
        with patch("app.api.workflows.run_incident_response", mock_fn):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "incident_response",
                    "inputs": {},
                },
            )
        data = cast(dict[str, object], response.json())
        assert data["status"] == "failed"

    def test_incident_response_outputs_contain_report(self):
        with patch(
            "app.api.workflows.run_incident_response",
            new_callable=AsyncMock,
            return_value=self._mock_result(),
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "incident_response",
                    "inputs": {"log_content": "ERROR: connection refused"},
                },
            )
        data = cast(dict[str, object], response.json())
        outputs = data["outputs"]
        assert isinstance(outputs, dict)
        assert "report" in outputs


class TestWorkflowTypesIncludesIncidentResponse:
    def test_incident_response_listed(self):
        response = client.get("/workflows/types")
        data = cast(dict[str, object], response.json())
        workflows = data["workflows"]
        assert isinstance(workflows, list)
        workflow_items = cast(list[dict[str, object]], workflows)
        types = {workflow_item["type"]: workflow_item for workflow_item in workflow_items}
        assert "incident_response" in types

    def test_incident_response_status_available(self):
        response = client.get("/workflows/types")
        data = cast(dict[str, object], response.json())
        workflows = data["workflows"]
        assert isinstance(workflows, list)
        workflow_items = cast(list[dict[str, object]], workflows)
        types = {workflow_item["type"]: workflow_item for workflow_item in workflow_items}
        assert types["incident_response"]["status"] == "available"

    def test_incident_response_has_expected_inputs(self):
        response = client.get("/workflows/types")
        data = cast(dict[str, object], response.json())
        workflows = data["workflows"]
        assert isinstance(workflows, list)
        workflow_items = cast(list[dict[str, object]], workflows)
        types = {workflow_item["type"]: workflow_item for workflow_item in workflow_items}
        ir_type = types["incident_response"]
        inputs = ir_type["inputs"]
        assert isinstance(inputs, list)
        assert "log_content" in inputs
        assert "alerts" in inputs
        assert "deploy_context" in inputs

    def test_incident_response_has_name_and_description(self):
        response = client.get("/workflows/types")
        data = cast(dict[str, object], response.json())
        workflows = data["workflows"]
        assert isinstance(workflows, list)
        workflow_items = cast(list[dict[str, object]], workflows)
        types = {workflow_item["type"]: workflow_item for workflow_item in workflow_items}
        ir_type = types["incident_response"]
        assert ir_type["name"] != ""
        assert ir_type["description"] != ""


class TestExistingWorkflowsNotBrokenByIncidentResponse:
    def test_unknown_type_still_returns_400(self):
        response = client.post(
            "/workflows/execute",
            json={
                "workflow_type": "nonexistent",
                "inputs": {},
            },
        )
        assert response.status_code == 400

    def test_log_analysis_still_dispatches(self):
        mock_fn = AsyncMock(return_value={"root_cause": "OOM", "severity": "high"})
        with patch(
            "app.api.workflows._execute_log_analysis_workflow",
            mock_fn,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "log_analysis",
                    "inputs": {"log_content": "error OOM"},
                },
            )
        assert response.status_code == 200
        data = cast(dict[str, object], response.json())
        assert data["status"] == "completed"

    def test_pr_risk_still_dispatches(self):
        mock_fn = AsyncMock(
            return_value={
                "diff": "diff --git a/x b/x",
                "errors": [],
                "retry_summary": {"pr_risk": 0},
                "degraded": False,
            }
        )
        with patch("app.api.workflows.run_pr_risk", mock_fn):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "pr_risk",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        assert response.status_code == 200
        data = cast(dict[str, object], response.json())
        assert data["status"] == "completed"

    def test_code_review_still_dispatches(self):
        mock_fn = AsyncMock(
            return_value={
                "diff": "diff --git a/x b/x",
                "errors": [],
                "retry_summary": {"code_review": 0},
                "degraded": False,
            }
        )
        with patch("app.api.workflows.run_code_review", mock_fn):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "code_review",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        assert response.status_code == 200
        data = cast(dict[str, object], response.json())
        assert data["status"] == "completed"

    def test_langchain_tool_agent_still_dispatches(self):
        mock_fn = AsyncMock(
            return_value={
                "analysis": "ok",
                "outputs": {"tool_outputs": []},
                "intermediate_summary": {
                    "errors": [],
                    "retry_summary": {"langchain_tool_agent": 0},
                    "degraded": False,
                },
            }
        )
        with patch("app.api.workflows.run_tool_agent", mock_fn):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "langchain_tool_agent",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        assert response.status_code == 200
        data = cast(dict[str, object], response.json())
        assert data["status"] == "completed"
