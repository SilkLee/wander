# Week 8 DORA Metrics + Frontend Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a DORA metrics API and a frontend dashboard that displays DORA metrics with simple trends.

**Architecture:** Build a new FastAPI metrics endpoint in the metrics service that returns aggregate DORA metrics and time-series trend data. Add a lightweight React dashboard that calls the API and renders metric cards + a trend chart, with empty-state handling.

**Tech Stack:** FastAPI, Pydantic, React, TypeScript, Chart library (lightweight)

---

### Task 1: Metrics API schema + stub data

**Files:**
- Create: `services/metrics/app/models/dora.py`
- Create: `services/metrics/app/api/dora.py`
- Modify: `services/metrics/app/main.py`
- Test: `services/metrics/tests/test_dora_endpoint.py`

**Step 1: Write the failing test**

```python
def test_dora_endpoint_returns_metrics(client):
    response = client.get("/metrics/dora?from=2026-03-01&to=2026-03-07&interval=day")
    assert response.status_code == 200
    data = response.json()
    assert "deployment_frequency" in data
    assert "lead_time" in data
    assert "change_failure_rate" in data
    assert "mttr" in data
    assert "trend" in data
```

**Step 2: Run test to verify it fails**

Run: `pytest services/metrics/tests/test_dora_endpoint.py::test_dora_endpoint_returns_metrics -v`
Expected: FAIL (endpoint not found)

**Step 3: Write minimal implementation**

```python
class DORATrendPoint(BaseModel):
    timestamp: str
    deployment_frequency: float
    lead_time: float
    change_failure_rate: float
    mttr: float

class DORAResponse(BaseModel):
    deployment_frequency: float
    lead_time: float
    change_failure_rate: float
    mttr: float
    trend: list[DORATrendPoint]
```

```python
@router.get("/metrics/dora", response_model=DORAResponse)
def get_dora_metrics(from: str, to: str, interval: str = "day"):
    return DORAResponse(
        deployment_frequency=1.2,
        lead_time=18.4,
        change_failure_rate=0.12,
        mttr=3.6,
        trend=[...],
    )
```

**Step 4: Run test to verify it passes**

Run: `pytest services/metrics/tests/test_dora_endpoint.py::test_dora_endpoint_returns_metrics -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/metrics/app services/metrics/tests/test_dora_endpoint.py
git commit -m "feat: add DORA metrics endpoint"
```

---

### Task 2: Frontend dashboard

**Files:**
- Create: `frontend/src/pages/DoraDashboard.tsx`
- Create: `frontend/src/components/DoraMetricCard.tsx`
- Create: `frontend/src/components/DoraTrendChart.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/pages/DoraDashboard.test.tsx`

**Step 1: Write the failing test**

```tsx
import { render, screen } from "@testing-library/react";
import DoraDashboard from "./DoraDashboard";

test("renders DORA metrics cards", () => {
  render(<DoraDashboard />);
  expect(screen.getByText(/Deployment Frequency/i)).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- DoraDashboard.test.tsx`
Expected: FAIL (component not found)

**Step 3: Write minimal implementation**

```tsx
export default function DoraDashboard() {
  return (
    <div>
      <DoraMetricCard title="Deployment Frequency" value="1.2/day" />
      <DoraMetricCard title="Lead Time" value="18.4h" />
      <DoraMetricCard title="Change Failure Rate" value="12%" />
      <DoraMetricCard title="MTTR" value="3.6h" />
    </div>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `npm test -- DoraDashboard.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat: add DORA metrics dashboard"
```

---

### Task 3: Wire API to frontend and empty-state handling

**Files:**
- Modify: `frontend/src/pages/DoraDashboard.tsx`
- Create: `frontend/src/api/metrics.ts`
- Test: `frontend/src/pages/DoraDashboard.test.tsx`

**Step 1: Write the failing test**

```tsx
test("shows empty state when API fails", async () => {
  render(<DoraDashboard />);
  expect(await screen.findByText(/No data available/i)).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `npm test -- DoraDashboard.test.tsx`
Expected: FAIL

**Step 3: Write minimal implementation**

```tsx
useEffect(() => {
  fetchDoraMetrics().then(setData).catch(() => setError(true));
}, []);
```

**Step 4: Run test to verify it passes**

Run: `npm test -- DoraDashboard.test.tsx`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src
git commit -m "feat: wire DORA dashboard to metrics API"
```

---

**Plan complete and saved to `docs/plans/2026-03-14-week8-dora-frontend-implementation-plan.md`.** Two execution options:

**1. Subagent-Driven (this session)** – I dispatch fresh subagent per task, review between tasks, fast iteration  
**2. Parallel Session (separate)** – Open new session with executing-plans, batch execution with checkpoints

Which approach?
