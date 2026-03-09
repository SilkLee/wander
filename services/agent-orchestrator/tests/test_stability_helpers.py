import asyncio
import importlib.util
from pathlib import Path

import pytest


def load_run_with_retry():
    module_path = Path(__file__).resolve().parents[1] / "app" / "workflows" / "stability.py"
    spec = importlib.util.spec_from_file_location("stability_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load stability module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.run_with_retry


@pytest.mark.asyncio
async def test_run_with_retry_succeeds_after_retry():
    run_with_retry = load_run_with_retry()
    attempts = {"count": 0}

    async def flaky():
        attempts["count"] += 1
        if attempts["count"] < 2:
            raise RuntimeError("boom")
        return "ok"

    result, error = await run_with_retry(flaky, retries=2, timeout_seconds=0.1)
    assert result == "ok"
    assert error is None


@pytest.mark.asyncio
async def test_run_with_retry_times_out():
    run_with_retry = load_run_with_retry()
    async def slow():
        await asyncio.sleep(0.2)
        return "ok"

    result, error = await run_with_retry(slow, retries=0, timeout_seconds=0.05)
    assert result is None
    assert error is not None
