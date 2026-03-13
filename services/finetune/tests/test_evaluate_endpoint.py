"""Tests for the finetune service /evaluate endpoint."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestEvaluateEndpointSuccess:
    """POST /evaluate should accept a run_id and return metrics."""

    def test_evaluate_returns_200(self):
        """POST /evaluate with valid payload should return 200."""
        response = client.post("/evaluate", json={"run_id": "abc-123"})
        assert response.status_code == 200

    def test_evaluate_returns_metrics(self):
        """POST /evaluate response must contain a metrics dict."""
        response = client.post("/evaluate", json={"run_id": "abc-123"})
        data = response.json()
        assert "metrics" in data
        assert isinstance(data["metrics"], dict)

    def test_evaluate_metrics_contain_macro_f1(self):
        """Metrics dict must include macro_f1 as a float."""
        response = client.post("/evaluate", json={"run_id": "abc-123"})
        metrics = response.json()["metrics"]
        assert "macro_f1" in metrics
        assert isinstance(metrics["macro_f1"], float)

    def test_evaluate_metrics_contain_high_risk_recall(self):
        """Metrics dict must include high_risk_recall as a float."""
        response = client.post("/evaluate", json={"run_id": "abc-123"})
        metrics = response.json()["metrics"]
        assert "high_risk_recall" in metrics
        assert isinstance(metrics["high_risk_recall"], float)


class TestEvaluateEndpointValidation:
    """POST /evaluate should reject invalid payloads."""

    def test_evaluate_requires_run_id(self):
        """POST /evaluate without run_id should return 422."""
        response = client.post("/evaluate", json={})
        assert response.status_code == 422

    def test_evaluate_rejects_empty_run_id(self):
        """POST /evaluate with empty run_id should return 422."""
        response = client.post("/evaluate", json={"run_id": ""})
        assert response.status_code == 422
