# Day 12 Stability Optimization Design

## Goal
Improve reliability of the Day 11 LangGraph multi-agent workflow for Build Failure Triage by adding timeouts, retries, and graceful degradation without changing core functionality.

## Scope
- Add node-level timeout and retry behavior for LangGraph roles (Parser, Diagnoser, Evidence Retriever, Remediator).
- Provide fallback/partial results on failure instead of failing the entire API response.
- Introduce a lightweight circuit breaker option to short‑circuit repeated failures and return a degraded response.
- Capture structured error metadata in `intermediate_summary`.

Out of scope:
- Changes to model quality, prompt engineering, or retrieval accuracy.
- Persistent state or distributed orchestration.

## Recommended Approach
**Minimal stability layer** around the existing LangGraph flow:
1. **Node timeouts + retries** (exponential backoff) for each role.
2. **Failure isolation** to preserve already-produced intermediate data.
3. **Optional circuit breaker** for repeat failures with a simplified fallback path.

## Architecture Overview
The workflow stays the same; reliability is added via wrappers:

```
analyze_log → AnalyzeLogUseCase → langgraph.run
  └─ parse_log   (timeout + retry + error capture)
  └─ diagnose    (timeout + retry + error capture)
  └─ retrieve    (timeout + retry + error capture)
  └─ remediate   (timeout + retry + error capture)
```

When a node fails:
- Record error details into `intermediate_summary.errors[]`.
- Continue returning whatever data was already generated.
- If circuit breaker is open, skip the failing node(s) and return a degraded response.

## Data Flow & Response Shape
Add the following keys to `intermediate_summary`:
- `errors`: list of `{node, error_type, message, retry_attempts, degraded}`
- `degraded`: boolean (overall)
- `retry_summary`: `{node: attempts}`

If a node fails, the API response still includes:
- Base analysis output (root cause, severity, confidence, suggestions)
- Partial `intermediate_summary` for completed nodes

## Error Classification
Standardize error types:
- `timeout`
- `dependency`
- `validation`
- `unknown`

Classification is used for reporting and circuit-breaker thresholds.

## Circuit Breaker (Lightweight)
An in-memory counter per node:
- Opens after N consecutive failures within a window.
- While open, skip the node and mark `degraded=true`.
- Closes after a cool‑down period or a successful run.

This keeps scope small while improving reliability under repeated failures.

## Testing Strategy
- Unit tests for retry/timeout behavior and error classification.
- Integration tests that simulate node failure and confirm API response still returns.
- Regression: existing Day11 tests must still pass.

## Risks & Mitigations
- **Risk**: excessive retries increase latency.  
  **Mitigation**: short timeouts, low retry limits, and circuit-breaker early exit.
- **Risk**: degraded responses confuse users.  
  **Mitigation**: expose `degraded` and `errors` in `intermediate_summary` for clarity.

## Success Criteria
- API returns successfully even when one LangGraph node fails.
- `intermediate_summary` includes structured error metadata.
- Existing Day11 integration tests still pass.
- New stability tests pass (timeouts/retries/fallbacks).
