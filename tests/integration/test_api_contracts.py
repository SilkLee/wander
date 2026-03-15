from __future__ import annotations

import httpx
import pytest


@pytest.mark.asyncio
async def test_gateway_health_contract(api_gateway_url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_gateway_url}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_metrics_health_contract(metrics_url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{metrics_url}/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "metrics"


@pytest.mark.asyncio
async def test_orchestrator_health_contract(agent_orchestrator_url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{agent_orchestrator_url}/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_gateway_root_contract(api_gateway_url: str):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_gateway_url}/")
    assert resp.status_code == 200
    data = resp.json()
    assert "service" in data
    assert "version" in data
