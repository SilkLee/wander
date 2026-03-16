"""Tests for POST /classify/risk endpoint."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# Stub heavy dependencies so tests run without torch/transformers installed
_stubs = {}
for mod_name in (
    "torch",
    "transformers",
    "accelerate",
    "sentencepiece",
):
    if mod_name not in sys.modules:
        _stubs[mod_name] = sys.modules[mod_name] = MagicMock()

# Patch get_inference_service before importing app.main to skip model loading
with patch("app.services.inference.get_inference_service", return_value=MagicMock()):
    from fastapi.testclient import TestClient
    from app.main import app


@pytest.fixture
def client():
    """Create a FastAPI test client with model loading mocked out."""
    with patch("app.main.get_inference_service"):
        with TestClient(app) as c:
            yield c


def test_classify_risk_returns_label_and_score(client):
    """POST /classify/risk returns a label in {low, medium, high} and a float score."""
    response = client.post("/classify/risk", json={"input": "diff --git a/foo.py"})
    assert response.status_code == 200
    body = response.json()
    assert body["label"] in {"low", "medium", "high"}
    assert isinstance(body["score"], float)
    assert 0.0 <= body["score"] <= 1.0


def test_classify_risk_rejects_missing_input(client):
    """POST /classify/risk returns 422 when input field is missing."""
    response = client.post("/classify/risk", json={})
    assert response.status_code == 422


def test_classify_risk_rejects_empty_input(client):
    """POST /classify/risk returns 422 when input is empty string."""
    response = client.post("/classify/risk", json={"input": ""})
    assert response.status_code == 422
