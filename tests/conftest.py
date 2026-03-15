from __future__ import annotations

import pytest
import pytest_asyncio
import httpx


def _check_service(url: str) -> bool:
    """Synchronously check if a service is reachable."""
    try:
        resp = httpx.get(f"{url}/health", timeout=3.0)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError):
        return False


@pytest.fixture(scope="session")
def api_gateway_url():
    import os

    url = os.getenv("API_GATEWAY_URL", "http://localhost:8000")
    if not _check_service(url):
        pytest.skip(f"API Gateway not running at {url}")
    return url


@pytest.fixture(scope="session")
def metrics_url():
    import os

    url = os.getenv("METRICS_SERVICE_URL", "http://localhost:8005")
    if not _check_service(url):
        pytest.skip(f"Metrics service not running at {url}")
    return url


@pytest.fixture(scope="session")
def agent_orchestrator_url():
    import os

    url = os.getenv("AGENT_ORCHESTRATOR_URL", "http://localhost:8002")
    if not _check_service(url):
        pytest.skip(f"Agent Orchestrator not running at {url}")
    return url
