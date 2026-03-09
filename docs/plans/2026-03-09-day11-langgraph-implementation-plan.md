# Day 11 LangGraph Multi-Agent Orchestration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement LangGraph-based multi-agent orchestration for Build Failure Triage with structured intermediate outputs and API response summary.

**Architecture:** A sequential LangGraph workflow runs four roles (Parser → Diagnoser → Evidence Retriever → Remediator). Each node emits a validated DTO, then a final summarizer builds the API response and intermediate summary. No retries/persistence in Day 11.

**Tech Stack:** Python 3.11, FastAPI, LangGraph (via langchain), Pydantic v2

---

### Task 1: Add intermediate DTOs for multi-agent outputs

**Files:**
- Create: `services/agent-orchestrator/app/models/intermediate.py`
- Modify: `services/agent-orchestrator/app/models/__init__.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_intermediate_models.py`:

```python
from pydantic import ValidationError

from app.models.intermediate import ParsedLog, Diagnosis, EvidenceBundle, Remediation


def test_parsed_log_validation():
    ParsedLog(
        source="ci",
        error_signatures=["timeout expired"],
        stack_fragments=["database.py:142"],
        environment={"service": "api"},
    )


def test_diagnosis_validation():
    Diagnosis(
        root_cause_candidates=["DB connection timeout"],
        confidence=0.7,
        reasoning="Connection to DB failed during deploy",
    )


def test_evidence_bundle_validation():
    EvidenceBundle(
        citations=["https://docs.example.com/db"],
        snippets=["timeout expired"],
        relevance_scores=[0.8],
    )


def test_remediation_validation():
    Remediation(
        steps=["Check DB network ACL"],
        risk_notes=["May require infra change"],
        verification_commands=["psql -h 10.0.1.50 -p 5432"],
    )


def test_validation_rejects_bad_confidence():
    try:
        Diagnosis(root_cause_candidates=["x"], confidence=1.5, reasoning="bad")
    except ValidationError:
        return
    raise AssertionError("Expected ValidationError for confidence > 1.0")
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_intermediate_models.py -v`

Expected: FAIL (module not found).

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/models/intermediate.py`:

```python
from typing import Dict, List
from pydantic import BaseModel, Field


class ParsedLog(BaseModel):
    source: str = Field(description="Log source (ci/runtime/deploy)")
    error_signatures: List[str] = Field(description="Key error signatures")
    stack_fragments: List[str] = Field(description="Stack trace fragments")
    environment: Dict[str, str] = Field(description="Contextual environment")


class Diagnosis(BaseModel):
    root_cause_candidates: List[str] = Field(description="Candidate root causes")
    confidence: float = Field(ge=0.0, le=1.0, description="Diagnosis confidence")
    reasoning: str = Field(description="Short reasoning summary")


class EvidenceBundle(BaseModel):
    citations: List[str] = Field(description="Reference URLs or docs")
    snippets: List[str] = Field(description="Key evidence excerpts")
    relevance_scores: List[float] = Field(description="Relevance scores")


class Remediation(BaseModel):
    steps: List[str] = Field(description="Fix steps")
    risk_notes: List[str] = Field(description="Risks or caveats")
    verification_commands: List[str] = Field(description="Verification commands")
```

Update `services/agent-orchestrator/app/models/__init__.py` to export these models.

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_intermediate_models.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/models/intermediate.py \
        services/agent-orchestrator/app/models/__init__.py \
        services/agent-orchestrator/tests/test_intermediate_models.py
git commit -m "feat: add intermediate DTOs for multi-agent flow"
```

---

### Task 2: Define LangGraph workflow and agent nodes

**Files:**
- Create: `services/agent-orchestrator/app/workflows/langgraph_flow.py`
- Create: `services/agent-orchestrator/app/agents/roles.py`
- Modify: `services/agent-orchestrator/app/workflows/__init__.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_langgraph_flow.py`:

```python
from app.workflows.langgraph_flow import build_langgraph_flow


def test_flow_builds():
    graph = build_langgraph_flow()
    assert graph is not None
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_langgraph_flow.py -v`

Expected: FAIL (module not found).

**Step 3: Write minimal implementation**

Create `services/agent-orchestrator/app/agents/roles.py`:

```python
from typing import Dict

from app.models.intermediate import ParsedLog, Diagnosis, EvidenceBundle, Remediation


async def parse_log(inputs: Dict) -> ParsedLog:
    return ParsedLog(
        source=inputs.get("log_type", "build"),
        error_signatures=["timeout"],
        stack_fragments=["database.py:142"],
        environment={"repository": inputs.get("context", {}).get("repository", "")},
    )


async def diagnose(parsed: ParsedLog) -> Diagnosis:
    return Diagnosis(
        root_cause_candidates=["DB connection timeout"],
        confidence=0.7,
        reasoning="Connection timed out while connecting to DB",
    )


async def retrieve_evidence(diagnosis: Diagnosis) -> EvidenceBundle:
    return EvidenceBundle(
        citations=[],
        snippets=["timeout expired"],
        relevance_scores=[0.5],
    )


async def remediate(diagnosis: Diagnosis, evidence: EvidenceBundle) -> Remediation:
    return Remediation(
        steps=["Check DB network connectivity"],
        risk_notes=["May require infra changes"],
        verification_commands=["psql -h 10.0.1.50 -p 5432"],
    )
```

Create `services/agent-orchestrator/app/workflows/langgraph_flow.py`:

```python
from typing import Dict

from app.agents.roles import parse_log, diagnose, retrieve_evidence, remediate


def build_langgraph_flow():
    return {
        "parse_log": parse_log,
        "diagnose": diagnose,
        "retrieve_evidence": retrieve_evidence,
        "remediate": remediate,
    }


async def run_langgraph(inputs: Dict) -> Dict:
    parsed = await parse_log(inputs)
    diagnosis = await diagnose(parsed)
    evidence = await retrieve_evidence(diagnosis)
    remediation = await remediate(diagnosis, evidence)
    return {
        "parsed": parsed,
        "diagnosis": diagnosis,
        "evidence": evidence,
        "remediation": remediation,
    }
```

Update `services/agent-orchestrator/app/workflows/__init__.py` to export `build_langgraph_flow` and `run_langgraph`.

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_langgraph_flow.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/agents/roles.py \
        services/agent-orchestrator/app/workflows/langgraph_flow.py \
        services/agent-orchestrator/app/workflows/__init__.py \
        services/agent-orchestrator/tests/test_langgraph_flow.py
git commit -m "feat: scaffold langgraph workflow and roles"
```

---

### Task 3: Add API response summary for intermediate artifacts

**Files:**
- Modify: `services/agent-orchestrator/app/models/requests.py`
- Modify: `services/agent-orchestrator/app/api/workflows.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_api_response_intermediate.py`:

```python
from app.models.requests import LogAnalysisResponse


def test_response_has_intermediate_summary():
    response = LogAnalysisResponse(
        analysis_id="id",
        root_cause="rc",
        severity="high",
        suggested_fixes=["fix"],
        references=[],
        confidence=0.5,
        intermediate_summary={"diagnosis": "rc"},
    )
    assert response.intermediate_summary["diagnosis"] == "rc"
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_api_response_intermediate.py -v`

Expected: FAIL (field missing).

**Step 3: Write minimal implementation**

Update `services/agent-orchestrator/app/models/requests.py`:

```python
from typing import Any, Dict

class LogAnalysisResponse(BaseModel):
    ...
    intermediate_summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Summary of intermediate agent outputs",
    )
```

Update `services/agent-orchestrator/app/api/workflows.py` to populate `intermediate_summary` when returning `LogAnalysisResponse` (start with placeholders based on current analysis output).

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_api_response_intermediate.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/models/requests.py \
        services/agent-orchestrator/app/api/workflows.py \
        services/agent-orchestrator/tests/test_api_response_intermediate.py
git commit -m "feat: include intermediate summary in log analysis response"
```

---

### Task 4: Wire LangGraph flow into log analysis workflow

**Files:**
- Modify: `services/agent-orchestrator/app/api/workflows.py`
- Modify: `services/agent-orchestrator/app/application/use_cases/analyze_log.py`
- Modify: `services/agent-orchestrator/app/dependencies.py`

**Step 1: Write the failing test**

Create `services/agent-orchestrator/tests/test_langgraph_integration.py`:

```python
import asyncio

from app.workflows.langgraph_flow import run_langgraph


def test_langgraph_flow_executes():
    result = asyncio.get_event_loop().run_until_complete(
        run_langgraph({"log_content": "err", "log_type": "build", "context": {}})
    )
    assert "parsed" in result
    assert "diagnosis" in result
    assert "evidence" in result
    assert "remediation" in result
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_langgraph_integration.py -v`

Expected: FAIL if missing or not wired.

**Step 3: Write minimal implementation**

- Update AnalyzeLogUseCase to call `run_langgraph()` and map result into response DTO.
- Update dependencies to inject workflow dependencies if needed.
- Ensure response includes `intermediate_summary`.

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_langgraph_integration.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/api/workflows.py \
        services/agent-orchestrator/app/application/use_cases/analyze_log.py \
        services/agent-orchestrator/app/dependencies.py \
        services/agent-orchestrator/tests/test_langgraph_integration.py
git commit -m "feat: integrate langgraph flow into log analysis"
```

---

### Task 5: End-to-end workflow test with test-payload.json

**Files:**
- Create: `services/agent-orchestrator/tests/test_end_to_end_langgraph.py`

**Step 1: Write the failing test**

```python
import json
import asyncio

from app.workflows.langgraph_flow import run_langgraph


def test_end_to_end_langgraph_with_payload():
    with open("../../test-payload.json", "r", encoding="utf-8") as f:
        payload = json.load(f)
    result = asyncio.get_event_loop().run_until_complete(run_langgraph(payload))
    assert result["diagnosis"].root_cause_candidates
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_end_to_end_langgraph.py -v`

Expected: FAIL if path resolution or flow missing.

**Step 3: Write minimal implementation**

- Adjust test to resolve path correctly
- Ensure `run_langgraph` accepts the payload

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_end_to_end_langgraph.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add services/agent-orchestrator/tests/test_end_to_end_langgraph.py
git commit -m "test: add end-to-end langgraph workflow test"
```

---

### Task 6: Update documentation

**Files:**
- Modify: `README.md`
- Modify: `services/agent-orchestrator/APPLICATION_LAYER.md`

**Step 1: Write the failing doc test (manual)**

Ensure README and APPLICATION_LAYER mention the LangGraph workflow and intermediate summaries.

**Step 2: Implement docs updates**

- README: update Day11 status and mention LangGraph orchestration in features.
- APPLICATION_LAYER: add section describing LangGraph workflow integration.

**Step 3: Commit**

```bash
git add README.md services/agent-orchestrator/APPLICATION_LAYER.md
git commit -m "docs: document langgraph orchestration flow"
```

---

### Task 7: Full verification

**Steps:**
1. Run `pytest services/agent-orchestrator/tests -v`
2. Run `python -m py_compile` on new modules

**Commit (if needed for fixes):**

```bash
git add -A
git commit -m "test: verify langgraph workflow"
```
