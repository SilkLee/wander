from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dora_default_returns_200(client: AsyncClient):
    resp = await client.get("/metrics/dora")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_dora_response_has_required_fields(client: AsyncClient):
    resp = await client.get("/metrics/dora")
    data = resp.json()
    for field in ("deployment_frequency", "lead_time", "change_failure_rate", "mttr", "trend"):
        assert field in data, f"Missing field: {field}"


@pytest.mark.asyncio
async def test_dora_with_repo_param(client: AsyncClient):
    resp = await client.get("/metrics/dora", params={"repo": "default"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["deployment_frequency"] > 0


@pytest.mark.asyncio
async def test_dora_with_date_range(client: AsyncClient):
    resp = await client.get(
        "/metrics/dora",
        params={"from": "2026-01-01T00:00:00Z", "to": "2026-03-15T23:59:59Z"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_dora_values_are_numeric(client: AsyncClient):
    resp = await client.get("/metrics/dora")
    data = resp.json()
    for field in ("deployment_frequency", "lead_time", "change_failure_rate", "mttr"):
        assert isinstance(data[field], (int, float)), f"{field} is not numeric: {type(data[field])}"


@pytest.mark.asyncio
async def test_dora_trend_is_list_of_points(client: AsyncClient):
    resp = await client.get("/metrics/dora")
    data = resp.json()
    trend = data["trend"]
    assert isinstance(trend, list)
    assert len(trend) > 0
    for point in trend:
        for key in ("timestamp", "deployment_frequency", "lead_time", "change_failure_rate", "mttr"):
            assert key in point, f"Trend point missing key: {key}"
