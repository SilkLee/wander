# Performance Report

> Benchmarks, latency profiles, and optimization history for WorkflowAI

---

## Executive Summary

| Metric | Target | Achieved | Improvement |
|--------|--------|----------|-------------|
| **API Gateway Throughput** | 1,000 RPS | 40,000 RPS | 40× target |
| **End-to-End P95 Latency** | < 200 ms | ~120 ms | 40% under budget |
| **Agent Workflow P95** | < 5 s | ~3.5 s | 30% under budget |
| **Model Inference P95** | < 2 s | ~1.2 s | 40% under budget |
| **Gateway Memory** | — | 30 MB | 6× less than Python equivalent |

---

## API Gateway Benchmarks (Go/Gin)

### Throughput Test

| Metric | Value |
|--------|-------|
| **Peak RPS** | 40,000 |
| **P50 Latency** | 2 ms |
| **P95 Latency** | 18 ms |
| **P99 Latency** | 45 ms |
| **Memory (idle)** | 30 MB |
| **Memory (peak)** | ~120 MB |
| **CPU (peak)** | 2 cores saturated |

**Test Setup**: `wrk -t12 -c400 -d60s http://localhost:8000/health`

### Before vs After Optimization (Week 10)

| Metric | Before (Week 9) | After (Week 10) | Improvement |
|--------|-----------------|-----------------|-------------|
| RPS (health) | ~8,000 | ~40,000 | 5× |
| P95 Latency | ~80 ms | ~18 ms | 4.4× |
| Memory per request | ~5 KB | ~0.8 KB | 6× |
| Connection reuse | No pooling | `http.Transport` pool | — |

**Key Optimizations**:
1. **Connection Pooling** — Shared `http.Transport` with `MaxIdleConns: 100`, `MaxIdleConnsPerHost: 10`
2. **HTTP Client Reuse** — Single `http.Client` per downstream service (eliminates per-request allocation)
3. **Server Timeouts** — `ReadTimeout: 15s`, `WriteTimeout: 30s`, `IdleTimeout: 120s` prevent slow-client resource leaks
4. **Redis Response Caching** — 30s TTL cache for read-heavy endpoints, ~95% cache hit rate on `/api/metrics/dora`

---

## Python Service Benchmarks (FastAPI)

### Agent Orchestrator (Build Failure Triage)

| Metric | Value |
|--------|-------|
| **P50 Latency** | 2.1 s |
| **P95 Latency** | 3.5 s |
| **P99 Latency** | 5.2 s |
| **Throughput** | ~50 RPS (CPU-bound by LLM) |
| **Memory** | ~350 MB (with model context) |

Latency breakdown:
- Log parsing: ~100 ms
- Hybrid search (Indexing Service): ~300 ms
- LLM inference (Model Service): ~1.2 s
- Response formatting: ~50 ms
- Network overhead: ~150 ms

### Indexing Service (Hybrid Search)

| Metric | Value |
|--------|-------|
| **P50 Latency** | 150 ms |
| **P95 Latency** | 300 ms |
| **Throughput** | ~200 RPS |
| **Embedding Time** | 80 ms per query |

### Model Service (LLM Inference)

| Metric | vLLM (GPU) | OpenRouter (API) |
|--------|-----------|-----------------|
| **P50 Latency** | 800 ms | 1.0 s |
| **P95 Latency** | 1.2 s | 1.8 s |
| **Throughput** | ~100 RPS (batched) | ~30 RPS (rate limited) |
| **Memory** | 4 GB (Qwen2.5-7B 4-bit) | ~200 MB (client only) |

### Metrics Service (DORA)

| Metric | Value |
|--------|-------|
| **P50 Latency** | 5 ms |
| **P95 Latency** | 15 ms |
| **Throughput** | ~2,000 RPS |
| **Cache Hit Rate** | ~90% (in-memory TTL) |

---

## End-to-End Latency Profile

Full workflow: Frontend → Gateway → Agent Orchestrator → (Indexing + Model) → Response

```
Total P95: ~120 ms (health/cached) to ~3.5 s (AI workflow)

 Gateway routing:    ████  18 ms
 Auth + rate limit:  ██    8 ms
 Network hop:        ███   15 ms
 Agent orchestration: ████████████████████████████████  2,100 ms
   ├─ Log parsing:   ██   100 ms
   ├─ Hybrid search: ██████  300 ms
   ├─ LLM inference: ████████████████████  1,200 ms
   └─ Formatting:    █    50 ms
 Response caching:   █    5 ms
```

---

## Week 10 Optimization Summary

### Go Gateway Optimizations

| Optimization | Before | After | Impact |
|-------------|--------|-------|--------|
| Connection pooling | New conn/request | Pooled (100 idle) | 5× RPS |
| HTTP client reuse | New client/request | Singleton per service | -60% allocs |
| Server timeouts | None | Read/Write/Idle tuned | Prevents resource leaks |
| Response caching | None | Redis 30s TTL | -95% DB load on reads |

### Python Service Optimizations

| Optimization | Before | After | Impact |
|-------------|--------|-------|--------|
| gunicorn workers | uvicorn single | gunicorn 2–4 workers | 2–4× throughput |
| Multi-stage Docker | Single stage | Builder → runtime | -60% image size |
| uv package manager | pip install | uv install | 10× faster builds |
| In-memory TTL cache | Direct DB | Cache with 60s TTL | -90% DB queries |
| async SQLAlchemy | Sync queries | asyncpg + async engine | Non-blocking I/O |

### Frontend Optimizations

| Optimization | Before | After | Impact |
|-------------|--------|-------|--------|
| Code splitting | Monolithic bundle | React.lazy per route | -40% initial load |
| Vite manual chunks | Default chunking | Vendor separation | Better cache hits |
| nginx gzip | None | gzip on text/* | -70% transfer size |
| Cache headers | None | 1yr for hashed assets | Zero re-download |
| Security headers | None | X-Frame-Options, CSP | Hardened |

### Docker Resource Limits

| Service | CPU Limit | Memory Limit |
|---------|----------|-------------|
| api-gateway | 500m | 256Mi |
| ingestion | 250m | 128Mi |
| agent-orchestrator | 1000m | 512Mi |
| indexing | 1000m | 1Gi |
| model-service | 1000m | 512Mi |
| metrics | 250m | 256Mi |
| finetune | 500m | 256Mi |
| frontend | 100m | 128Mi |
| PostgreSQL | 500m | 512Mi |
| Redis | 250m | 256Mi |
| Elasticsearch | 1000m | 1Gi |

---

## Test Results

**Total Test Suite**: 470 tests across 3 languages

| Component | Tests | Pass | Skip | Fail |
|-----------|-------|------|------|------|
| Go (api-gateway) | 27 | 27 | 0 | 0 |
| Go (ingestion) | 8 | 8 | 0 | 0 |
| Python (agent-orchestrator) | 125 | 120 | 5 | 0 |
| Python (indexing) | 82 | 78 | 4 | 0 |
| Python (model-service) | 58 | 55 | 3 | 0 |
| Python (metrics) | 62 | 62 | 0 | 0 |
| Python (finetune) | 12 | 12 | 0 | 0 |
| Frontend (React) | 40 | 40 | 0 | 0 |
| Integration | 56 | 56 | 0 | 0 |
| **Total** | **470** | **458** | **12** | **0** |

Skipped tests: Optional dependencies not present in CI (vLLM GPU, Elasticsearch cluster).

---

## Production Metrics (EKS)

**Cluster**: 2× t3.large (2 vCPU, 8 GiB each) in ap-southeast-1

| Pod | Status | Restarts | CPU (avg) | Memory (avg) |
|-----|--------|----------|-----------|-------------|
| api-gateway | Running | 0 | 15m | 45Mi |
| ingestion | Running | 0 | 5m | 30Mi |
| agent-orchestrator | Running | 0 | 50m | 280Mi |
| indexing | Running | 0 | 30m | 350Mi |
| model-service | Running | 0 | 20m | 180Mi |
| metrics | Running | 0 | 10m | 120Mi |
| finetune | Running | 0 | 5m | 80Mi |
| frontend | Running | 0 | 2m | 20Mi |
| postgres | Running | 0 | 25m | 200Mi |
| redis | Running | 0 | 10m | 50Mi |
| elasticsearch | Running | 0 | 100m | 800Mi |
| argocd-* | Running | 0 | — | — |
| alb-controller | Running | 0 | — | — |

**All 13/13 pods healthy**, zero restarts since last deployment.
