"""Unit tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from app.main import app

client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns service info."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "agent-orchestrator"
    assert data["status"] == "running"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_endpoint_success():
    """Test health endpoint when all services are healthy."""
    with patch("redis.asyncio.Redis.from_url") as mock_redis, \
         patch("elasticsearch.AsyncElasticsearch") as mock_es:
        
        # Mock Redis
        mock_redis_instance = AsyncMock()
        mock_redis_instance.ping = AsyncMock(return_value=True)
        mock_redis.return_value = mock_redis_instance
        
        # Mock Elasticsearch
        mock_es_instance = AsyncMock()
        mock_es_instance.info = AsyncMock(return_value={"cluster_name": "test"})
        mock_es.return_value = mock_es_instance
        
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["redis_connected"] is True
        assert data["elasticsearch_connected"] is True


def test_ready_endpoint():
    """Test readiness probe endpoint."""
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True


def test_live_endpoint():
    """Test liveness probe endpoint."""
    response = client.get("/live")
    assert response.status_code == 200
    data = response.json()
    assert data["alive"] is True
