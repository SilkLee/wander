from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_returns_200(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_health_response_shape(client: AsyncClient):
    resp = await client.get("/health")
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "metrics"
