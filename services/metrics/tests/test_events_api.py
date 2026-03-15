from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_record_deployment_event(client: AsyncClient):
    resp = await client.post(
        "/metrics/events/deployment",
        json={
            "repo": "test-repo",
            "sha": "abc123",
            "deployed_at": "2026-03-15T10:00:00Z",
            "success": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["status"] == "created"


@pytest.mark.asyncio
async def test_record_change_event(client: AsyncClient):
    resp = await client.post(
        "/metrics/events/change",
        json={
            "repo": "test-repo",
            "sha": "def456",
            "first_commit_at": "2026-03-15T08:00:00Z",
            "merged_at": "2026-03-15T09:00:00Z",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["status"] == "created"


@pytest.mark.asyncio
async def test_record_incident_event(client: AsyncClient):
    resp = await client.post(
        "/metrics/events/incident",
        json={
            "repo": "test-repo",
            "detected_at": "2026-03-15T10:00:00Z",
            "resolved_at": "2026-03-15T13:00:00Z",
            "severity": "high",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["status"] == "created"


@pytest.mark.asyncio
async def test_list_events_default(client: AsyncClient):
    # First record an event so there's data
    await client.post(
        "/metrics/events/deployment",
        json={
            "repo": "default",
            "sha": "list-test-001",
            "deployed_at": "2026-03-14T12:00:00Z",
            "success": True,
        },
    )
    resp = await client.get("/metrics/events")
    assert resp.status_code == 200
    data = resp.json()
    assert "events" in data
    assert "total" in data
    assert isinstance(data["events"], list)
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_events_with_type_filter(client: AsyncClient):
    # Record a deployment first
    await client.post(
        "/metrics/events/deployment",
        json={
            "repo": "default",
            "sha": "filter-test-001",
            "deployed_at": "2026-03-14T12:00:00Z",
            "success": True,
        },
    )
    resp = await client.get("/metrics/events", params={"type": "deployment"})
    assert resp.status_code == 200
    data = resp.json()
    assert all(e["type"] == "deployment" for e in data["events"])
