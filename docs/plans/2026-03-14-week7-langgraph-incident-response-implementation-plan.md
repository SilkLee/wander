# Week 7 Incident Response LangGraph Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a new Incident Response LangGraph workflow that ingests logs + metrics + PR diff and outputs a structured incident report with rollback plan.

**Architecture:** Add new DTOs and agent roles, build a dedicated LangGraph flow with stability wrappers, and expose it through `/workflows/execute` as `workflow_type=incident_response`.

**Tech Stack:** Python 3.11, FastAPI, LangGraph, Pydantic v2, pytest

---

### Task 1: Add incident response DTOs

**Files:**
- Create: `services/agent-orchestrator/app/models/incident.py`
- Modify: `services/agent-orchestrator/app/models/__init__.py`
- Test: `services/agent-orchestrator/tests/test_incident_models.py`

**Step 1: Write the failing test**

```python
from app.models.incident import IncidentReport, MetricsSummary, ChangeImpact


def test_incident_report_validation():
    IncidentReport(
        root_cause="redis outage",
        evidence=["redis timeout"],
        remediation=["restart redis"],
        rollback=["revert deploy"],
    )
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_incident_models.py -v`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

```python
class IncidentReport(BaseModel):
    root_cause: str
    evidence: list[str]
    remediation: list[str]
    rollback: list[str]
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_incident_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/models/incident.py \
        services/agent-orchestrator/app/models/__init__.py \
        services/agent-orchestrator/tests/test_incident_models.py
git commit -m "feat: add incident response DTOs"
```

---

### Task 2: Add incident response agent roles

**Files:**
- Create: `services/agent-orchestrator/app/agents/incident_roles.py`
- Test: `services/agent-orchestrator/tests/test_incident_roles.py`

**Step 1: Write the failing test**

```python
import asyncio
from app.agents.incident_roles import metrics_analyzer, change_impact, coordinator


def test_incident_roles_execute():
    metrics = asyncio.get_event_loop().run_until_complete(metrics_analyzer({"metrics": {}}))
    impact = asyncio.get_event_loop().run_until_complete(change_impact({"diff": "diff --git a/x b/x"}))
    report = asyncio.get_event_loop().run_until_complete(
        coordinator({"metrics": metrics, "impact": impact, "evidence": []})
    )
    assert report.root_cause
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_incident_roles.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
async def metrics_analyzer(inputs: Dict) -> MetricsSummary: ...
async def change_impact(inputs: Dict) -> ChangeImpact: ...
async def coordinator(inputs: Dict) -> IncidentReport: ...
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_incident_roles.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/agents/incident_roles.py \
        services/agent-orchestrator/tests/test_incident_roles.py
git commit -m "feat: add incident response agent roles"
```

---

### Task 3: Build incident response LangGraph workflow

**Files:**
- Create: `services/agent-orchestrator/app/workflows/incident_response_flow.py`
- Modify: `services/agent-orchestrator/app/workflows/__init__.py`
- Test: `services/agent-orchestrator/tests/test_incident_response_flow.py`

**Step 1: Write the failing test**

```python
from app.workflows.incident_response_flow import build_incident_graph


def test_incident_graph_builds():
    graph = build_incident_graph()
    assert graph is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_incident_response_flow.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
def build_incident_graph() -> Any:
    graph = StateGraph(IncidentState)
    ...
    return graph.compile()
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_incident_response_flow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/workflows/incident_response_flow.py \
        services/agent-orchestrator/tests/test_incident_response_flow.py \
        services/agent-orchestrator/app/workflows/__init__.py
git commit -m "feat: add incident response workflow"
```

---

### Task 4: Wire workflow into API

**Files:**
- Modify: `services/agent-orchestrator/app/api/workflows.py`
- Test: `services/agent-orchestrator/tests/test_workflow_execute_incident_response.py`

**Step 1: Write the failing test**

```python
def test_execute_incident_response(client):
    response = client.post(
        "/workflows/execute",
        json={"workflow_type": "incident_response", "inputs": {"log_content": "err", "metrics": {}, "diff": ""}},
    )
    assert response.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_workflow_execute_incident_response.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

```python
elif request.workflow_type == "incident_response":
    result = await run_incident_response(request.inputs)
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_workflow_execute_incident_response.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/api/workflows.py \
        services/agent-orchestrator/tests/test_workflow_execute_incident_response.py
git commit -m "feat: expose incident response workflow"
```

---

### Task 5: End‑to‑end verification

**Files:**
- Modify: `docs/plans/2026-03-14-week7-langgraph-incident-response-implementation-plan.md`

**Step 1: Run relevant tests**

Run: `pytest services/agent-orchestrator/tests/test_incident_models.py -v`
Expected: PASS

Run: `pytest services/agent-orchestrator/tests/test_incident_roles.py -v`
Expected: PASS

Run: `pytest services/agent-orchestrator/tests/test_incident_response_flow.py -v`
Expected: PASS

Run: `pytest services/agent-orchestrator/tests/test_workflow_execute_incident_response.py -v`
Expected: PASS (or existing failures noted)

**Step 2: Record verification results in plan doc**

Add section “Verification Results” with timestamps and status.

#### Verification Results

- 2026-03-14 10:07: `pytest tests/test_incident_models.py -v` (PASS)
- 2026-03-14 10:07: `pytest tests/test_incident_roles.py -v` (PASS)
- 2026-03-14 10:07: `pytest tests/test_incident_response_flow.py -v` (PASS)
- 2026-03-14 10:08: `pytest tests/test_workflow_execute_incident_response.py` (PASS; warning about `python_multipart` deprecation in starlette)

**Step 3: Commit**

```bash
git add docs/plans/2026-03-14-week7-langgraph-incident-response-implementation-plan.md
git commit -m "docs: record Week 7 verification results"
```

---

**Plan complete and saved to `docs/plans/2026-03-14-week7-langgraph-incident-response-implementation-plan.md`.** Two execution options:

**1. Subagent-Driven (this session)** – I dispatch fresh subagent per task, review between tasks, fast iteration  
**2. Parallel Session (separate)** – Open new session with executing-plans, batch execution with checkpoints

Which approach?
