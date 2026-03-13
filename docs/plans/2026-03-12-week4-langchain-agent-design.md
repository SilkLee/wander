# Week 4 Design — LangChain Agent Basics (Tooling Agent)

**Date**: 2026-03-12  
**Scope**: Week 4 (LangChain agent basics)

## 1) Goal
Implement a LangChain **tooling agent** that supports both:
- **B1 (basic)**: PR summary + risk highlights
- **B3 (extended)**: dependency risk + change impact analysis

The agent should reuse the stability layer and return consistent API output via `/workflows/execute`.

## 2) Non‑Goals
- No UI changes.
- No persistent memory or long-term conversation state.
- No production tool execution (read-only analysis only).

## 3) Approach Summary
Single tooling agent with a small toolset and deterministic output schema. The toolset is used in a standard call order, but is flexible to skip tools if inputs are missing.

## 4) Architecture & Components
**Agent**
- `app/agents/langchain_tools_agent.py`: LangChain agent entry, tool orchestration, output aggregation.

**Tools**
- `app/tools/repo_search_tool.py`: search files/paths/symbols
- `app/tools/dependency_scan_tool.py`: detect dependency changes and version risk
- `app/tools/impact_analysis_tool.py`: map diff to impacted modules/services

**DTOs**
- `app/models/agent_reports.py`: `PRSummary`, `RiskFinding`, `DependencyRisk`, `ImpactReport`

**API**
- `/workflows/execute` accepts `workflow_type=langchain_tool_agent`
- outputs in `WorkflowExecutionResponse` with `analysis`, `outputs`, `intermediate_summary`

## 5) Data Flow
1. **Repo Search Tool** → locate relevant files
2. **Dependency Scan Tool** → detect dependency changes
3. **Impact Analysis Tool** → assess affected modules/services

Response:
- `analysis`: concise summary
- `outputs`: structured DTOs
- `intermediate_summary`: tool outputs + errors/degraded/retry_summary

## 6) Error Handling
- Tool failures do not stop the agent; errors captured in `intermediate_summary.errors[]`.
- `degraded=true` when partial output is returned.
- Stability layer applied for timeouts/retries/circuit breaker.

## 7) Testing Strategy
- Unit tests for each tool
- Agent flow test for structured output and intermediate_summary
- API test for `/workflows/execute` with `workflow_type=langchain_tool_agent`
- Regression: existing tests must pass

## 8) Success Criteria
- Agent returns PR summary + risks + dependency + impact reports
- API response consistent with existing workflow response shape
- Full test suite passes
