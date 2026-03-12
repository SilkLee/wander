# Week 3 LangGraph Multi-Agent Orchestration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two new LangGraph workflows (PR Risk Assessment + Code Review Assistant) that reuse stability/metadata and return consistent API responses.

**Architecture:** Implement new review DTOs, agent roles, and two LangGraph flows. Wire them into `/workflows/execute` with `workflow_type=pr_risk|code_review`, reusing stability wrappers and `intermediate_summary`.

**Tech Stack:** Python 3.11, FastAPI, LangGraph, Pydantic v2, pytest

---

### Task 1: Add review DTOs (PR risk + code review)

**Files:**
- Create: `services/agent-orchestrator/app/models/review.py`
- Modify: `services/agent-orchestrator/app/models/__init__.py`
- Test: `services/agent-orchestrator/tests/test_review_models.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_review_models.py`:

```python
from pydantic import ValidationError

from app.models.review import PRRiskReport, ReviewComment, ReviewSummary


def test_pr_risk_report_validation():
    PRRiskReport(
        risk_level="medium",
        impacted_areas=["ci", "db"],
        checks=["run full integration"],
        rationale="Touches migration + db config",
    )


def test_review_comment_validation():
    ReviewComment(
        file="services/api/handler.py",
        line=42,
        severity="warning",
        message="Missing input validation",
        suggestion="Add pydantic validation",
    )


def test_review_summary_validation():
    ReviewSummary(
        summary="Overall OK",
        comments=[],
        severity_breakdown={"warning": 1},
    )


def test_invalid_risk_level_rejected():
    try:
        PRRiskReport(
            risk_level="invalid",
            impacted_areas=[],
            checks=[],
            rationale="",
        )
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError")
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_review_models.py -v`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/models/review.py`:

```python
from typing import Dict, List

from pydantic import BaseModel, Field


class PRRiskReport(BaseModel):
    risk_level: str = Field(pattern="^(low|medium|high|critical)$")
    impacted_areas: List[str] = Field(default_factory=list)
    checks: List[str] = Field(default_factory=list)
    rationale: str = Field(description="Reasoning for risk score")


class ReviewComment(BaseModel):
    file: str = Field(description="File path")
    line: int = Field(ge=1)
    severity: str = Field(pattern="^(info|warning|error)$")
    message: str = Field(description="Comment message")
    suggestion: str = Field(default="")


class ReviewSummary(BaseModel):
    summary: str = Field(description="Short overall summary")
    comments: List[ReviewComment] = Field(default_factory=list)
    severity_breakdown: Dict[str, int] = Field(default_factory=dict)
```

Update `services/agent-orchestrator/app/models/__init__.py` to export `PRRiskReport`, `ReviewComment`, `ReviewSummary`.

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_review_models.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/models/review.py \
        services/agent-orchestrator/app/models/__init__.py \
        services/agent-orchestrator/tests/test_review_models.py
git commit -m "feat: add review DTOs for week 3 workflows"
```

---

### Task 2: Add review roles (diff parser, risk analyst, reviewer, summarizer)

**Files:**
- Create: `services/agent-orchestrator/app/agents/review_roles.py`
- Test: `services/agent-orchestrator/tests/test_review_roles.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_review_roles.py`:

```python
import asyncio

from app.agents.review_roles import diff_parser, risk_analyst, reviewer, summarizer


def test_review_roles_execute():
    parsed = asyncio.get_event_loop().run_until_complete(
        diff_parser({"diff": "diff --git a/x b/x"})
    )
    report = asyncio.get_event_loop().run_until_complete(risk_analyst(parsed))
    summary = asyncio.get_event_loop().run_until_complete(
        summarizer({"report": report, "comments": []})
    )
    assert report.risk_level
    assert summary["analysis"]
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_review_roles.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/agents/review_roles.py`:

```python
from typing import Dict, List

from app.models.review import PRRiskReport, ReviewComment, ReviewSummary


async def diff_parser(inputs: Dict) -> Dict:
    return {
        "diff": inputs.get("diff", ""),
        "context": inputs.get("context", {}),
        "standards": inputs.get("coding_standards", ""),
    }


async def risk_analyst(parsed: Dict) -> PRRiskReport:
    return PRRiskReport(
        risk_level="medium",
        impacted_areas=["ci"],
        checks=["run integration tests"],
        rationale="Touches CI config",
    )


async def reviewer(parsed: Dict) -> List[ReviewComment]:
    return [
        ReviewComment(
            file="unknown",
            line=1,
            severity="info",
            message="Review diff for style consistency",
            suggestion="Apply project formatting",
        )
    ]


async def summarizer(payload: Dict) -> Dict:
    report: PRRiskReport = payload.get("report")
    comments: List[ReviewComment] = payload.get("comments", [])
    summary = ReviewSummary(
        summary="Review complete",
        comments=comments,
        severity_breakdown={"info": len(comments)},
    )
    return {
        "analysis": summary.summary,
        "summary": summary,
        "report": report,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_review_roles.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/agents/review_roles.py \
        services/agent-orchestrator/tests/test_review_roles.py
git commit -m "feat: add review roles for langgraph workflows"
```

---

### Task 3: Add PR risk LangGraph flow

**Files:**
- Create: `services/agent-orchestrator/app/workflows/pr_risk_flow.py`
- Modify: `services/agent-orchestrator/app/workflows/__init__.py`
- Test: `services/agent-orchestrator/tests/test_pr_risk_flow.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_pr_risk_flow.py`:

```python
import asyncio

from app.workflows.pr_risk_flow import run_pr_risk


def test_pr_risk_flow_returns_report():
    result = asyncio.get_event_loop().run_until_complete(
        run_pr_risk({"diff": "diff --git a/x b/x", "context": {}})
    )
    assert "report" in result
    assert result["report"].risk_level
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_pr_risk_flow.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/workflows/pr_risk_flow.py`:

```python
from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from app.agents.review_roles import diff_parser, risk_analyst, summarizer
from app.workflows.stability import run_with_retry, CircuitBreaker


class PRRiskState(dict):
    pass


_PR_RISK_BREAKER = CircuitBreaker(threshold=2, cooldown_seconds=30.0)


async def run_pr_risk(inputs: Dict[str, Any]) -> Dict[str, Any]:
    graph = StateGraph(PRRiskState)
    graph.add_node("diff_parser", diff_parser)
    graph.add_node("risk_analyst", risk_analyst)
    graph.add_node("summarizer", summarizer)
    graph.add_edge(START, "diff_parser")
    graph.add_edge("diff_parser", "risk_analyst")
    graph.add_edge("risk_analyst", "summarizer")
    graph.add_edge("summarizer", END)

    compiled = graph.compile()
    base_state = {"errors": [], "retry_summary": {}, "degraded": False}

    async def invoke():
        return await compiled.ainvoke({**inputs, **base_state})

    result, error = await run_with_retry(invoke, retries=1, timeout_seconds=1.0)
    if error is not None:
        _PR_RISK_BREAKER.record_failure()
        return {**base_state, "errors": [{"node": "pr_risk", "message": str(error), "degraded": True}], "degraded": True}
    _PR_RISK_BREAKER.record_success()
    return result
```

Update `services/agent-orchestrator/app/workflows/__init__.py` to export `run_pr_risk`.

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_pr_risk_flow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/workflows/pr_risk_flow.py \
        services/agent-orchestrator/app/workflows/__init__.py \
        services/agent-orchestrator/tests/test_pr_risk_flow.py
git commit -m "feat: add pr risk langgraph flow"
```

---

### Task 4: Add code review LangGraph flow

**Files:**
- Create: `services/agent-orchestrator/app/workflows/code_review_flow.py`
- Modify: `services/agent-orchestrator/app/workflows/__init__.py`
- Test: `services/agent-orchestrator/tests/test_code_review_flow.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_code_review_flow.py`:

```python
import asyncio

from app.workflows.code_review_flow import run_code_review


def test_code_review_flow_returns_summary():
    result = asyncio.get_event_loop().run_until_complete(
        run_code_review({"diff": "diff --git a/x b/x", "coding_standards": ""})
    )
    assert "summary" in result
    assert result["summary"].summary
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_code_review_flow.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/workflows/code_review_flow.py`:

```python
from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from app.agents.review_roles import diff_parser, reviewer, summarizer
from app.workflows.stability import run_with_retry, CircuitBreaker


class CodeReviewState(dict):
    pass


_CODE_REVIEW_BREAKER = CircuitBreaker(threshold=2, cooldown_seconds=30.0)


async def run_code_review(inputs: Dict[str, Any]) -> Dict[str, Any]:
    graph = StateGraph(CodeReviewState)
    graph.add_node("diff_parser", diff_parser)
    graph.add_node("reviewer", reviewer)
    graph.add_node("summarizer", summarizer)
    graph.add_edge(START, "diff_parser")
    graph.add_edge("diff_parser", "reviewer")
    graph.add_edge("reviewer", "summarizer")
    graph.add_edge("summarizer", END)

    compiled = graph.compile()
    base_state = {"errors": [], "retry_summary": {}, "degraded": False}

    async def invoke():
        return await compiled.ainvoke({**inputs, **base_state})

    result, error = await run_with_retry(invoke, retries=1, timeout_seconds=1.0)
    if error is not None:
        _CODE_REVIEW_BREAKER.record_failure()
        return {**base_state, "errors": [{"node": "code_review", "message": str(error), "degraded": True}], "degraded": True}
    _CODE_REVIEW_BREAKER.record_success()
    return result
```

Update `services/agent-orchestrator/app/workflows/__init__.py` to export `run_code_review`.

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_code_review_flow.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/workflows/code_review_flow.py \
        services/agent-orchestrator/app/workflows/__init__.py \
        services/agent-orchestrator/tests/test_code_review_flow.py
git commit -m "feat: add code review langgraph flow"
```

---

### Task 5: Wire new flows into workflow execution API

**Files:**
- Modify: `services/agent-orchestrator/app/api/workflows.py`
- Modify: `services/agent-orchestrator/app/models/requests.py`
- Test: `services/agent-orchestrator/tests/test_workflow_execute_reviews.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_workflow_execute_reviews.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_execute_pr_risk_workflow():
    response = client.post(
        "/workflows/execute",
        json={"workflow_type": "pr_risk", "inputs": {"diff": "diff"}},
    )
    assert response.status_code == 200
    assert "outputs" in response.json()


def test_execute_code_review_workflow():
    response = client.post(
        "/workflows/execute",
        json={"workflow_type": "code_review", "inputs": {"diff": "diff"}},
    )
    assert response.status_code == 200
    assert "outputs" in response.json()
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_workflow_execute_reviews.py -v`
Expected: FAIL (unknown workflow type)

**Step 3: Write minimal implementation**

- Update `WorkflowExecutionRequest` schema to document allowed types.
- Update `/workflows/execute` to dispatch to `run_pr_risk` and `run_code_review`.
- Ensure response wraps outputs in `WorkflowExecutionResponse`.

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_workflow_execute_reviews.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/api/workflows.py \
        services/agent-orchestrator/app/models/requests.py \
        services/agent-orchestrator/tests/test_workflow_execute_reviews.py
git commit -m "feat: add review workflows to execute endpoint"
```

---

### Task 6: Full verification

**Steps:**
1. Run `pytest services/agent-orchestrator/tests -v`
2. Run `python -m py_compile` on new modules

**Commit (if needed for fixes):**

```bash
git add -A
git commit -m "test: verify week 3 langgraph workflows"
```
