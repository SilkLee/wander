# Week 3 Design — LangGraph Multi-Agent Orchestration (PR Risk + Code Review)

**Date**: 2026-03-12  
**Scope**: Week 3 (new multi-agent workflows, reuse Day 12 stability)

## 1) Goal
Add two new LangGraph workflows to demonstrate multi‑agent orchestration beyond build triage:
1) **PR Risk Assessment**
2) **Code Review Assistant**

Each workflow should reuse the existing stability layer (timeouts, retries, circuit breaker) and return a consistent response shape with `intermediate_summary` and `degraded` signals.

## 2) Non‑Goals
- No UI changes or dashboard work (Week 3 is backend only).
- No persistent workflow state or distributed execution.
- No breaking changes to existing APIs.

## 3) Recommended Approach
**A1: Two new LangGraph flows** with shared DTOs and roles:
- `pr_risk_flow.py`: PR risk assessment
- `code_review_flow.py`: Code review suggestions

**Why**: Fastest visible delivery, minimal risk, reuses Day 11/12 patterns and tests.

## 4) Architecture Overview
```
/workflows/execute
  ├─ workflow_type=pr_risk
  │    → diff_parser → risk_analyst → summarizer
  └─ workflow_type=code_review
       → diff_parser → reviewer → summarizer
```

Common behavior:
- Each node is wrapped by the stability layer (`run_with_retry`, circuit breaker).
- Errors are captured in `intermediate_summary.errors[]`.
- `degraded=true` when partial results are returned.

## 5) Components
1. **DTOs**
   - `PRRiskReport` (risk_level, impacted_areas, checks, rationale)
   - `ReviewComment` (file, line, severity, message, suggestion)
   - `ReviewSummary` (summary, comments[], severity_breakdown)

2. **Agents/Roles**
   - `diff_parser`: normalize diff + context
   - `risk_analyst`: risk scoring & impacted areas
   - `reviewer`: review comment generation
   - `summarizer`: final response + intermediate_summary

3. **Workflows**
   - `pr_risk_flow.py`
   - `code_review_flow.py`

4. **API**
   - `/workflows/execute` supports `workflow_type` = `pr_risk` | `code_review`.
   - Response remains compatible with `WorkflowExecutionResponse`.

## 6) Data Flow & Response Shape
- **PR Risk Assessment**
  - Input: `workflow_type=pr_risk`, `diff`, `context`
  - Output: `PRRiskReport`

- **Code Review**
  - Input: `workflow_type=code_review`, `diff`, `coding_standards`
  - Output: `ReviewSummary`

Unified response:
- `analysis`: top-level conclusion
- `intermediate_summary`: node outputs + `errors`/`retry_summary`/`degraded`

## 7) Error Handling
- Node-level failures are isolated; partial results are returned.
- Stability metadata captured in `intermediate_summary.errors[]`.
- Circuit breaker short-circuits repeated failures.

## 8) Testing Strategy
- DTO model validation tests for new review DTOs.
- Flow unit tests for each workflow.
- API test for `/workflows/execute` with each workflow_type.
- Regression: existing Day11/Day12 tests must pass.

## 9) Success Criteria
- Both workflows return valid outputs with stability metadata.
- API stays backward compatible.
- All tests (including existing ones) pass.
