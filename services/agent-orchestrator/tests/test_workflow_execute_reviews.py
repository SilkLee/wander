"""Tests for /workflows/execute dispatch to pr_risk and code_review flows.

Covers:
- pr_risk workflow_type dispatches to run_pr_risk and returns WorkflowExecutionResponse
- code_review workflow_type dispatches to run_code_review and returns WorkflowExecutionResponse
- Both return status=completed on success
- Both return status=failed with error on flow failure
- Unknown workflow_type returns 400
- Missing required inputs returns appropriate error
- Request schema accepts pr_risk and code_review workflow_types
"""

from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------


class TestWorkflowExecutionRequestSchema:
    """WorkflowExecutionRequest accepts pr_risk and code_review types."""

    def test_pr_risk_type_accepted(self):
        from app.models.requests import WorkflowExecutionRequest

        req = WorkflowExecutionRequest(
            workflow_type="pr_risk",
            inputs={"diff": "diff --git a/x b/x"},
        )
        assert req.workflow_type == "pr_risk"

    def test_code_review_type_accepted(self):
        from app.models.requests import WorkflowExecutionRequest

        req = WorkflowExecutionRequest(
            workflow_type="code_review",
            inputs={"diff": "diff --git a/x b/x"},
        )
        assert req.workflow_type == "code_review"

    def test_log_analysis_type_still_accepted(self):
        from app.models.requests import WorkflowExecutionRequest

        req = WorkflowExecutionRequest(
            workflow_type="log_analysis",
            inputs={"log_content": "error"},
        )
        assert req.workflow_type == "log_analysis"


# ---------------------------------------------------------------------------
# PR Risk via /workflows/execute
# ---------------------------------------------------------------------------


class TestExecutePRRisk:
    """POST /workflows/execute with workflow_type=pr_risk dispatches to run_pr_risk."""

    def test_pr_risk_returns_200(self):
        mock_result = {
            "diff": "diff --git a/x b/x",
            "report": {"risk_level": "low", "risk_factors": [], "recommendations": []},
            "summary": {"verdict": "approve", "key_findings": [], "recommendation": "ok"},
            "analysis": "parsed diff",
            "errors": [],
            "retry_summary": {"pr_risk": 0},
            "degraded": False,
        }
        with patch(
            "app.api.workflows.run_pr_risk",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "pr_risk",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        assert response.status_code == 200

    def test_pr_risk_returns_completed_status(self):
        mock_result = {
            "diff": "diff --git a/x b/x",
            "report": {"risk_level": "low", "risk_factors": [], "recommendations": []},
            "summary": {"verdict": "approve", "key_findings": [], "recommendation": "ok"},
            "analysis": "parsed diff",
            "errors": [],
            "retry_summary": {"pr_risk": 0},
            "degraded": False,
        }
        with patch(
            "app.api.workflows.run_pr_risk",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "pr_risk",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert data["status"] == "completed"

    def test_pr_risk_returns_execution_id(self):
        mock_result = {
            "diff": "diff --git a/x b/x",
            "errors": [],
            "retry_summary": {"pr_risk": 0},
            "degraded": False,
        }
        with patch(
            "app.api.workflows.run_pr_risk",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "pr_risk",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert "execution_id" in data
        assert len(data["execution_id"]) > 0

    def test_pr_risk_returns_outputs(self):
        mock_result = {
            "diff": "diff --git a/x b/x",
            "report": {"risk_level": "low", "risk_factors": [], "recommendations": []},
            "errors": [],
            "retry_summary": {"pr_risk": 0},
            "degraded": False,
        }
        with patch(
            "app.api.workflows.run_pr_risk",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "pr_risk",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert "outputs" in data
        assert isinstance(data["outputs"], dict)

    def test_pr_risk_returns_execution_time(self):
        mock_result = {
            "diff": "diff --git a/x b/x",
            "errors": [],
            "retry_summary": {"pr_risk": 0},
            "degraded": False,
        }
        with patch(
            "app.api.workflows.run_pr_risk",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "pr_risk",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert "execution_time" in data
        assert data["execution_time"] >= 0

    def test_pr_risk_calls_run_pr_risk_with_inputs(self):
        mock_fn = AsyncMock(
            return_value={
                "diff": "diff --git a/x b/x",
                "errors": [],
                "retry_summary": {},
                "degraded": False,
            }
        )
        with patch("app.api.workflows.run_pr_risk", mock_fn):
            client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "pr_risk",
                    "inputs": {"diff": "diff --git a/x b/x", "context": {"repo": "test"}},
                },
            )
        mock_fn.assert_called_once_with({"diff": "diff --git a/x b/x", "context": {"repo": "test"}})

    def test_pr_risk_failure_returns_failed_status(self):
        mock_fn = AsyncMock(side_effect=RuntimeError("flow exploded"))
        with patch("app.api.workflows.run_pr_risk", mock_fn):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "pr_risk",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert data["status"] == "failed"
        assert "flow exploded" in data["error"]

    def test_pr_risk_missing_diff_returns_failed(self):
        """Missing diff input causes flow to fail gracefully."""
        mock_fn = AsyncMock(side_effect=ValueError("Missing required input: diff"))
        with patch("app.api.workflows.run_pr_risk", mock_fn):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "pr_risk",
                    "inputs": {},
                },
            )
        data = response.json()
        assert data["status"] == "failed"


# ---------------------------------------------------------------------------
# Code Review via /workflows/execute
# ---------------------------------------------------------------------------


class TestExecuteCodeReview:
    """POST /workflows/execute with workflow_type=code_review dispatches to run_code_review."""

    def test_code_review_returns_200(self):
        mock_result = {
            "diff": "diff --git a/x b/x",
            "comments": [],
            "summary": {"verdict": "approve", "key_findings": [], "recommendation": "ok"},
            "analysis": "parsed diff",
            "errors": [],
            "retry_summary": {"code_review": 0},
            "degraded": False,
        }
        with patch(
            "app.api.workflows.run_code_review",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "code_review",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        assert response.status_code == 200

    def test_code_review_returns_completed_status(self):
        mock_result = {
            "diff": "diff --git a/x b/x",
            "comments": [],
            "summary": {"verdict": "approve", "key_findings": [], "recommendation": "ok"},
            "analysis": "parsed diff",
            "errors": [],
            "retry_summary": {"code_review": 0},
            "degraded": False,
        }
        with patch(
            "app.api.workflows.run_code_review",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "code_review",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert data["status"] == "completed"

    def test_code_review_returns_execution_id(self):
        mock_result = {
            "diff": "diff --git a/x b/x",
            "errors": [],
            "retry_summary": {"code_review": 0},
            "degraded": False,
        }
        with patch(
            "app.api.workflows.run_code_review",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "code_review",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert "execution_id" in data
        assert len(data["execution_id"]) > 0

    def test_code_review_returns_outputs(self):
        mock_result = {
            "diff": "diff --git a/x b/x",
            "comments": [],
            "errors": [],
            "retry_summary": {"code_review": 0},
            "degraded": False,
        }
        with patch(
            "app.api.workflows.run_code_review",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "code_review",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert "outputs" in data
        assert isinstance(data["outputs"], dict)

    def test_code_review_calls_run_code_review_with_inputs(self):
        mock_fn = AsyncMock(
            return_value={
                "diff": "diff --git a/x b/x",
                "errors": [],
                "retry_summary": {},
                "degraded": False,
            }
        )
        with patch("app.api.workflows.run_code_review", mock_fn):
            client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "code_review",
                    "inputs": {"diff": "diff --git a/x b/x", "context": {"repo": "test"}},
                },
            )
        mock_fn.assert_called_once_with({"diff": "diff --git a/x b/x", "context": {"repo": "test"}})

    def test_code_review_failure_returns_failed_status(self):
        mock_fn = AsyncMock(side_effect=RuntimeError("review exploded"))
        with patch("app.api.workflows.run_code_review", mock_fn):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "code_review",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        data = response.json()
        assert data["status"] == "failed"
        assert "review exploded" in data["error"]

    def test_code_review_no_longer_returns_501(self):
        """code_review was previously 501 NOT_IMPLEMENTED; now it should work."""
        mock_result = {
            "diff": "diff --git a/x b/x",
            "errors": [],
            "retry_summary": {"code_review": 0},
            "degraded": False,
        }
        with patch(
            "app.api.workflows.run_code_review",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            response = client.post(
                "/workflows/execute",
                json={
                    "workflow_type": "code_review",
                    "inputs": {"diff": "diff --git a/x b/x"},
                },
            )
        assert response.status_code != 501


# ---------------------------------------------------------------------------
# Existing behavior preserved
# ---------------------------------------------------------------------------


class TestExecuteWorkflowExisting:
    """Existing workflow_type=log_analysis and unknown types still work."""

    def test_unknown_type_returns_400(self):
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


# ---------------------------------------------------------------------------
# /workflows/types includes new workflows
# ---------------------------------------------------------------------------


class TestWorkflowTypesEndpoint:
    """GET /workflows/types reflects available status for new workflows."""

    def test_pr_risk_listed(self):
        response = client.get("/workflows/types")
        data = response.json()
        types = {w["type"]: w for w in data["workflows"]}
        assert "pr_risk" in types

    def test_pr_risk_status_available(self):
        response = client.get("/workflows/types")
        data = response.json()
        types = {w["type"]: w for w in data["workflows"]}
        assert types["pr_risk"]["status"] == "available"

    def test_code_review_listed(self):
        response = client.get("/workflows/types")
        data = response.json()
        types = {w["type"]: w for w in data["workflows"]}
        assert "code_review" in types

    def test_code_review_status_available(self):
        response = client.get("/workflows/types")
        data = response.json()
        types = {w["type"]: w for w in data["workflows"]}
        assert types["code_review"]["status"] == "available"
