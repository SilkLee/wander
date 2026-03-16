# Architecture Deep-Dive

> System design, service topology, data flow, and key architecture decisions for WorkflowAI

---

## System Overview

WorkflowAI is a microservices platform with 8 backend services, a React frontend, and supporting infrastructure (PostgreSQL, Redis, Elasticsearch). It runs on AWS EKS with ArgoCD GitOps.

```
                    ┌──────────────────┐
                    │   React Frontend │ :3000
                    │  (nginx + Vite)  │
                    └────────┬─────────┘
                             │ HTTP
                    ┌────────▼─────────┐
                    │   API Gateway    │ :8000  (Go/Gin)
                    │  JWT · Rate Limit│
                    │  Cache · CORS    │
                    └──┬───┬───┬───┬───┘
           ┌───────────┤   │   │   └──────────────┐
           ▼           ▼   ▼   ▼                  ▼
    ┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌────────┐
    │Ingestion │ │ Agent  │ │Indexing│ │  Model   │ │Metrics │
    │  :8001   │ │Orchestr│ │ :8003  │ │ Service  │ │ :8005  │
    │  (Go)    │ │ :8002  │ │(Python)│ │  :8004   │ │(Python)│
    └────┬─────┘ │(Python)│ └───┬────┘ │ (Python) │ └───┬────┘
         │       └───┬────┘     │      └──────────┘     │
         │           │          │                        │
    ┌────▼────┐  ┌───▼──────▼──┐                  ┌─────▼─────┐
    │  Redis  │  │Elasticsearch│                  │PostgreSQL │
    │ Streams │  │   (Hybrid)  │                  │  (DORA)   │
    │ + Cache │  │  BM25+Dense │                  └───────────┘
    └─────────┘  └─────────────┘
```

---

## Service Catalog

| Service | Language | Port | Responsibility | Scaling Strategy |
|---------|----------|------|---------------|-----------------|
| **api-gateway** | Go (Gin) | 8000 | Auth, rate limiting, caching, reverse proxy | HPA on CPU (handles 40k RPS) |
| **ingestion** | Go (Gin) | 8001 | Webhook intake, event normalization, Redis Streams publish | HPA on queue depth |
| **agent-orchestrator** | Python (FastAPI) | 8002 | LangChain/LangGraph AI workflow execution | HPA on CPU (compute-bound) |
| **indexing** | Python (FastAPI) | 8003 | Vector embeddings, hybrid search (BM25 + dense) | HPA on CPU |
| **model-service** | Python (FastAPI) | 8004 | LLM inference (vLLM/OpenRouter), fine-tune serving | Vertical (GPU) or horizontal |
| **metrics** | Python (FastAPI) | 8005 | DORA metrics calculation, event recording, dashboards | HPA on requests |
| **finetune** | Python (FastAPI) | 8006 | LoRA fine-tuning job management | Single replica (batch) |
| **frontend** | React (nginx) | 3000 | Dashboard UI for all workflows + DORA metrics | Static, CDN-cacheable |

---

## Data Flow: AI Workflows

### Build Failure Triage (RAG Pipeline)

```
CI Log → API Gateway → Agent Orchestrator
                           │
                           ├── 1. Parse log → extract error patterns
                           ├── 2. Query Indexing Service (hybrid search)
                           │      └── BM25 + dense vector → RRF merge
                           ├── 3. Build prompt with retrieved context
                           ├── 4. Call Model Service (LLM inference)
                           │      └── Qwen2.5 via vLLM/OpenRouter
                           └── 5. Return: root cause + fix steps + refs
```

### Incident Response (LangGraph Multi-Agent)

```
Incident Alert → API Gateway → Agent Orchestrator
                                    │
                     ┌──── LangGraph State Machine ────┐
                     │                                  │
                     ▼                                  │
               ┌──────────┐                             │
               │  Triage   │ → severity + category      │
               └─────┬─────┘                             │
                     ▼                                  │
               ┌──────────┐                             │
               │ Diagnosis │ → root cause analysis      │
               └─────┬─────┘                             │
                     ▼                                  │
               ┌──────────┐                             │
               │Remediation│ → fix recommendations      │
               └─────┬─────┘                             │
                     ▼                                  │
               ┌──────────┐                             │
               │  Report   │ → structured JSON output   │
               └───────────┘                             │
                     │                                  │
                     └──────────────────────────────────┘
```

### DORA Metrics Flow

```
Git Push / CI Event / Deployment
        │
        ▼
  API Gateway ──► Metrics Service
                       │
                       ├── Record deployment event (POST /api/metrics/events/deployment)
                       ├── Record change event     (POST /api/metrics/events/change)
                       ├── Record incident event   (POST /api/metrics/events/incident)
                       │
                       ▼
                  PostgreSQL
                       │
                       ▼
                  DORA Calculator
                       │
                       ├── Deployment Frequency
                       ├── Lead Time for Changes
                       ├── Change Failure Rate
                       └── Mean Time to Recovery (MTTR)
                       │
                       ▼
                  React Dashboard (GET /api/metrics/dora)
```

---

## Infrastructure Architecture (AWS EKS)

```
┌─────────────────── AWS ap-southeast-1 ───────────────────┐
│                                                           │
│  VPC (10.0.0.0/16)                                        │
│  ├── Public Subnets (3 AZs) ── ALB Ingress Controller    │
│  └── Private Subnets (3 AZs)                              │
│       │                                                   │
│       ▼                                                   │
│  EKS Cluster (v1.28)                                       │
│  ├── 2× t3.large nodes (managed node group)               │
│  ├── Namespace: workflowai                                 │
│  │   ├── 8 service Deployments                             │
│  │   ├── PostgreSQL StatefulSet + PVC                      │
│  │   ├── Redis StatefulSet + PVC                           │
│  │   ├── Elasticsearch StatefulSet + PVC                   │
│  │   └── ALB Ingress (path-based routing)                  │
│  ├── Namespace: argocd                                     │
│  │   └── ArgoCD (app-of-apps pattern)                      │
│  ├── Namespace: kyverno                                    │
│  │   └── Kyverno (policy engine, Enforce mode)             │
│  └── Namespace: monitoring                                 │
│       └── kube-prometheus-stack (Prometheus + Grafana)      │
│                                                           │
│  ECR (8 repositories)                                      │
│  ├── api-gateway, ingestion, agent-orchestrator            │
│  ├── indexing, model-service, metrics                       │
│  ├── finetune, frontend                                    │
│                                                           │
│  IAM                                                       │
│  ├── OIDC Provider (GitHub Actions federation)             │
│  └── IRSA Roles (pod-level AWS permissions)                │
│                                                           │
│  S3 + DynamoDB (Terraform state backend)                   │
└───────────────────────────────────────────────────────────┘
```

---

## Architecture Decision Records (ADRs)

### ADR-1: Polyglot Go + Python

**Context**: Need high-throughput API layer AND access to Python AI/ML ecosystem.

**Decision**: Go for network services (Gateway, Ingestion), Python for AI services.

**Consequence**: 5× throughput at the edge, full LangChain/vLLM access in AI layer. ~40h cross-language overhead across 12 weeks.

### ADR-2: Redis Streams over Kafka

**Context**: Need durable message queue for event processing between ingestion and AI services.

**Decision**: Redis Streams with consumer groups.

**Consequence**: Simpler ops (single Redis for caching + rate limiting + streaming). Sufficient at our scale (~100 events/sec). Would need Kafka at 10k+ events/sec.

### ADR-3: Kustomize over Helm for Application Manifests

**Context**: Need K8s manifest management. Helm is standard but introduces template complexity.

**Decision**: Kustomize for application manifests (base + overlays). Helm only for 3rd-party tools (ALB Controller, ArgoCD, Prometheus).

**Consequence**: Plain YAML manifests are easier to review in PRs. ArgoCD natively supports Kustomize. No Helm chart maintenance for our own services.

### ADR-4: ArgoCD GitOps with selfHeal

**Context**: Need automated deployment from git changes.

**Decision**: ArgoCD with `automated.selfHeal: true` — any manual `kubectl` changes get reverted to match git.

**Consequence**: Git is the single source of truth. All changes must go through git commits. Direct `kubectl patch` is not persistent (learned the hard way with ConfigMaps).

### ADR-5: OpenRouter Fallback for Model Service

**Context**: t3.large EKS nodes have no GPU. vLLM requires GPU for inference.

**Decision**: Model service supports both vLLM (GPU) and OpenRouter (API) backends. EKS uses OpenRouter's free tier.

**Consequence**: AI workflows function on CPU-only nodes. Production GPU deployment would switch to vLLM for lower latency and no API dependency.

### ADR-6: Monorepo Structure

**Context**: 8 services + frontend + infra could be separate repos.

**Decision**: Single monorepo with `services/`, `frontend/`, `infra/`, `k8s/` directories.

**Consequence**: Atomic commits across services, single CI pipeline, easier cross-service refactoring. Trade-off: larger clone, broader CI triggers (mitigated with path-based CI filters).

### ADR-7: Kyverno Policy Engine (Enforce Mode)

**Context**: Need admission control to enforce pod security standards, image provenance, and resource governance across the `workflowai` namespace.

**Decision**: Kyverno in Enforce mode with 6 ClusterPolicies, managed via ArgoCD GitOps. Scoped to `workflowai` namespace only.

**Consequence**: Non-compliant pods are rejected at admission time. All existing manifests already comply (verified pre-enforcement). Policy changes follow the same git → ArgoCD flow as application changes.

---

## Security Model

| Layer | Mechanism |
|-------|----------|
| External → Gateway | ALB Ingress (HTTPS termination) |
| Gateway → Services | JWT authentication (internal network) |
| Rate Limiting | Redis token bucket (configurable RPS per client) |
| Secrets | Kubernetes Secrets (no hardcoded values in manifests) |
| IAM | IRSA (pod-level AWS permissions via OIDC) |
| CI/CD Auth | GitHub OIDC federation (no long-lived AWS keys) |
| Admission Control | Kyverno (6 policies, Enforce mode — reject non-compliant pods) |

**Public Routes** (no JWT): Frontend-facing workflow endpoints (`/api/v1/workflows/*`, `/api/metrics/*`) are rate-limited but not JWT-protected, as the React frontend has no auth layer.

**Protected Routes** (JWT required): All `/api/v1/*` endpoints require Bearer token. Admin routes additionally require admin role claim.

---

## Observability

| Signal | Tool | Collection |
|--------|------|-----------|
| Metrics | Prometheus | Service `/metrics` endpoints, kube-state-metrics |
| Dashboards | Grafana | Pre-configured via kube-prometheus-stack |
| Traces | Jaeger | OpenTelemetry SDK propagation |
| Logs | stdout/stderr | CloudWatch via Fluent Bit (EKS) |
| Alerts | Prometheus Alertmanager | CPU, memory, error rate thresholds |
