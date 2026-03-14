# Week 6 Design — Advanced RAG (Hybrid Search + Reranking)

**Date**: 2026-03-14  \
**Scope**: Week 6 (Advanced RAG)

## 1) Goal
Add **reranking on top of existing hybrid retrieval** to improve result relevance. Rerank runs in **Indexing** by default, with **optional secondary rerank** in Agent‑orchestrator for critical flows (PR risk, code review).

## 2) Non‑Goals
- No changes to how documents are indexed or embedded.
- No replacement of hybrid search strategy (BM25 + vector fusion stays).
- No UI changes.

## 3) Chosen Approach
**Primary rerank in Indexing** + **secondary rerank in Agent‑orchestrator (key flows only)**. This preserves centralized retrieval behavior while allowing quality boosts in critical workflows.

## 4) Architecture Overview
1) **Indexing Service**
   - Hybrid retrieval returns a candidate pool (top_k * 2).
   - Rerank candidates using **BAAI/bge‑reranker‑base**.
   - Response includes `reranked=true` + `rerank_model` metadata.

2) **Agent‑orchestrator (key flows only)**
   - When flow in {PR risk, code review}, run a **secondary rerank** on top_k results.
   - Mark results with `secondary_reranked=true`.

## 5) Data Flow
1) Query → Indexing `/search`
2) Hybrid retrieval → candidate pool
3) Rerank → return ordered results + metadata
4) Agent‑orchestrator optionally reranks for key flows

## 6) API/Schema Changes (Indexing)
**SearchResponse additions (backwards compatible):**
- `reranked: bool`
- `rerank_model: Optional[str]`

## 7) Error Handling
- **Indexing rerank failure** → return hybrid order, `reranked=false`.
- **Secondary rerank failure** → keep Indexing order, `secondary_reranked=false`.

## 8) Configuration
- `INDEXING_RERANK_ENABLED`
- `RERANK_MODEL_NAME` (default: `BAAI/bge-reranker-base`)
- `SECONDARY_RERANK_ENABLED`
- `SECONDARY_RERANK_TARGETS = [pr_risk, code_review]`

## 9) Testing Strategy
- **Indexing**: rerank changes order; fallback on model error.
- **Agent‑orchestrator**: secondary rerank only for key flows.
- **Contract**: SearchResponse includes new fields; older callers still work.

## 10) Success Criteria
- Reranked results demonstrably improve relevance vs hybrid-only.
- No regressions for non‑critical flows.
- Clear metadata indicating rerank status.
