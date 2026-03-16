# Technology Stack Selection

> Design rationale for WorkflowAI's polyglot Go + Python architecture

---

## Strategic Decision: Why Two Languages?

WorkflowAI separates **network I/O** (Go) from **AI compute** (Python) based on measured requirements, not preference.

| Concern | Go | Python | Winner |
|---------|-----|--------|--------|
| HTTP throughput | 40,000 RPS (Gin) | ~8,000 RPS (FastAPI/uvicorn) | Go — 5× |
| Memory footprint | 30 MB per instance | 180 MB per instance | Go — 6× |
| AI/ML ecosystem | Minimal (no LangChain, no vLLM) | LangChain, vLLM, Transformers, PEFT | Python |
| Cold start | < 100 ms | 2–5 s (model loading) | Go |
| Concurrency model | Goroutines (M:N) | asyncio + gunicorn workers | Go |
| Developer velocity for ML | Poor | Excellent | Python |

**Conclusion**: A single-language approach would either sacrifice 5× network performance (all-Python) or give up the entire AI ecosystem (all-Go). The polyglot boundary adds ~30–40 hours of overhead across 12 weeks — acceptable for 5× throughput gains.

---

## Go Layer: Network Services

### API Gateway (`services/api-gateway`)

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Framework | Gin | 1.9.1 | Fastest Go HTTP framework, middleware ecosystem |
| Auth | JWT (golang-jwt) | v5 | Stateless auth, no session DB required |
| Rate Limiting | Redis + token bucket | - | Distributed rate limiting across replicas |
| Caching | Redis TTL cache | - | 30s response cache for read-heavy endpoints |
| Architecture | Clean Architecture | - | Domain/interfaces/infrastructure separation |

**Key Design Choices:**
- Connection pooling with `http.Transport` reuse — eliminates per-request TCP overhead
- `ReadTimeout: 15s`, `WriteTimeout: 30s`, `IdleTimeout: 120s` — tuned server timeouts
- Reverse proxy to downstream Python services via `httputil.ReverseProxy`

### Ingestion Service (`services/ingestion`)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Framework | Gin | Consistent with Gateway |
| Queue | Redis Streams | Durable, consumer-group fan-out |
| Serialization | JSON | Interop with Python consumers |

**Why Redis Streams over Kafka?** At our scale (~100 events/sec), Redis Streams provides ordered, durable message delivery with consumer groups — without Kafka's operational complexity (ZooKeeper, partition management). Single Redis instance handles both rate limiting and streaming.

---

## Python Layer: AI Services

### Agent Orchestrator (`services/agent-orchestrator`)

| Component | Technology | Version | Rationale |
|-----------|-----------|---------|-----------|
| Framework | FastAPI | ≥0.109.0 | Async-first, OpenAPI generation |
| Orchestration | LangChain | ≥0.3.0 | Chain composition, memory, tool use |
| Multi-Agent | LangGraph | 0.0.20 | State-machine workflows (Build Triage, Incident Response) |
| LLM Client | langchain-openai | ≥0.3.0 | OpenRouter/OpenAI API compatibility |
| Search | Elasticsearch | 8.11 | BM25 + vector hybrid retrieval |

**4 AI Workflows:**

1. **Build Failure Triage** — RAG retrieval → LLM root-cause analysis → fix suggestions
2. **PR Risk Assessment** — Feature extraction → ML risk scoring → recommendations
3. **Code Review Assistant** — Diff parsing → LLM review → issue categorization
4. **Incident Response** — LangGraph multi-agent (Triage → Diagnosis → Remediation → Report)

### Indexing Service (`services/indexing`)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Embeddings | Sentence Transformers 2.2.2 | Local inference, no API cost |
| Vector Store | Faiss 1.7.4 | Fast approximate nearest neighbor |
| Text Search | Elasticsearch 8.11 | BM25 keyword retrieval |
| Hybrid | RRF (Reciprocal Rank Fusion) | Combines BM25 + dense vector scores |

### Model Service (`services/model-service`)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Inference | vLLM 0.2.6 (prod) / OpenRouter (EKS) | PagedAttention for throughput; OpenRouter when GPU unavailable |
| Fine-tuning | PEFT 0.7.0 (LoRA) | 4-bit QLoRA on Qwen2.5-7B, trains on single GPU |
| Tokenizer | SentencePiece | Qwen2.5 tokenization |

**Production Note**: On t3.large EKS nodes (no GPU), model-service uses OpenRouter's free tier as a drop-in replacement. The vLLM path is used on GPU-equipped instances.

### Metrics Service (`services/metrics`)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| ORM | SQLAlchemy 2.0 (async) | Async PostgreSQL via asyncpg |
| Caching | In-memory TTL cache | Reduce DB queries for dashboard |
| Schema | Pydantic v2 | Request/response validation |

---

## Infrastructure

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Container Runtime | Docker | 24.0 | Standard containerization |
| Local Orchestration | Docker Compose | 2.20+ | Full-stack local dev (11 services) |
| Production Orchestration | Kubernetes (EKS) | 1.28 | Horizontal scaling, self-healing |
| GitOps | ArgoCD | 2.x | Automated sync + prune + selfHeal |
| IaC | Terraform | 1.x | VPC, EKS, ECR ×8, IAM OIDC/IRSA |
| CI | GitHub Actions | - | Matrix: Go ×2, Python ×4, Frontend |
| CD | GitHub Actions → ArgoCD | - | ECR push → kustomize tag update → auto-sync |
| Manifests | Kustomize | - | Base + overlay (dev/production) |
| Monitoring | Prometheus + Grafana | - | Metrics scraping + dashboards |
| Tracing | OpenTelemetry + Jaeger | - | Distributed trace propagation |
| Database | PostgreSQL | 15 | DORA metrics, structured data |
| Cache/Queue | Redis | 7 | Rate limiting, response caching, Streams |

---

## Build System

| Service Type | Build Tool | Package Manager |
|-------------|-----------|-----------------|
| Go services | `go build` (multi-stage Docker) | Go modules |
| Python services | hatchling (multi-stage Docker) | pip + pyproject.toml |
| Frontend | Vite | npm |

All Python services use `pyproject.toml` with hatchling — no `requirements.txt`. Multi-stage Docker builds minimize image size (base → builder → runtime).

---

## Version Matrix

| Dependency | Pinned Version | Notes |
|-----------|---------------|-------|
| Go | 1.22+ | Minimum for gateway/ingestion |
| Python | 3.11+ (AI), 3.9+ (metrics) | Metrics supports older Python for compat |
| Node.js | 18+ | Frontend build |
| PostgreSQL | 15 | Async driver: asyncpg |
| Redis | 7 | Streams + rate limiting |
| Elasticsearch | 8.11 | Pinned <9.0 to avoid API v9 breaking changes |
| pytest-asyncio | ≥0.23, <1.0 | 1.x line breaks async test fixtures |
| torch | ≥2.1, <2.6 | Sentence Transformers compatibility |

---

## Overhead Analysis

**Polyglot Cost** (estimated across 12 weeks):

| Item | Hours |
|------|-------|
| Cross-language integration (HTTP contracts) | 10 |
| Dual CI pipeline (Go + Python matrix) | 8 |
| Dual Docker build patterns | 6 |
| Mental context switching | 8 |
| Debugging cross-service issues | 8 |
| **Total Overhead** | **~40h** |

**Polyglot Benefit**:
- 5× API throughput (40k vs 8k RPS)
- 6× memory efficiency at the network edge
- Access to full Python AI/ML ecosystem
- Independent scaling of compute-heavy vs I/O-heavy services

**Net Assessment**: 40 hours is ~15% of the 250–300 hour budget. The 5× throughput improvement and ecosystem access justify the cost.
