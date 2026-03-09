# Day 11 Design — LangGraph Multi-Agent Orchestration (Build Failure Triage)

**Date**: 2026-03-09  
**Scope**: Day 11 only (no retries/persistence; Day 12 optimization later)

## 1) Goal
Introduce LangGraph-based multi-agent orchestration for **Build Failure Triage** with:
- 4 roles: **Parser → Diagnoser → Evidence Retriever → Remediator**
- **Structured intermediate artifacts** at each step
- **API response includes intermediate summary** (not full internals)

## 2) Non-Goals (Day 11)
- No retry/circuit breaker policies (reserved for Day 12)
- No persistence of intermediate artifacts
- No changes to request input schema

## 3) Approach (Selected)
**Sequential LangGraph workflow** with explicit node outputs and a final summarizer.

**Why**: Lowest implementation risk, preserves current RAG pipeline, and clearly demonstrates multi-agent collaboration with traceable outputs.

## 4) Architecture
```
Request(log_content)
  → ParserAgent → ParsedLog
  → DiagnoserAgent → Diagnosis
  → EvidenceRetrieverAgent → EvidenceBundle
  → RemediatorAgent → Remediation
  → FinalSummarizer → Response(summary + intermediate_summary)
```

## 5) Components
1. **LangGraph Workflow Definition**
   - Node order: Parser → Diagnoser → EvidenceRetriever → Remediator → FinalSummarizer
2. **Agent Roles (4)**
   - Parser: raw log → structured incident facts
   - Diagnoser: facts → root-cause hypotheses
   - Evidence Retriever: hypotheses → RAG evidence bundle
   - Remediator: hypotheses + evidence → fix steps
3. **DTOs for intermediate artifacts**
   - `ParsedLog`, `Diagnosis`, `EvidenceBundle`, `Remediation`
4. **FinalSummarizer**
   - Produces `summary` and `intermediate_summary`
5. **API Response Extension**
   - Adds `intermediate_summary` (preserves current input contract)

## 6) Data Contracts (Shape)
- **ParsedLog**: source, timestamps, error_signatures, stack_fragments, env
- **Diagnosis**: root_cause_candidates[], confidence, reasoning
- **EvidenceBundle**: citations[], snippets[], relevance_scores[]
- **Remediation**: steps[], risk_notes[], verification_commands[]

## 7) Error Handling
- **Node failure**: return DTO with `error_reason` and empty payload where possible
- **Workflow failure**: standardized API error response + `trace_id`
- **Validation**: all node outputs validated by Pydantic DTOs

## 8) Testing Strategy
- **Unit tests**: DTO validation + each agent output contract
- **Workflow test**: run full graph using `test-payload.json`
- **Regression**: ensure `/analyze-log` input remains unchanged

## 9) Success Criteria
- End-to-end LangGraph workflow runs for `test-payload.json`
- API response includes `summary` and `intermediate_summary`
- All node outputs validated and traceable
