# Learnings — Week 11 CI/CD + EKS Deployment

## [2026-03-15] Session Started: ses_31077bfdbffeX00Hgz5ysRHTV1

### Critical Technical Facts
- **Local Python is 3.9.6** — PEP 604 `X | Y` union syntax fails at runtime. Always add `from __future__ import annotations` to new files.
- **api-gateway uses `FROM scratch`** — No shell. All K8s probes MUST use `httpGet` not `exec`.
- **Frontend `REACT_APP_API_URL` is baked at build time** — On K8s, nginx must proxy `/api` to api-gateway service instead.
- **PostgreSQL init.sql uses `CREATE TABLE` without `IF NOT EXISTS`** — Needs to be made idempotent for K8s StatefulSet restarts.
- **No terraform, kubectl, aws CLI, or docker available in dev environment** — Tasks 11-13 must be executed from user's real terminal.

### Architecture Decisions
- AWS Region: `ap-southeast-1` (Singapore)
- EKS Cluster Name: `workflowai`
- Terraform State: S3 bucket `workflowai-terraform-state` + DynamoDB `workflowai-terraform-locks`
- ECR Repos: 8 total (api-gateway, ingestion, agent-orchestrator, indexing, model-service, metrics, finetune, frontend)
- Node Instance Type: `t3.large`, 2-4 nodes, single NAT gateway (cost optimization)
- Git remote: `https://github.com/SilkLee/workflow-ai.git`, branch `main`

### Service Ports
- api-gateway: 8000
- ingestion: 8001
- agent-orchestrator: 8002
- indexing: 8003
- model-service: 8004
- metrics: 8005
- finetune: 8006
- frontend: 3000

### K8s Probe Rules
- api-gateway: httpGet on /health:8000 (scratch base — NO exec)
- All other services: httpGet on /health:<port>
- postgres: tcpSocket:5432 (readiness), exec:pg_isready (liveness)
- redis: tcpSocket:6379 (readiness), exec:redis-cli ping (liveness)
- elasticsearch: httpGet /_cluster/health:9200

### Codebase Patterns
- DDD with domain/application/infrastructure/api layers
- Pydantic models for API DTOs, dataclasses for domain models
- FastAPI with CORS middleware
- Dependency injection via FastAPI Depends + lru_cache singletons
- Raw SQL with text() queries, NOT ORM mapped classes
- Inline styles in React (no CSS files, no UI frameworks)
- Functional components only in React
- Kustomize for app manifests (NOT Helm for application)
- Helm ONLY for 3rd-party tools (ArgoCD, kube-prometheus-stack, ALB controller)
- Image tags: `sha-<commit>` (never `:latest`)
- Single `workflowai` namespace (no multi-env)
