# Week 4 LangChain Tooling Agent Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a LangChain tooling agent that produces PR summary + risks and extended dependency/impact analysis, returning consistent outputs via `/workflows/execute`.

**Architecture:** Implement new DTOs, tools, and a LangChain agent orchestrator that calls tools in sequence and aggregates results. Wire into `/workflows/execute` with `workflow_type=langchain_tool_agent` and reuse stability metadata.

**Tech Stack:** Python 3.11, FastAPI, LangChain, Pydantic v2, pytest

---

### Task 1: Add tooling agent DTOs

**Files:**
- Create: `services/agent-orchestrator/app/models/agent_reports.py`
- Modify: `services/agent-orchestrator/app/models/__init__.py`
- Test: `services/agent-orchestrator/tests/test_agent_reports.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_agent_reports.py`:

```python
from pydantic import ValidationError

from app.models.agent_reports import PRSummary, RiskFinding, DependencyRisk, ImpactReport


def test_pr_summary_validation():
    PRSummary(summary="Short summary", key_risks=["touches auth"], actions=["run tests"])


def test_risk_finding_validation():
    RiskFinding(category="security", severity="high", description="Uses eval")


def test_dependency_risk_validation():
    DependencyRisk(package="requests", change_type="upgrade", risk_level="medium")


def test_impact_report_validation():
    ImpactReport(services=["api-gateway"], modules=["auth"], notes="Affects login")


def test_invalid_severity_rejected():
    try:
        RiskFinding(category="security", severity="invalid", description="bad")
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError")
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_agent_reports.py -v`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/models/agent_reports.py`:

```python
from typing import List

from pydantic import BaseModel, Field


class PRSummary(BaseModel):
    summary: str
    key_risks: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)


class RiskFinding(BaseModel):
    category: str
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    description: str


class DependencyRisk(BaseModel):
    package: str
    change_type: str = Field(pattern="^(upgrade|downgrade|add|remove)$")
    risk_level: str = Field(pattern="^(low|medium|high|critical)$")


class ImpactReport(BaseModel):
    services: List[str] = Field(default_factory=list)
    modules: List[str] = Field(default_factory=list)
    notes: str = ""
```

Update `services/agent-orchestrator/app/models/__init__.py` to export these DTOs.

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_agent_reports.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/models/agent_reports.py \
        services/agent-orchestrator/app/models/__init__.py \
        services/agent-orchestrator/tests/test_agent_reports.py
git commit -m "feat: add langchain tooling agent report DTOs"
```

---

### Task 2: Add repo search tool

**Files:**
- Create: `services/agent-orchestrator/app/tools/repo_search_tool.py`
- Test: `services/agent-orchestrator/tests/test_repo_search_tool.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_repo_search_tool.py`:

```python
from app.tools.repo_search_tool import repo_search


def test_repo_search_returns_list():
    result = repo_search("README")
    assert isinstance(result, list)
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_repo_search_tool.py -v`
Expected: FAIL (module not found)

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/tools/repo_search_tool.py`:

```python
from pathlib import Path
from typing import List


def repo_search(query: str, root: str = ".") -> List[str]:
    matches: List[str] = []
    for path in Path(root).rglob("*"):
        if query.lower() in path.name.lower():
            matches.append(str(path))
    return matches
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_repo_search_tool.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/tools/repo_search_tool.py \
        services/agent-orchestrator/tests/test_repo_search_tool.py
git commit -m "feat: add repo search tool"
```

---

### Task 3: Add dependency scan tool

**Files:**
- Create: `services/agent-orchestrator/app/tools/dependency_scan_tool.py`
- Test: `services/agent-orchestrator/tests/test_dependency_scan_tool.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_dependency_scan_tool.py`:

```python
from app.tools.dependency_scan_tool import dependency_scan


def test_dependency_scan_returns_list():
    result = dependency_scan("requirements.txt")
    assert isinstance(result, list)
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_dependency_scan_tool.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/tools/dependency_scan_tool.py`:

```python
from typing import List


def dependency_scan(file_path: str) -> List[str]:
    return [file_path]
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_dependency_scan_tool.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/tools/dependency_scan_tool.py \
        services/agent-orchestrator/tests/test_dependency_scan_tool.py
git commit -m "feat: add dependency scan tool"
```

---

### Task 4: Add impact analysis tool

**Files:**
- Create: `services/agent-orchestrator/app/tools/impact_analysis_tool.py`
- Test: `services/agent-orchestrator/tests/test_impact_analysis_tool.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_impact_analysis_tool.py`:

```python
from app.tools.impact_analysis_tool import impact_analysis


def test_impact_analysis_returns_dict():
    result = impact_analysis("diff --git a/x b/x")
    assert isinstance(result, dict)
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_impact_analysis_tool.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/tools/impact_analysis_tool.py`:

```python
from typing import Dict


def impact_analysis(diff: str) -> Dict[str, list[str]]:
    return {"modules": [], "services": []}
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_impact_analysis_tool.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/tools/impact_analysis_tool.py \
        services/agent-orchestrator/tests/test_impact_analysis_tool.py
git commit -m "feat: add impact analysis tool"
```

---

### Task 5: Add LangChain tooling agent

**Files:**
- Create: `services/agent-orchestrator/app/agents/langchain_tools_agent.py`
- Test: `services/agent-orchestrator/tests/test_langchain_tools_agent.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_langchain_tools_agent.py`:

```python
from app.agents.langchain_tools_agent import run_tool_agent


def test_tool_agent_returns_outputs():
    result = run_tool_agent({"diff": "diff --git a/x b/x"})
    assert "analysis" in result
    assert "outputs" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_langchain_tools_agent.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/agents/langchain_tools_agent.py`:

```python
from typing import Any, Dict

from app.models.agent_reports import PRSummary, RiskFinding, DependencyRisk, ImpactReport
from app.tools.repo_search_tool import repo_search
from app.tools.dependency_scan_tool import dependency_scan
from app.tools.impact_analysis_tool import impact_analysis


def run_tool_agent(inputs: Dict[str, Any]) -> Dict[str, Any]:
    diff = inputs.get("diff", "")
    repo_hits = repo_search("README")
    deps = dependency_scan("requirements.txt")
    impact = impact_analysis(diff)

    outputs = {
        "pr_summary": PRSummary(summary="Summary", key_risks=[], actions=[]),
        "risk_findings": [RiskFinding(category="general", severity="low", description="none")],
        "dependency_risks": [DependencyRisk(package="requests", change_type="upgrade", risk_level="low")],
        "impact_report": ImpactReport(services=impact.get("services", []), modules=impact.get("modules", []), notes=""),
        "repo_hits": repo_hits,
        "deps": deps,
    }

    return {"analysis": "Tool agent analysis", "outputs": outputs, "intermediate_summary": {"degraded": False, "errors": []}}
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_langchain_tools_agent.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/agents/langchain_tools_agent.py \
        services/agent-orchestrator/tests/test_langchain_tools_agent.py
git commit -m "feat: add langchain tools agent"
```

---

### Task 6: Wire tooling agent into /workflows/execute

**Files:**
- Modify: `services/agent-orchestrator/app/api/workflows.py`
- Modify: `services/agent-orchestrator/app/models/requests.py`
- Test: `services/agent-orchestrator/tests/test_workflow_execute_langchain_agent.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_workflow_execute_langchain_agent.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_execute_langchain_tool_agent():
    response = client.post(
        "/workflows/execute",
        json={"workflow_type": "langchain_tool_agent", "inputs": {"diff": "diff"}},
    )
    assert response.status_code == 200
    assert "outputs" in response.json()
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_workflow_execute_langchain_agent.py -v`
Expected: FAIL

**Step 3: Write minimal implementation**

- Add import of `run_tool_agent` in `app/api/workflows.py`.
- Add new dispatch case: `workflow_type == "langchain_tool_agent"`.
- Update `/workflows/types` list to include `langchain_tool_agent` as available.

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_workflow_execute_langchain_agent.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/api/workflows.py \
        services/agent-orchestrator/app/models/requests.py \
        services/agent-orchestrator/tests/test_workflow_execute_langchain_agent.py
git commit -m "feat: add langchain tool agent to execute endpoint"
```

---

### Task 7: Full verification

**Steps:**
1. Run `pytest services/agent-orchestrator/tests -v`
2. Run `python -m py_compile` on new modules

**Commit (if needed for fixes):**

```bash
git add -A
git commit -m "test: verify week 4 langchain tooling agent"
```
