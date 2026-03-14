# LangChain Classic Migration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove all `langchain_classic` usage and migrate to the latest LangChain APIs while preserving current agent behavior.

**Architecture:** Replace legacy agent imports with `langchain`/`langchain_core` equivalents, keep the executor configuration unchanged, and delete test shims that mock `langchain_classic`.

**Note:** Update LangChain dependency to the latest version before switching to `create_react_agent` (available in langchain>=0.3.x).

**Tech Stack:** Python 3.11, LangChain (latest), FastAPI, pytest

---

### Task 1: Replace legacy agent imports

**Files:**
- Modify: `services/agent-orchestrator/app/agents/base.py`
- Test: `services/agent-orchestrator/tests/test_langchain_tools_agent.py`

**Step 1: Write the failing test**

```python
def test_agent_executor_uses_langchain_agent_executor():
    from app.agents.base import BaseAgent
    assert BaseAgent
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_langchain_tools_agent.py -v`
Expected: FAIL due to import error for langchain_classic

**Step 3: Write minimal implementation**

```python
from langchain.agents import AgentExecutor, AgentType, create_react_agent
from langchain_core.tools import BaseTool

agent = create_react_agent(llm=self.llm, tools=tools, prompt=prompt)
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    max_iterations=self.max_iterations,
    verbose=True,
    return_intermediate_steps=True,
    handle_parsing_errors=create_lenient_parsing_error_handler(),
)
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_langchain_tools_agent.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/app/agents/base.py
git commit -m "refactor: migrate BaseAgent to latest langchain"
```

---

### Task 2: Remove `langchain_classic` test shims

**Files:**
- Modify: `services/agent-orchestrator/tests/test_workflow_execute_incident_response.py`
- Test: `services/agent-orchestrator/tests/test_workflow_execute_incident_response.py`

**Step 1: Write the failing test**

```python
def test_incident_response_execute_no_langchain_classic():
    import sys
    assert "langchain_classic" not in sys.modules
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_workflow_execute_incident_response.py -v`
Expected: FAIL because shim loads langchain_classic

**Step 3: Write minimal implementation**

```python
# Remove the langchain_classic shim and args-schema patch.
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_workflow_execute_incident_response.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add services/agent-orchestrator/tests/test_workflow_execute_incident_response.py
git commit -m "test: remove langchain_classic shim"
```

---

### Task 3: Update dependency expectations and verify full suite

**Files:**
- Modify: `services/agent-orchestrator/pyproject.toml`
- Test: `services/agent-orchestrator/tests/*`

**Step 1: Write the failing test**

```python
def test_no_langchain_classic_dependency():
    import importlib.util
    assert importlib.util.find_spec("langchain_classic") is None
```

**Step 2: Run test to verify it fails**

Run: `pytest services/agent-orchestrator/tests/test_health.py -v`
Expected: FAIL if langchain_classic still referenced

**Step 3: Write minimal implementation**

```toml
[project]
dependencies = [
  "langchain>=0.1.0",
  "langchain-openai>=0.0.5",
  "langchain-community>=0.0.20",
]
```

**Step 4: Run test to verify it passes**

Run: `pytest services/agent-orchestrator/tests/test_health.py -v`
Expected: PASS

**Step 5: Run full suite**

Run: `pytest services/agent-orchestrator/tests -v`
Expected: PASS (no langchain_classic errors)

**Step 6: Commit**

```bash
git add services/agent-orchestrator/pyproject.toml
git commit -m "chore: drop langchain_classic dependency"
```

---

**Plan complete and saved to `docs/plans/2026-03-14-langchain-classic-migration-implementation-plan.md`.** Two execution options:

**1. Subagent-Driven (this session)** – I dispatch fresh subagent per task, review between tasks, fast iteration  
**2. Parallel Session (separate)** – Open new session with executing-plans, batch execution with checkpoints

Which approach?
