from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.dora import DORAResponse


@pytest.mark.asyncio
async def test_dora_endpoint_returns_metrics(client: AsyncClient):
    resp = await client.get("/metrics/dora")
    assert resp.status_code == 200
    data = resp.json()

    assert "deployment_frequency" in data
    assert "lead_time" in data
    assert "change_failure_rate" in data
    assert "mttr" in data
    assert "trend" in data

    parsed = DORAResponse(**data)
    assert parsed.deployment_frequency > 0
    assert parsed.trend
