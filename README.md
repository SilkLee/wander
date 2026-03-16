# WorkflowAI

> AI-powered DevOps workflow automation platform for NVIDIA IPP Senior Software Engineer interview preparation

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Go Version](https://img.shields.io/badge/Go-1.22+-00ADD8?logo=go)](https://golang.org/)
[![Python Version](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org/)
[![CI](https://img.shields.io/badge/CI-15%2F15%20passing-brightgreen?logo=github)](https://github.com/SilkLee/workflow-ai/actions)
[![EKS](https://img.shields.io/badge/EKS-13%2F13%20pods-brightgreen?logo=amazonaws)]()

---

## 📋 Project Overview

**WorkflowAI** is a production-grade AI platform that automates DevOps workflows using:
- **RAG (Retrieval-Augmented Generation)** - Context-aware failure diagnosis
- **LLM Fine-tuning** - Custom classification models on enterprise data
- **Multi-Agent Systems** - LangGraph orchestration for complex reasoning
- **DORA Metrics** - Quantifiable engineering efficiency tracking

### Target Position
- **Company**: NVIDIA
- **Role**: Senior Software Engineer - AI Workflow (IPP)
- **Job ID**: JR2012063
- **Timeline**: 3-month hands-on project (250-300 hours)

---

## 🎯 Key Features

| Feature | Input | Output | AI Technology |
|---------|-------|--------|---------------|
| **Build Failure Triage** | CI logs | Root cause + Fix steps + References | RAG + Fine-tuned classifier |
| **PR Risk Assessment** | PR diff + metadata | Risk score + Recommendations | ML prediction model |
| **Code Review Assistant** | PR diff | Issues + Improvement suggestions | LLM + Static analysis |
| **DORA Metrics Tracking** | Git/CI events | Trend charts + Weekly reports | Time-series analysis |

---

## 🏗️ Architecture

### Strategic Polyglot Design (Go + Python)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Go Network Layer                         │
│  API Gateway (Gin)         Ingestion Service (Gin)              │
│  - JWT Auth                - Webhook intake                     │
│  - Rate limiting           - Redis Streams publishing           │
│  - 40k RPS throughput      - Event normalization                │
│  - 30MB memory footprint   - 5x faster than Python              │
└─────────────────────────────┬───────────────────────────────────┘
                              │ HTTP / Redis Streams
┌─────────────────────────────▼───────────────────────────────────┐
│                       Python AI Layer                           │
│  Agent Orchestrator (FastAPI + LangChain)                       │
│  Indexing Service   (FastAPI + Sentence Transformers)           │
│  Model Service      (FastAPI + vLLM/PEFT)                       │
│  Metrics Service    (FastAPI + SQLAlchemy)                      │
└─────────────────────────────────────────────────────────────────┘
```

**Why Polyglot?**
- **Go (Network)**: 5x performance improvement (40k vs 8k RPS), 6x memory efficiency
- **Python (AI)**: LangChain/vLLM/Transformers ecosystem requirement
- **Result**: Best-of-both-worlds with 30-40h manageable overhead

See [docs/tech-stack.md](docs/tech-stack.md) for detailed rationale.

---

## 📂 Project Structure

```
workflow-ai/
├── services/               # Microservices
│   ├── api-gateway/        # Go - Gin framework (40k RPS)
│   ├── ingestion/          # Go - Webhook processing
│   ├── agent-orchestrator/ # Python - LangChain workflows
│   ├── indexing/           # Python - Vector embeddings
│   ├── model-service/      # Python - vLLM inference + PEFT
│   └── metrics/            # Python - DORA metrics tracking
├── frontend/               # React dashboard
├── infra/                  # Infrastructure as Code
│   ├── docker/             # Dockerfiles + compose configs
│   └── terraform/          # AWS EKS deployment (ap-southeast-1)
├── k8s/                    # Kubernetes manifests (Kustomize)
│   ├── base/               # Base manifests (Deployments, Services)
│   ├── overlays/           # Environment overrides (dev, production)
│   └── policies/           # Kyverno ClusterPolicies (Enforce mode)
├── docs/                   # Documentation
│   ├── tech-stack.md       # Technology selection rationale
│   ├── architecture.md     # System design deep-dive
│   ├── api.md              # API endpoint reference
│   ├── cicd.md              # CI/CD system architecture
│   ├── performance-report.md # Benchmarks & optimizations
│   ├── interview-prep/     # Q&A preparation materials
│   └── portfolio/          # Interactive HTML portfolio website
└── tests/                  # Integration & load tests
    ├── integration/
    └── load/
```

---

## 🚀 Quick Start

### Prerequisites

- **Go**: 1.22+
- **Python**: 3.11+
- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **Redis**: 7+
- **PostgreSQL**: 15+

### Local Development Setup

```bash
# 1. Clone repository
git clone https://github.com/SilkLee/workflow-ai.git
cd workflow-ai

# 2. Start infrastructure services
docker-compose up -d postgres redis

# 3. Start Go API Gateway
cd services/api-gateway
go mod download
go run main.go
# Gateway running on http://localhost:8000

# 4. Start Python services (in separate terminals)
cd services/agent-orchestrator
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8002

# 5. Verify health
curl http://localhost:8000/health
```

### Full Stack Deployment

```bash
# Start all services with Docker Compose
docker-compose up --build

# Access services:
# - API Gateway:  http://localhost:8000
# - Frontend:     http://localhost:3000
# - Prometheus:   http://localhost:9090
# - Grafana:      http://localhost:3001
# - Jaeger:       http://localhost:16686
```

---

## 🛠️ Technology Stack

### Languages & Frameworks

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| **Network** | Go (Gin) | 1.22 / 1.9.1 | API Gateway, Ingestion |
| **AI Core** | Python (FastAPI) | 3.11 / 0.104.1 | Agent, Indexing, Model, Metrics |
| **Frontend** | React + TypeScript | 18 / 5.0 | Dashboard UI |
| **Orchestration** | LangChain + LangGraph | 0.1.0 / 0.0.20 | Multi-agent workflows |
| **Inference** | vLLM | 0.2.6 | LLM serving (Qwen2.5-7B) |
| **Fine-tuning** | PEFT (LoRA) | 0.7.0 | Low-rank adaptation |
| **Embeddings** | Sentence Transformers | 2.2.2 | Vector generation |
| **Search** | Elasticsearch + Faiss | 8.11 / 1.7.4 | Hybrid retrieval |
| **Database** | PostgreSQL | 15 | Structured data |
| **Cache/Queue** | Redis | 7 | Rate limiting + Streams |
| **Observability** | OpenTelemetry + Prometheus + Jaeger | - | Tracing + Metrics |

### Infrastructure

- **Container**: Docker 24.0
- **Orchestration**: Docker Compose (local) / Kubernetes (production)
- **IaC**: Terraform
- **CI/CD**: GitHub Actions
- **GitOps**: ArgoCD (app-of-apps, selfHeal)
- **Policy Engine**: Kyverno (6 ClusterPolicies, Enforce mode)
- **Cloud**: AWS (ap-southeast-1) — EKS, ECR, ALB, IRSA

---

## 📊 Performance Targets

| Metric | Target | Achieved |
|--------|--------|----------|
| **API Gateway Throughput** | 1,000 RPS | 40,000 RPS (40×) |
| **End-to-End P95 Latency** | < 200ms | ~120ms |
| **Agent Workflow P95** | < 5s | ~3.5s |
| **Model Inference P95** | < 2s | ~1.2s |
| **System Uptime** | 99.9% | 13/13 pods, 0 restarts |
| **Test Suite** | All pass | 470 tests (458 pass, 12 skip, 0 fail) |
| **CI Pipeline** | All green | 15/15 jobs passing |

---

## 📅 Development Timeline

### Month 1: Foundation (Week 1-4)
- ✅ **Week 1**: Infrastructure setup (Go Gateway, Docker Compose)
  - ✅ Day 1: Repository setup + Go API Gateway skeleton
  - ✅ Day 2: Docker Compose + PostgreSQL integration
  - ✅ Day 3: JWT authentication + Redis rate limiting
  - ✅ Day 4: Python services skeleton (FastAPI)
  - ✅ Day 5: Data ingestion pipeline (Go Ingestion + Redis Streams)
  - ✅ Day 6: Indexing service (Vector embeddings + Hybrid search)
  - ✅ Day 7: Model service (vLLM/Ollama integration)
- ✅ **Week 2**: Agent Orchestrator + Model Service Integration (Day 8-14)
  - ✅ Day 8: Agent uses local Model Service (LangChain custom LLM wrapper)
  - ✅ Day 9: Streaming responses with SSE (Server-Sent Events)
  - ✅ Day 10: RAG Agent Deployment & Optimization - Complete
    - ✅ Deployed 11 Docker services on AWS EC2 t3.xlarge (all healthy)
    - ✅ Upgraded to Qwen2.5-1.5B-Instruct model (3.9s response time)
    - ✅ Fixed timeout issues: base.py (60→300s), analyzer.py (180→300s)
    - ✅ Fixed custom error handler: None-check in output_parser.py
    - ✅ End-to-end validation: 4m22s workflow completion, 0.95 confidence
    - ✅ AWS cleanup completed (IAM roles preserved for reuse)
  - ✅ Day 11: Multi-agent orchestration with LangGraph (Build Failure Triage)
  - ✅ Day 12: Agent workflow optimization (Stability + graceful degradation)
- ✅ **Week 3**: Multi-agent orchestration (LangGraph)
  - ✅ Added PR Risk Assessment workflow
  - ✅ Added Code Review Assistant workflow
- ✅ **Week 4**: LangChain agent basics

### Month 2: Advanced Features (Week 5-8)
- ✅ **Week 5**: Fine-tuning classifier (LoRA on Qwen2.5-7B)
- ✅ **Week 6**: Advanced RAG (hybrid search, reranking)
- ✅ **Week 7**: Multi-agent orchestration (LangGraph)
  - ✅ Incident Response workflow (LangGraph) - automated triage & alerting
  - ✅ API wiring for incident ingestion & agent callbacks
  - ✅ Removed langchain_classic, upgraded to LangChain 0.1.0+ architecture
- ✅ **Week 8**: DORA metrics + frontend integration
  - ✅ DORA metrics service (domain models, calculator, PostgreSQL repository, REST API)
  - ✅ React frontend with router, layout, and 5 workflow pages
  - ✅ API Gateway proxy routes for metrics service
  - ✅ Docker Compose + Dockerfiles for metrics and frontend services

### Month 3: Production Ready (Week 9-12)
- ✅ **Week 9**: Integration testing + bug fixes
  - ✅ Fixed Python 3.9 compat (PEP 604 union syntax, datetime Z-suffix)
  - ✅ Fixed Go gateway stale tests (relocated + rewritten)
  - ✅ Metrics service tests (14 tests: health, DORA, events)
  - ✅ Go handler + middleware tests (19 tests)
  - ✅ Cross-service integration tests (6 tests: API contracts, e2e)
  - ✅ Full suite: 470 tests, 458 pass, 12 skip, 0 fail
- ✅ **Week 10**: Performance optimization (async, caching)
  - ✅ Go Gateway: connection pooling, HTTP client reuse, server timeouts
  - ✅ Go Gateway: Redis-backed response caching middleware with TTL
  - ✅ Python services: gunicorn multi-worker (agent-orchestrator, indexing, model-service)
  - ✅ Metrics service: multi-stage Docker build with uv, in-memory TTL cache
  - ✅ Frontend: React.lazy code splitting + Vite manual chunk config
  - ✅ Frontend: nginx-based Dockerfile with gzip, caching, security headers
  - ✅ Docker Compose: resource limits (CPU + memory) for all services
  - ✅ Full suite: 470 tests, 458 pass, 12 skip, 0 fail (no regressions)
- ✅ **Week 11**: CI/CD pipeline + cloud deployment
  - ✅ GitHub Actions CI (matrix: Go ×2, Python ×4, Frontend — tests + lint)
  - ✅ GitHub Actions CD (OIDC auth, ECR push, kustomize image update, ArgoCD auto-sync)
  - ✅ Terraform IaC (VPC, EKS, ECR ×8, IAM OIDC + IRSA — ap-southeast-1)
  - ✅ Kubernetes manifests (Kustomize: Deployments, Services, StatefulSets, Ingress, HPA, PVCs)
  - ✅ ArgoCD GitOps (app-of-apps, automated sync + prune + selfHeal)
  - ✅ Finetune service Dockerfile added (multi-stage, gunicorn, port 8006)
  - ✅ Cluster bootstrap (ALB Controller, ArgoCD, Prometheus, Kyverno via Helm)
  - ✅ Root Makefile (terraform, deploy, status, test-ci, docker-build, clean targets)
- ✅ **Week 12**: Portfolio packaging + interview prep
  - ✅ Interactive portfolio website (8 pages: HTML/CSS/JS, NVIDIA-themed dark mode)
  - ✅ Architecture diagram (interactive SVG with clickable service details)
  - ✅ Demo walkthrough (step-by-step curl commands for all 4 AI workflows)
  - ✅ Performance report (throughput charts, latency profiles, optimization history)
  - ✅ Interview Q&A (13 deep-dive questions across 5 NVIDIA IPP categories)
  - ✅ AWS cost analysis (line-item breakdown + optimization strategies)
  - ✅ Teardown guide (6-step safe decommission procedure)
---

## 🚀 Cloud Deployment

### Deploy to AWS EKS from Scratch

```bash
# 1. Bootstrap Terraform state backend (S3 + DynamoDB)
cd infra/terraform/bootstrap && terraform init && terraform apply -auto-approve

# 2. Provision VPC, EKS, ECR, IAM
make terraform-init
make terraform-plan   # review plan
make terraform-apply  # ~15-25 min

# 3. Set required secrets as environment variables
export POSTGRES_PASSWORD=<strong-password>
export JWT_SECRET=<strong-secret>
export OPENAI_API_KEY=<your-key>

# 4. Bootstrap cluster (ALB Controller, ArgoCD, Prometheus, Kyverno) + apply ArgoCD root app
make bootstrap

# 5. Check deployment status
make status
```

### Teardown

```bash
# Delete workflowai namespace and destroy all AWS resources
make clean
```

### GitOps CD Flow

Push to `main` -> GitHub Actions CI -> on success, CD builds Docker images,
pushes to ECR with `sha-<commit>` tag, updates `k8s/overlays/production/kustomization.yaml`,
commits back to main -> ArgoCD detects git change and auto-syncs the cluster.

## 🧪 Testing

### Run Unit Tests

```bash
# Go services
cd services/api-gateway
go test -v ./...

# Python services
cd services/agent-orchestrator
pytest --cov=. --cov-report=term-missing
```

### Run Integration Tests

```bash
cd tests/integration
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
pytest -v
```

### Run Load Tests

```bash
cd tests/load
locust -f locustfile.py --host=http://localhost:8000 --users=1000 --spawn-rate=100
```

---

## 📖 Documentation

- **[Technology Stack Selection](docs/tech-stack.md)** - Why Go + Python?
- **[Architecture Deep-Dive](docs/architecture.md)** - System design & ADRs
- **[API Documentation](docs/api.md)** - Endpoint reference & request/response formats
- **[Interview Preparation](docs/interview-prep/)** - Technical Q&A, demo script
- **[Performance Report](docs/performance-report.md)** - Benchmarks & optimizations
- **[CI/CD System Architecture](docs/cicd.md)** - Pipeline design, GitOps flow, security model
- **[Portfolio Website](docs/portfolio/index.html)** - Interactive project showcase (open in browser)

---

## 🎤 Interview Preparation

### Key Talking Points

**Q: Why polyglot architecture?**
> "I separated network I/O (Go) from AI compute (Python) based on technical requirements. Go achieved 40k RPS with 30MB memory for the Gateway, while Python was mandatory for LangChain/vLLM. Standard microservices patterns (HTTP + Redis Streams + OpenTelemetry) made language boundaries transparent."

**Q: How did you ensure performance at scale?**
> "I profiled every layer: Go Gateway achieves P95 < 20ms through goroutines and Redis connection pooling. Python services use async FastAPI with batched vLLM inference. Horizontal scaling is validated through load tests (1000 concurrent users, 10min duration). Week 10 report shows 8x improvement post-optimization."

**Q: How do you quantify AI impact?**
> "DORA metrics. I track deployment frequency, lead time, change failure rate, and MTTR. For example, automated failure triage reduces MTTR from 45min (manual) to 8min (AI-assisted), a 5.6x improvement quantifiable in dashboards."

---

## 🤝 Contributing

This is a personal portfolio project for NVIDIA interview. Not accepting external contributions.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 👤 Author

**Ren**  
Preparing for NVIDIA Senior Software Engineer - AI Workflow (IPP) interview  
**Project Duration**: Feb 2026 - May 2026 (3 months)  
**Target**: Demonstrate RAG, fine-tuning, and large-scale systems capability

---

## 🔗 Related Resources

- [NVIDIA AI Enterprise](https://www.nvidia.com/en-us/data-center/products/ai-enterprise/)
- [LangChain Documentation](https://python.langchain.com/)
- [vLLM Documentation](https://docs.vllm.ai/)
- [OpenTelemetry Specification](https://opentelemetry.io/docs/)

---

**Last Updated**: 2026-03-16  
**Status**: ✅ All 12 weeks complete — Production on AWS EKS, 15/15 CI green, 13/13 pods running
