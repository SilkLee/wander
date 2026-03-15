from __future__ import annotations

import httpx
import pytest


@pytest.mark.asyncio
async def test_record_deployment_and_query_dora(metrics_url: str):
    """End-to-end: record a deployment event, then verify DORA metrics include it."""
    async with httpx.AsyncClient() as client:
        # Record a deployment
        resp = await client.post(
            f"{metrics_url}/metrics/events/deployment",
            json={
                "repo": "e2e-test",
                "sha": "e2e-abc123",
                "deployed_at": "2026-03-15T10:00:00Z",
                "success": True,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "created"

        # Query DORA metrics
        resp = await client.get(
            f"{metrics_url}/metrics/dora", params={"repo": "e2e-test"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "deployment_frequency" in data
        assert "lead_time" in data


@pytest.mark.asyncio
async def test_record_incident_and_verify_in_events(metrics_url: str):
    """End-to-end: record an incident, then list events and verify it appears."""
    async with httpx.AsyncClient() as client:
        # Record an incident
        resp = await client.post(
            f"{metrics_url}/metrics/events/incident",
            json={
                "repo": "e2e-test",
                "detected_at": "2026-03-15T10:00:00Z",
                "resolved_at": "2026-03-15T13:00:00Z",
                "severity": "critical",
            },
        )
        assert resp.status_code == 200
        event_id = resp.json()["id"]

        # List incident events
        resp = await client.get(
            f"{metrics_url}/metrics/events",
            params={"type": "incident", "repo": "e2e-test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        incident_ids = [e["id"] for e in data["events"]]
        assert event_id in incident_ids
