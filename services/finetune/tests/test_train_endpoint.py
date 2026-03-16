"""Tests for the finetune service /train endpoint."""

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


class TestTrainEndpointSuccess:
    """POST /train should accept a dataset path and return a run_id."""

    def test_train_returns_200(self):
        """POST /train with valid payload should return 200."""
        response = client.post("/train", json={"dataset_path": "data/train.jsonl"})
        assert response.status_code == 200

    def test_train_returns_run_id(self):
        """POST /train response must contain a non-empty run_id string."""
        response = client.post("/train", json={"dataset_path": "data/train.jsonl"})
        data = response.json()
        assert "run_id" in data
        assert isinstance(data["run_id"], str)
        assert len(data["run_id"]) > 0

    def test_train_run_id_is_unique(self):
        """Each POST /train call should produce a distinct run_id."""
        r1 = client.post("/train", json={"dataset_path": "data/train.jsonl"})
        r2 = client.post("/train", json={"dataset_path": "data/train.jsonl"})
        assert r1.json()["run_id"] != r2.json()["run_id"]


class TestTrainEndpointValidation:
    """POST /train should reject invalid payloads."""

    def test_train_requires_dataset_path(self):
        """POST /train without dataset_path should return 422."""
        response = client.post("/train", json={})
        assert response.status_code == 422

    def test_train_rejects_empty_dataset_path(self):
        """POST /train with empty dataset_path should return 422."""
        response = client.post("/train", json={"dataset_path": ""})
        assert response.status_code == 422
