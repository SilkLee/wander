# Day 12 Stability Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add timeouts, retries, and graceful degradation to the LangGraph build-failure triage flow so the API returns partial results instead of failing.

**Architecture:** Wrap each LangGraph role node with a stability layer (timeout + retry + error capture). Persist errors into `intermediate_summary`, and optionally apply a lightweight circuit breaker that skips failing nodes and marks the response as degraded.

**Tech Stack:** Python 3.11, FastAPI, LangGraph, Pydantic v2, pytest

---

### Task 1: Add stability error DTO and summary shape

**Files:**
- Create: `services/agent-orchestrator/app/models/stability.py`
- Modify: `services/agent-orchestrator/app/models/__init__.py`
- Test: `services/agent-orchestrator/tests/test_stability_models.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_stability_models.py`:

```python
from pydantic import ValidationError

from app.models.stability import StabilityError, RetrySummary


def test_stability_error_validation():
    StabilityError(
        node="diagnose",
        error_type="timeout",
        message="diagnose timed out",
        retry_attempts=2,
        degraded=True,
    )


def test_retry_summary_validation():
    summary = RetrySummary(retries={"parse": 1, "diagnose": 2})
    assert summary.retries["diagnose"] == 2


def test_invalid_error_type_rejected():
    try:
        StabilityError(
            node="parse",
            error_type="invalid",
            message="bad",
            retry_attempts=0,
            degraded=False,
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError")
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_stability_models.py -v`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/models/stability.py`:

```python
from typing import Dict
from pydantic import BaseModel, Field


class StabilityError(BaseModel):
    node: str = Field(description="LangGraph node name")
    error_type: str = Field(pattern="^(timeout|dependency|validation|unknown)$")
    message: str = Field(description="Short error description")
    retry_attempts: int = Field(ge=0, description="Number of retries attempted")
    degraded: bool = Field(description="Whether response was degraded")


class RetrySummary(BaseModel):
    retries: Dict[str, int] = Field(default_factory=dict)
```

Update `services/agent-orchestrator/app/models/__init__.py` to export `StabilityError` and `RetrySummary`.

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_stability_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/models/stability.py \
        services/agent-orchestrator/app/models/__init__.py \
        services/agent-orchestrator/tests/test_stability_models.py
git commit -m "feat: add stability error models"
```

---

### Task 2: Add retry/timeout helpers for LangGraph nodes

**Files:**
- Create: `services/agent-orchestrator/app/workflows/stability.py`
- Test: `services/agent-orchestrator/tests/test_stability_helpers.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_stability_helpers.py`:

```python
import asyncio
import pytest

from app.workflows.stability import run_with_retry


@pytest.mark.asyncio
async def test_run_with_retry_succeeds_after_retry():
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
    async def slow():
        await asyncio.sleep(0.2)
        return "ok"

    result, error = await run_with_retry(slow, retries=0, timeout_seconds=0.05)
    assert result is None
    assert error is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_stability_helpers.py -v`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/workflows/stability.py`:

```python
import asyncio
from typing import Awaitable, Callable, Optional, Tuple, TypeVar

T = TypeVar("T")


async def run_with_retry(
    func: Callable[[], Awaitable[T]],
    retries: int,
    timeout_seconds: float,
) -> Tuple[Optional[T], Optional[Exception]]:
    attempt = 0
    while True:
        try:
            result = await asyncio.wait_for(func(), timeout=timeout_seconds)
            return result, None
        except Exception as exc:
            if attempt >= retries:
                return None, exc
            attempt += 1
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_stability_helpers.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/workflows/stability.py \
        services/agent-orchestrator/tests/test_stability_helpers.py
git commit -m "feat: add retry and timeout helper"
```

---

### Task 3: Add node-level error capture to LangGraph workflow

**Files:**
- Modify: `services/agent-orchestrator/app/workflows/langgraph_flow.py`
- Modify: `services/agent-orchestrator/app/workflows/__init__.py`
- Test: `services/agent-orchestrator/tests/test_langgraph_stability.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_langgraph_stability.py`:

```python
import asyncio

from app.workflows.langgraph_flow import run_langgraph


def test_langgraph_returns_errors_on_failure():
    result = asyncio.get_event_loop().run_until_complete(
        run_langgraph({"log_content": "err", "force_fail": "diagnose"})
    )
    assert "errors" in result
    assert result["errors"], "Expected error metadata"
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_langgraph_stability.py -v`
Expected: FAIL (errors missing)

**Step 3: Write minimal implementation**

Update `run_langgraph` to:
- wrap each node with `run_with_retry`
- store errors into an `errors` list
- include `retry_summary` and `degraded` flags
- support a test-only input flag `force_fail` to simulate failures in tests

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_langgraph_stability.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/workflows/langgraph_flow.py \
        services/agent-orchestrator/app/workflows/__init__.py \
        services/agent-orchestrator/tests/test_langgraph_stability.py
git commit -m "feat: add node-level error capture in langgraph"
```

---

### Task 4: Surface stability metadata in API response

**Files:**
- Modify: `services/agent-orchestrator/app/api/workflows.py`
- Modify: `services/agent-orchestrator/app/models/requests.py`
- Test: `services/agent-orchestrator/tests/test_api_response_stability.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_api_response_stability.py`:

```python
from app.models.requests import LogAnalysisResponse


def test_response_contains_stability_fields():
    response = LogAnalysisResponse(
        analysis_id="id",
        root_cause="rc",
        severity="high",
        suggested_fixes=["fix"],
        references=[],
        confidence=0.5,
        intermediate_summary={"errors": [{"node": "diagnose"}]},
    )
    assert "errors" in response.intermediate_summary
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_api_response_stability.py -v`
Expected: FAIL if response schema omits errors

**Step 3: Write minimal implementation**

- Ensure `LogAnalysisResponse` allows stability metadata (errors, degraded, retry_summary).
- Ensure API populates `intermediate_summary` with stability fields from langgraph output.

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_api_response_stability.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/api/workflows.py \
        services/agent-orchestrator/app/models/requests.py \
        services/agent-orchestrator/tests/test_api_response_stability.py
git commit -m "feat: surface stability metadata in response"
```

---

### Task 5: Add lightweight circuit breaker and fallback path

**Files:**
- Modify: `services/agent-orchestrator/app/workflows/stability.py`
- Modify: `services/agent-orchestrator/app/workflows/langgraph_flow.py`
- Test: `services/agent-orchestrator/tests/test_circuit_breaker.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_circuit_breaker.py`:

```python
import asyncio

from app.workflows.langgraph_flow import run_langgraph


def test_circuit_breaker_degrades_response():
    payload = {"log_content": "err", "force_fail": "diagnose", "simulate_breaker": True}
    result = asyncio.get_event_loop().run_until_complete(run_langgraph(payload))
    assert result.get("degraded") is True
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_circuit_breaker.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Implement a simple in-memory circuit breaker with:
- failure counter
- open threshold
- cooldown timer

When open, skip diagnose/evidence/remediate and return a minimal response with `degraded=True`.

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_circuit_breaker.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/workflows/stability.py \
        services/agent-orchestrator/app/workflows/langgraph_flow.py \
        services/agent-orchestrator/tests/test_circuit_breaker.py
git commit -m "feat: add circuit breaker fallback"
```

---

### Task 6: Full verification

**Steps:**
1. Run `pytest services/agent-orchestrator/tests -v` (ignore test_health if redis missing)
2. Run `python -m py_compile` on new/modified modules

**Commit (if needed for fixes):**

```bash
git add -A
git commit -m "test: verify stability optimizations"
```
