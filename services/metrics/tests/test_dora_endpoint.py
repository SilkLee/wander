from httpx import ASGITransport, AsyncClient
import pytest
import pytest_asyncio

from app.main import app
from app.models.dora import DORAResponse


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_dora_endpoint_returns_metrics(client: AsyncClient):
    resp = await client.get("/metrics/dora")
    assert resp.status_code == 200
    data = resp.json()

    assert "deployment_frequency" in data
    assert "lead_time_hours" in data
    assert "change_failure_rate" in data
    assert "mttr_hours" in data
    assert "trend" in data

    parsed = DORAResponse(**data)
    assert parsed.deployment_frequency > 0
    assert parsed.trend in ("improving", "stable", "declining")
