"""Tests for /workflows/execute dispatch to langchain_tool_agent workflow.

Covers:
- langchain_tool_agent workflow_type dispatches to run_tool_agent and returns WorkflowExecutionResponse
- Returns status=completed on success
- Returns status=failed with error on agent failure
- Returns execution_id, outputs, execution_time
- Calls run_tool_agent with correct inputs
- /workflows/types includes langchain_tool_agent with status=available
- Request schema accepts langchain_tool_agent workflow_type
"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------


class TestWorkflowExecutionRequestSchemaLangchainAgent:
    """WorkflowExecutionRequest accepts langchain_tool_agent type."""

    def test_langchain_tool_agent_type_accepted(self):
        from app.models.requests import WorkflowExecutionRequest

        req = WorkflowExecutionRequest(
            workflow_type="langchain_tool_agent",
            inputs={"diff": "diff --git a/x b/x"},
        )
        assert req.workflow_type == "langchain_tool_agent"


# ---------------------------------------------------------------------------
# langchain_tool_agent via /workflows/execute
# ---------------------------------------------------------------------------


class TestExecuteLangchainToolAgent:
    """POST /workflows/execute with workflow_type=langchain_tool_agent dispatches to run_tool_agent."""

    def test_langchain_tool_agent_returns_200(self):
        mock_result = {
            "analysis": "Root cause: missing dependency",
            "outputs": {
                "pr_summary": {"summary": "ok", "key_risks": [], "actions": []},
                "risk_findings": [],
                "dependency_risks": [],
                "impact_report": {"services": [], "modules": [], "notes": ""},
                "tool_outputs": [],
            },
            "intermediate_summary": {
                "errors": [],
                "retry_summary": {"langchain_tool_agent": 0},
                "degraded": False,
            },
        }
        with patch(
            "app.api.workflows.run_tool_agent",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "langchain_tool_agent",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        assert response.status_code == 200

    def test_langchain_tool_agent_returns_completed_status(self):
        mock_result = {
            "analysis": "Root cause: missing dependency",
            "outputs": {
                "pr_summary": {"summary": "ok", "key_risks": [], "actions": []},
                "risk_findings": [],
                "dependency_risks": [],
                "impact_report": {"services": [], "modules": [], "notes": ""},
                "tool_outputs": [],
            },
            "intermediate_summary": {
                "errors": [],
                "retry_summary": {"langchain_tool_agent": 0},
                "degraded": False,
            },
        }
        with patch(
            "app.api.workflows.run_tool_agent",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "langchain_tool_agent",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert data["status"] == "completed"

    def test_langchain_tool_agent_returns_execution_id(self):
        mock_result = {
            "analysis": "ok",
            "outputs": {"tool_outputs": []},
            "intermediate_summary": {
                "errors": [],
                "retry_summary": {"langchain_tool_agent": 0},
                "degraded": False,
            },
        }
        with patch(
            "app.api.workflows.run_tool_agent",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "langchain_tool_agent",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert "execution_id" in data
        assert len(data["execution_id"]) > 0

    def test_langchain_tool_agent_returns_outputs(self):
        mock_result = {
            "analysis": "Root cause found",
            "outputs": {
                "pr_summary": {"summary": "ok", "key_risks": [], "actions": []},
                "risk_findings": [],
                "dependency_risks": [],
                "impact_report": {"services": [], "modules": [], "notes": ""},
                "tool_outputs": [{"tool": "repo_search", "result": "found: auth.py"}],
            },
            "intermediate_summary": {
                "errors": [],
                "retry_summary": {"langchain_tool_agent": 0},
                "degraded": False,
            },
        }
        with patch(
            "app.api.workflows.run_tool_agent",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "langchain_tool_agent",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert "outputs" in data
        assert isinstance(data["outputs"], dict)

    def test_langchain_tool_agent_returns_execution_time(self):
        mock_result = {
            "analysis": "ok",
            "outputs": {"tool_outputs": []},
            "intermediate_summary": {
                "errors": [],
                "retry_summary": {"langchain_tool_agent": 0},
                "degraded": False,
            },
        }
        with patch(
            "app.api.workflows.run_tool_agent",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "langchain_tool_agent",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert "execution_time" in data
        assert data["execution_time"] >= 0

    def test_langchain_tool_agent_calls_run_tool_agent_with_inputs(self):
        mock_fn = AsyncMock(
            return_value={
                "analysis": "ok",
                "outputs": {"tool_outputs": []},
                "intermediate_summary": {
                    "errors": [],
                    "retry_summary": {},
                    "degraded": False,
                },
            }
        )
        with patch("app.api.workflows.run_tool_agent", mock_fn):
            client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "langchain_tool_agent",
                    "inputs": {"diff": "diff --git a/x b/x", "context": {"repo": "test"}},
                },
            )
        mock_fn.assert_called_once_with({"diff": "diff --git a/x b/x", "context": {"repo": "test"}})

    def test_langchain_tool_agent_failure_returns_failed_status(self):
        mock_fn = AsyncMock(side_effect=RuntimeError("agent exploded"))
        with patch("app.api.workflows.run_tool_agent", mock_fn):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "langchain_tool_agent",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert data["status"] == "failed"
        assert "agent exploded" in data["error"]

    def test_langchain_tool_agent_missing_diff_returns_failed(self):
        """Missing diff input causes agent to fail gracefully."""
        mock_fn = AsyncMock(side_effect=ValueError("Missing required input: diff"))
        with patch("app.api.workflows.run_tool_agent", mock_fn):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "langchain_tool_agent",
                    "inputs": {},
                },
            )
        data = response.json()
        assert data["status"] == "failed"


# ---------------------------------------------------------------------------
# /workflows/types includes langchain_tool_agent
# ---------------------------------------------------------------------------


class TestWorkflowTypesIncludesLangchainAgent:
    """GET /workflows/types reflects langchain_tool_agent with available status."""

    def test_langchain_tool_agent_listed(self):
        response = client.get("/workflows/types")
        data = response.json()
        types = {w["type"]: w for w in data["workflows"]}
        assert "langchain_tool_agent" in types

    def test_langchain_tool_agent_status_available(self):
        response = client.get("/workflows/types")
        data = response.json()
        types = {w["type"]: w for w in data["workflows"]}
        assert types["langchain_tool_agent"]["status"] == "available"

    def test_langchain_tool_agent_has_expected_inputs(self):
        response = client.get("/workflows/types")
        data = response.json()
        types = {w["type"]: w for w in data["workflows"]}
        agent_type = types["langchain_tool_agent"]
        assert "diff" in agent_type["inputs"]
        assert "context" in agent_type["inputs"]


# ---------------------------------------------------------------------------
# Existing behavior preserved
# ---------------------------------------------------------------------------


class TestExistingWorkflowsNotBroken:
    """Existing workflow types still work after adding langchain_tool_agent."""

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
        """log_analysis workflow still works (no regression)."""
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
        data = response.json()
        assert data["status"] == "completed"

    def test_pr_risk_still_dispatches(self):
        """pr_risk workflow still works (no regression)."""
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
        data = response.json()
        assert data["status"] == "completed"

    def test_code_review_still_dispatches(self):
        """code_review workflow still works (no regression)."""
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
        data = response.json()
        assert data["status"] == "completed"
