# Week 11: CI/CD Pipeline + AWS EKS Deployment

## TL;DR

> **Quick Summary**: Build a complete CI/CD pipeline with GitHub Actions, create production-grade Kubernetes infrastructure on AWS EKS using Terraform, deploy all 8 microservices via ArgoCD GitOps, and verify a live demo URL — maximizing NVIDIA interview impression.
> 
> **Deliverables**:
> - GitHub Actions CI pipeline (matrix: Go + Python + Frontend tests + linting)
> - GitHub Actions CD pipeline (build Docker images → push to ECR → trigger ArgoCD)
> - Terraform IaC (VPC, EKS cluster, ECR repos, ALB, IAM/OIDC)
> - Kubernetes manifests (Kustomize: Deployments, Services, StatefulSets, Ingress, HPA, Secrets, ConfigMaps)
> - ArgoCD GitOps configuration (app-of-apps pattern)
> - Cluster bootstrap script (ALB Controller, ArgoCD, kube-prometheus-stack)
> - Root Makefile for unified operations
> - Finetune service Dockerfile
> - Live EKS deployment with accessible ALB URL
> - Updated README with Week 11 completion
> 
> **Estimated Effort**: XL (20+ tasks, multi-wave)
> **Parallel Execution**: YES - 4 waves
> **Critical Path**: Task 2 (Terraform) → Task 10 (Bootstrap Script) → Task 12 (Deploy) → Task 13 (Verify)

---

## Context

### Original Request
User requested "Week 11: CI/CD pipeline + cloud deployment" — the penultimate week of a 12-week NVIDIA interview preparation project. User chose the most ambitious path: EKS + ArgoCD GitOps + full Terraform IaC + live deployment.

### Interview Summary
**Key Discussions**:
- Cloud architecture: EKS chosen over ECS/EC2 for maximum K8s showcase at NVIDIA
- GitOps: ArgoCD for continuous deployment (most impressive CD approach)
- CI: Full matrix GitHub Actions with parallel Go/Python/Frontend test jobs
- CD: Auto-deploy on push to main (CI → ECR → ArgoCD sync)
- Docker registry: ECR (AWS-native, IRSA integration)
- Terraform: Full AWS IaC using community modules
- Deploy for real: Actually `terraform apply` — live cluster with running services
- Finetune service: Add Dockerfile and deploy to K8s

**Research Findings**:
- Zero CI/CD infrastructure exists — completely greenfield
- 7 existing Dockerfiles (all multi-stage, well-structured)
- docker-compose.yml has 13 services — battle-tested ports, env vars, health checks, resource limits
- infra/terraform/ has only .gitkeep
- .env.example files exist for 5 services
- Prometheus/Grafana/Jaeger configs already exist
- No terraform, kubectl, aws CLI, or docker available in dev environment — deployment must be done from user's real terminal
- AWS region: ap-southeast-1 (Singapore), IAM roles preserved from Week 2

### Metis Review
**Identified Gaps** (addressed):
- Frontend API URL routing: nginx must proxy to api-gateway K8s service (not build-time env var)
- PostgreSQL init.sql not idempotent: Add `IF NOT EXISTS` to CREATE TABLE statements
- ECR pull auth: Use IRSA with node IAM role
- api-gateway uses `scratch` base: All K8s probes must use `httpGet` not `exec`
- Model download on pod startup: Use PVC for `/app/cache`
- Elasticsearch needs StatefulSet with PVC
- Hardcoded secrets in docker-compose.yml must NOT propagate to K8s
- No linting config at repo root: CI must explicitly define lint tools
- GitHub Actions concurrency: Cancel stale runs
- Cost guardrails: Single NAT, t3.large nodes, tag everything

---

## Work Objectives

### Core Objective
Create a complete, production-grade CI/CD pipeline and deploy all WorkflowAI microservices to AWS EKS via GitOps (ArgoCD), resulting in a live demo URL accessible from any browser.

### Concrete Deliverables
- `.github/workflows/ci.yml` — CI pipeline
- `.github/workflows/cd.yml` — CD pipeline
- `infra/terraform/` — Complete Terraform IaC (VPC, EKS, ECR, IAM, ALB)
- `infra/terraform/bootstrap/` — State backend bootstrap
- `k8s/base/` — Kustomize base manifests (all services)
- `k8s/overlays/production/` — Production overlay
- `k8s/argocd/` — ArgoCD Application CRs
- `infra/scripts/bootstrap-cluster.sh` — One-click cluster bootstrap
- `Makefile` — Root-level unified operations
- `services/finetune/Dockerfile` — New Dockerfile for finetune service
- Live ALB URL serving frontend + API

### Definition of Done
- [ ] `gh run list --workflow=ci.yml` shows green CI pass
- [ ] `terraform plan -detailed-exitcode` exits 0 (no drift)
- [ ] `kubectl get pods -n workflowai` shows all pods Running
- [ ] `curl http://<ALB_URL>/health` returns healthy
- [ ] `curl http://<ALB_URL>/` returns 200 (frontend)
- [ ] `kubectl get applications -n argocd` shows all Synced/Healthy

### Must Have
- Matrix CI with parallel test jobs for all services
- Terraform with pinned versions and S3 state backend
- Kustomize-based K8s manifests matching docker-compose.yml patterns exactly
- ArgoCD GitOps with auto-sync on git push
- HPA on api-gateway and frontend
- ALB Ingress Controller for external access
- K8s Secrets (no hardcoded passwords)
- PVCs for stateful services (postgres, elasticsearch, model cache)
- `httpGet` health probes (api-gateway uses `scratch` base)
- Prometheus + Grafana on K8s (via kube-prometheus-stack)
- Cost tags on all AWS resources
- `terraform destroy` documented for teardown

### Must NOT Have (Guardrails)
- **No application code changes** — Zero modifications to services/* source code or frontend/src/* (except Dockerfile additions)
- **No Helm charts for application** — Kustomize only for app manifests; Helm only for 3rd-party tools
- **No custom domain or SSL/TLS** — ALB URL is sufficient
- **No RDS or ElastiCache** — In-cluster PostgreSQL and Redis
- **No service mesh** (Istio/Linkerd) — Basic K8s Service + Ingress only
- **No network policies** — Not needed for demo
- **No Terraform CI/CD** (Atlantis) — Manual `terraform apply` only
- **No multi-environment namespaces** — Single `workflowai` namespace
- **No container vulnerability scanning** — Mention as "next step"
- **No `:latest` image tags in K8s** — Use `sha-<commit>` tags
- **No hardcoded secrets in K8s manifests** — Use K8s Secrets objects

---

## Verification Strategy

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed. No exceptions.

### Test Decision
- **Infrastructure exists**: YES (470 tests across all services)
- **Automated tests**: None new — wire existing tests into CI
- **Framework**: Go test, pytest, Jest (existing)
- **New infra validation**: `terraform validate`, `kubectl kustomize --dry-run`, `bash -n` for scripts

### QA Policy
Every task MUST include agent-executed QA scenarios.
Evidence saved to `.sisyphus/evidence/task-{N}-{scenario-slug}.{ext}`.

- **IaC files**: Use Bash — `terraform validate`, `terraform fmt -check`, syntax validation
- **K8s manifests**: Use Bash — `kubectl kustomize`, `kubectl apply --dry-run=client`
- **Shell scripts**: Use Bash — `bash -n`, `shellcheck` if available
- **GitHub Actions**: Use Bash — YAML lint, `gh workflow run` + `gh run list`
- **Live deployment**: Use Bash — `kubectl`, `curl`, `aws` commands

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately — no dependencies, 6 tasks parallel):
├── Task 1: GitHub Actions CI pipeline [deep]
├── Task 2: Terraform IaC (VPC, EKS, ECR, IAM) [deep]
├── Task 3: K8s base manifests — infrastructure (PG, Redis, ES) [deep]
├── Task 4: K8s base manifests — Go services (gateway, ingestion) [unspecified-high]
├── Task 5: K8s base manifests — Python services (agent, indexing, model, metrics, finetune) [deep]
├── Task 6: Finetune Dockerfile + K8s base manifests — frontend [quick]

Wave 2 (After Wave 1 — depends on manifests + Terraform, 4 tasks parallel):
├── Task 7: K8s production overlay (kustomization, ingress, HPA) [unspecified-high]
├── Task 8: ArgoCD configuration (app-of-apps) [unspecified-high]
├── Task 9: GitHub Actions CD pipeline [deep]
├── Task 10: Cluster bootstrap script + Makefile [unspecified-high]

Wave 3 (After Wave 2 — actual deployment, sequential):
├── Task 11: Terraform apply (create AWS resources) [deep]
├── Task 12: Cluster bootstrap + deploy services [deep]

Wave 4 (After Wave 3 — verification + docs):
├── Task 13: End-to-end verification [deep]
├── Task 14: Update README + commit + push [quick]

Wave FINAL (After ALL tasks — independent review, 4 parallel):
├── Task F1: Plan compliance audit (oracle)
├── Task F2: Code quality review (unspecified-high)
├── Task F3: Real manual QA (unspecified-high)
├── Task F4: Scope fidelity check (deep)

Critical Path: Task 2 → Task 7 → Task 10 → Task 11 → Task 12 → Task 13 → F1-F4
Parallel Speedup: ~60% faster than sequential (Wave 1 runs 6 tasks in parallel)
Max Concurrent: 6 (Wave 1)
```

### Dependency Matrix

| Task | Depends On | Blocks | Wave |
|------|-----------|--------|------|
| 1 | — | 9 | 1 |
| 2 | — | 7, 9, 10, 11 | 1 |
| 3 | — | 7 | 1 |
| 4 | — | 7 | 1 |
| 5 | — | 7 | 1 |
| 6 | — | 7 | 1 |
| 7 | 3, 4, 5, 6 | 8, 10, 12 | 2 |
| 8 | 7 | 12 | 2 |
| 9 | 1, 2 | 12 | 2 |
| 10 | 2, 7 | 12 | 2 |
| 11 | 2 | 12 | 3 |
| 12 | 7, 8, 9, 10, 11 | 13 | 3 |
| 13 | 12 | 14 | 4 |
| 14 | 13 | — | 4 |

### Agent Dispatch Summary

- **Wave 1**: **6** — T1 → `deep`, T2 → `deep`, T3 → `deep`, T4 → `unspecified-high`, T5 → `deep`, T6 → `quick`
- **Wave 2**: **4** — T7 → `unspecified-high`, T8 → `unspecified-high`, T9 → `deep`, T10 → `unspecified-high`
- **Wave 3**: **2** — T11 → `deep`, T12 → `deep`
- **Wave 4**: **2** — T13 → `deep`, T14 → `quick`
- **FINAL**: **4** — F1 → `oracle`, F2 → `unspecified-high`, F3 → `unspecified-high`, F4 → `deep`

---

## TODOs

> Implementation + Test = ONE Task. Never separate.
> EVERY task MUST have: Recommended Agent Profile + Parallelization info + QA Scenarios.
> **A task WITHOUT QA Scenarios is INCOMPLETE. No exceptions.**

### Wave 1 — Foundation (Start Immediately, 6 tasks parallel)

- [ ] 1. GitHub Actions CI Pipeline

  **What to do**:
  - Create `.github/workflows/ci.yml` with matrix strategy
  - Go jobs: `go test -v -short ./...` for api-gateway and ingestion (separate matrix entries)
  - Python jobs: `pip install -e '.[dev]' && python -m pytest tests/ -v --tb=short` for agent-orchestrator, indexing, model-service, metrics, finetune (5 separate matrix entries)
  - Frontend job: `npm ci && npx jest` in frontend/
  - Linting jobs: `golangci-lint run ./...` for Go services, `ruff check .` for Python services
  - Use `actions/checkout@v4`, `actions/setup-go@v5`, `actions/setup-python@v5`, `actions/setup-node@v4`
  - Add Go module cache (`actions/cache` with `go-build` + `go-mod`), pip cache, npm cache
  - Use `concurrency` group with `cancel-in-progress: true` to prevent parallel stale runs
  - Trigger on `push` (all branches) and `pull_request` to `main`
  - Service containers: PostgreSQL 15 + Redis 7 for integration test jobs (metrics service needs PG)
  - Go test needs `-short` flag (skips tests requiring Redis connection)

  **Must NOT do**:
  - Do NOT modify any service source code
  - Do NOT add new test files
  - Do NOT use `:latest` for action versions (pin to specific versions)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`superpowers/verification-before-completion`]
    - `superpowers/verification-before-completion`: Must validate YAML syntax and workflow structure before committing
  - **Skills Evaluated but Omitted**:
    - `git-master`: Standard git operations only, no complex git needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 2, 3, 4, 5, 6)
  - **Blocks**: Task 9 (CD pipeline extends CI)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `services/api-gateway/go.mod` — Go version (1.22) and module name for test command
  - `services/agent-orchestrator/pyproject.toml` — Python test config, pytest options, dev dependencies
  - `services/metrics/pyproject.toml` — Has asyncpg dependency (needs PG service container for tests)
  - `frontend/package.json` — Jest config, test script, Node version requirements
  - `services/finetune/pyproject.toml` — Finetune test config (has tests but no Dockerfile yet)

  **Test References**:
  - `services/api-gateway/internal/interfaces/http/` — 3 Go test files (handlers, auth, ratelimit)
  - `services/agent-orchestrator/tests/` — ~30 Python test files (largest suite)
  - `services/metrics/tests/` — 4 test files (needs PG for some tests)
  - `frontend/src/__tests__/` — 3 Jest test files
  - `tests/integration/` — 2 integration test files (skip in CI — needs running services)

  **WHY Each Reference Matters**:
  - pyproject.toml files define `[tool.pytest.ini_options]` which controls test discovery paths
  - Go tests use `-short` flag to skip Redis-dependent tests
  - Metrics tests need a PostgreSQL service container because they test real DB queries
  - Frontend uses ts-jest transformer — must `npm ci` before testing
  - Integration tests in `tests/` should be SKIPPED in CI (they require all services running)

  **Acceptance Criteria**:
  - [ ] `.github/workflows/ci.yml` exists and is valid YAML
  - [ ] Workflow has matrix strategy with entries for: api-gateway, ingestion, agent-orchestrator, indexing, model-service, metrics, finetune, frontend, go-lint, python-lint
  - [ ] Concurrency group configured with cancel-in-progress
  - [ ] Caching configured for Go modules, pip, npm

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: CI YAML is valid
    Tool: Bash
    Steps:
      1. python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" (if pyyaml available)
      2. OR: Manually inspect structure matches GitHub Actions schema
    Expected Result: No YAML parse errors
    Evidence: .sisyphus/evidence/task-1-yaml-valid.txt

  Scenario: CI workflow triggers correctly
    Tool: Bash (gh CLI)
    Steps:
      1. git push to trigger CI
      2. gh run list --workflow=ci.yml --limit=1 --json status,conclusion
      3. Wait for completion (gh run watch)
    Expected Result: conclusion="success" (all matrix jobs pass)
    Failure Indicators: Any matrix job shows conclusion="failure"
    Evidence: .sisyphus/evidence/task-1-ci-run.txt
  ```

  **Commit**: YES
  - Message: `feat(ci): add GitHub Actions CI pipeline with matrix testing`
  - Files: `.github/workflows/ci.yml`

- [ ] 2. Terraform AWS Infrastructure (VPC, EKS, ECR, IAM)

  **What to do**:
  - Create `infra/terraform/versions.tf`: AWS provider ~> 5.0, Kubernetes provider, Helm provider. S3 backend configuration for state (bucket: `workflowai-terraform-state`, DynamoDB: `workflowai-terraform-locks`)
  - Create `infra/terraform/variables.tf`: region (default: ap-southeast-1), cluster_name (default: workflowai), node_instance_type (default: t3.large), node_count (min: 2, max: 4, desired: 2), common tags
  - Create `infra/terraform/vpc.tf`: Use `terraform-aws-modules/vpc/aws` ~> 5.0 — 2 AZs, public + private subnets, **single NAT gateway** (cost optimization), enable DNS hostnames
  - Create `infra/terraform/eks.tf`: Use `terraform-aws-modules/eks/aws` ~> 20.0 — managed node group (t3.large, 2-4 nodes), IRSA enabled, OIDC provider for GitHub Actions, aws-auth configmap, enable EBS CSI driver addon, coredns addon, vpc-cni addon, kube-proxy addon
  - Create `infra/terraform/ecr.tf`: 8 ECR repositories (api-gateway, ingestion, agent-orchestrator, indexing, model-service, metrics, finetune, frontend). Image scanning on push enabled. Lifecycle policy: keep last 10 images.
  - Create `infra/terraform/iam.tf`: IAM role for GitHub Actions OIDC (for CD pipeline to push to ECR), IAM role for AWS Load Balancer Controller (IRSA), IAM policy for ECR pull on EKS nodes
  - Create `infra/terraform/outputs.tf`: cluster_endpoint, cluster_name, ecr_repository_urls (map), alb_controller_role_arn, github_actions_role_arn, kubeconfig_command
  - Create `infra/terraform/terraform.tfvars.example` with safe defaults
  - Create `infra/terraform/bootstrap/main.tf`: S3 bucket + DynamoDB table for Terraform state backend (must be applied FIRST before main terraform)
  - All resources tagged with: Project=workflowai, Environment=production, ManagedBy=terraform, Week=11

  **Must NOT do**:
  - Do NOT create RDS or ElastiCache (in-cluster PG/Redis)
  - Do NOT create Route53 hosted zone or ACM certificate
  - Do NOT create multiple NAT gateways (cost optimization)
  - Do NOT use local Terraform state (S3 backend mandatory)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`superpowers/verification-before-completion`]
  - **Skills Evaluated but Omitted**:
    - `superpowers/systematic-debugging`: Not debugging, creating new files

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 3, 4, 5, 6)
  - **Blocks**: Tasks 7, 9, 10, 11
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `docker-compose.yml:1-317` — All service names, ports, environment variables, resource limits — Terraform outputs must produce values compatible with these
  - `services/api-gateway/.env.example` — Environment variables the api-gateway expects
  - `services/agent-orchestrator/.env.example` — Environment variables the agent-orchestrator expects

  **External References**:
  - terraform-aws-modules/vpc/aws: https://registry.terraform.io/modules/terraform-aws-modules/vpc/aws/latest
  - terraform-aws-modules/eks/aws: https://registry.terraform.io/modules/terraform-aws-modules/eks/aws/latest
  - AWS EKS IRSA: https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html
  - GitHub OIDC with AWS: https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services

  **WHY Each Reference Matters**:
  - docker-compose.yml is the source of truth for service ports, names, and env vars — K8s + Terraform must match
  - .env.example files show what secrets/config each service needs — informs K8s Secrets/ConfigMaps
  - Community Terraform modules are battle-tested and follow AWS best practices — preferred over raw resources

  **Acceptance Criteria**:
  - [ ] `cd infra/terraform && terraform fmt -check` passes (no formatting issues)
  - [ ] `cd infra/terraform && terraform validate` returns "Success!"
  - [ ] `cd infra/terraform && terraform plan` shows expected resources (VPC, EKS, 8 ECR repos, IAM roles)
  - [ ] `cd infra/terraform/bootstrap && terraform validate` returns "Success!"
  - [ ] All provider/module versions are pinned (no floating versions)
  - [ ] terraform.tfvars.example exists with documented variables

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Terraform validates successfully
    Tool: Bash
    Steps:
      1. cd infra/terraform
      2. terraform init -backend=false (skip backend for validation)
      3. terraform validate
      4. terraform fmt -check -recursive
    Expected Result: "Success! The configuration is valid." and no format diffs
    Evidence: .sisyphus/evidence/task-2-terraform-validate.txt

  Scenario: Bootstrap validates
    Tool: Bash
    Steps:
      1. cd infra/terraform/bootstrap
      2. terraform init
      3. terraform validate
    Expected Result: "Success!"
    Evidence: .sisyphus/evidence/task-2-bootstrap-validate.txt
  ```

  **Commit**: YES
  - Message: `feat(infra): add Terraform IaC for VPC, EKS, ECR, IAM`
  - Files: `infra/terraform/**`

- [ ] 3. K8s Base Manifests — Infrastructure (PostgreSQL, Redis, Elasticsearch)

  **What to do**:
  - Create `k8s/base/kustomization.yaml`: Resource list of all base manifests
  - Create `k8s/base/namespace.yaml`: `workflowai` namespace
  - Create `k8s/base/postgres-statefulset.yaml`: PostgreSQL 15 StatefulSet
    - 1 replica, PVC (5Gi), port 5432
    - `tcpSocket` readiness probe on port 5432 (postgres doesn't have HTTP)
    - `exec` liveness probe: `pg_isready -U workflowai`
    - Init container or initdb: mount `init.sql` from ConfigMap (with IF NOT EXISTS added)
    - Environment from K8s Secret: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
  - Create `k8s/base/postgres-service.yaml`: ClusterIP service on port 5432
  - Create `k8s/base/redis-statefulset.yaml`: Redis 7-alpine StatefulSet
    - 1 replica, PVC (1Gi), port 6379
    - `tcpSocket` readiness probe on port 6379
    - `exec` liveness probe: `redis-cli ping`
  - Create `k8s/base/redis-service.yaml`: ClusterIP service on port 6379
  - Create `k8s/base/elasticsearch-statefulset.yaml`: Elasticsearch 8.11.0 StatefulSet
    - 1 replica, PVC (10Gi), port 9200
    - Environment: `discovery.type=single-node`, `ES_JAVA_OPTS=-Xms512m -Xmx512m`, `xpack.security.enabled=false`
    - `httpGet` readiness probe on port 9200 path `/_cluster/health`
    - Resource limits: memory 1Gi (ES needs it)
  - Create `k8s/base/elasticsearch-service.yaml`: ClusterIP service on port 9200
  - Create `k8s/base/secrets.yaml`: K8s Secret (opaque) with base64 placeholders for:
    - `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `JWT_SECRET`, `OPENAI_API_KEY`
    - Comment: "Replace with real values or use sealed-secrets in production"
  - Create `k8s/base/configmap.yaml`: ConfigMap with non-secret config:
    - `REDIS_URL=redis://redis:6379/0`
    - `ELASTICSEARCH_URL=http://elasticsearch:9200`
    - `MODEL_SERVICE_URL=http://model-service:8004`
    - `AGENT_SERVICE_URL=http://agent-orchestrator:8002`
    - `INDEXING_SERVICE_URL=http://indexing:8003`
    - `INGESTION_SERVICE_URL=http://ingestion:8001`
    - `METRICS_SERVICE_URL=http://metrics:8005`
    - `DATABASE_URL=postgresql+asyncpg://workflowai:$(POSTGRES_PASSWORD)@postgres:5432/workflowai`
  - Create `k8s/base/postgres-init-configmap.yaml`: ConfigMap containing init.sql content (with IF NOT EXISTS)

  **Must NOT do**:
  - Do NOT use Helm charts for infrastructure services
  - Do NOT create PersistentVolume objects (use dynamic provisioning via StorageClass)
  - Do NOT hardcode passwords in manifests — use K8s Secret references
  - Do NOT use `:latest` image tags

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`superpowers/verification-before-completion`]
    - `superpowers/verification-before-completion`: Must validate YAML structure of all manifests
  - **Skills Evaluated but Omitted**:
    - `frontend-ui-ux`: No UI work involved

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 4, 5, 6)
  - **Blocks**: Task 7 (production overlay needs base manifests)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `docker-compose.yml:5-59` — PostgreSQL, Redis, Elasticsearch service definitions: image versions, ports, env vars, health checks, volumes
  - `infra/docker/postgres/init.sql` — Database schema (must be mounted as ConfigMap with IF NOT EXISTS added)

  **API/Type References**:
  - `docker-compose.yml:8-11` — PostgreSQL credentials (POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB)
  - `docker-compose.yml:46-48` — Elasticsearch env vars (discovery.type, ES_JAVA_OPTS, xpack.security.enabled)

  **External References**:
  - K8s StatefulSet: https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/
  - K8s Kustomize: https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/

  **WHY Each Reference Matters**:
  - docker-compose.yml is the source of truth for all service configurations — K8s manifests must match ports, env vars, and health check patterns exactly
  - init.sql must be made idempotent (IF NOT EXISTS) because K8s StatefulSet pods restart and re-run init
  - Health checks in docker-compose show what protocol each service supports (PG=tcp, Redis=exec, ES=http)

  **Acceptance Criteria**:
  - [ ] `kubectl kustomize k8s/base/` produces valid combined YAML
  - [ ] Namespace, 3 StatefulSets, 3 Services, 1 Secret, 2 ConfigMaps present in output
  - [ ] All StatefulSets have PVC templates
  - [ ] No hardcoded passwords in any manifest (only Secret references)
  - [ ] All image tags are pinned (postgres:15-alpine, redis:7-alpine, elasticsearch:8.11.0)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Kustomize builds successfully
    Tool: Bash
    Preconditions: k8s/base/ directory with all manifests created
    Steps:
      1. kubectl kustomize k8s/base/ > /tmp/base-output.yaml
      2. grep -c 'kind: StatefulSet' /tmp/base-output.yaml
      3. grep -c 'kind: Service' /tmp/base-output.yaml (count infrastructure services only)
      4. grep -c 'kind: Secret' /tmp/base-output.yaml
      5. grep -c 'kind: ConfigMap' /tmp/base-output.yaml
    Expected Result: 3 StatefulSets, 3+ Services, 1 Secret, 2+ ConfigMaps
    Failure Indicators: kubectl kustomize returns error, or counts don't match
    Evidence: .sisyphus/evidence/task-3-kustomize-build.txt

  Scenario: No hardcoded secrets in manifests
    Tool: Bash
    Steps:
      1. grep -r 'dev_password_123' k8s/
      2. grep -r 'changeme' k8s/ (excluding comments)
    Expected Result: No matches (all secrets via K8s Secret references)
    Failure Indicators: grep finds hardcoded passwords in non-Secret files
    Evidence: .sisyphus/evidence/task-3-no-hardcoded-secrets.txt
  ```

  **Evidence to Capture:**
  - [ ] task-3-kustomize-build.txt — kubectl kustomize output
  - [ ] task-3-no-hardcoded-secrets.txt — grep results

  **Commit**: YES (groups with Tasks 4, 5, 6)
  - Message: `feat(k8s): add Kubernetes base manifests with Kustomize`
  - Files: `k8s/base/**`

- [ ] 4. K8s Base Manifests — Go Services (API Gateway, Ingestion)

  **What to do**:
  - Create `k8s/base/api-gateway-deployment.yaml`: api-gateway Deployment
    - Image: `<ECR_URL>/api-gateway:sha-<commit>` (placeholder)
    - Port 8000, 2 replicas
    - `httpGet` readiness/liveness probe on `/health` port 8000 (api-gateway has /health endpoint)
    - Environment from ConfigMap: REDIS_URL, AGENT_SERVICE_URL, INDEXING_SERVICE_URL, MODEL_SERVICE_URL, INGESTION_SERVICE_URL, METRICS_SERVICE_URL
    - Environment from Secret: JWT_SECRET
    - Resource limits: memory 256Mi, cpu 500m (matching docker-compose)
  - Create `k8s/base/api-gateway-service.yaml`: ClusterIP service, port 8000
  - Create `k8s/base/ingestion-deployment.yaml`: ingestion Deployment
    - Image: `<ECR_URL>/ingestion:sha-<commit>` (placeholder)
    - Port 8001, 1 replica
    - `httpGet` readiness/liveness probe on `/health` port 8001
    - Environment from ConfigMap: REDIS_URL
    - Resource limits: memory 256Mi, cpu 500m
  - Create `k8s/base/ingestion-service.yaml`: ClusterIP service, port 8001
  - Update `k8s/base/kustomization.yaml` to include these new resources

  **Must NOT do**:
  - Do NOT modify Go service source code
  - Do NOT use `exec` probes (api-gateway uses `scratch` base — no shell)
  - Do NOT use `:latest` image tags

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`superpowers/verification-before-completion`]
    - `superpowers/verification-before-completion`: Must validate YAML and probe configuration
  - **Skills Evaluated but Omitted**:
    - `deep`: Straightforward manifest creation, not complex logic

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 5, 6)
  - **Blocks**: Task 7 (production overlay)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `docker-compose.yml:62-88` — api-gateway service definition: port 8000, all environment variables, resource limits (256M, 0.50 cpu)
  - `docker-compose.yml:91-111` — ingestion service definition: port 8001, REDIS_URL env var, resource limits
  - `services/api-gateway/Dockerfile` — Uses `FROM scratch` (no shell — all probes must be httpGet)

  **API/Type References**:
  - `services/api-gateway/.env.example` — Environment variables needed by api-gateway
  - `services/api-gateway/internal/interfaces/http/router.go` — Has `/health` endpoint for probes

  **WHY Each Reference Matters**:
  - api-gateway uses `scratch` base image — this is CRITICAL because `exec` probes won't work (no shell)
  - docker-compose env vars are the source of truth for what configuration each Go service needs
  - Resource limits from docker-compose should be translated to K8s resource requests/limits

  **Acceptance Criteria**:
  - [ ] api-gateway Deployment uses `httpGet` probes (NOT exec)
  - [ ] Both Deployments have resource limits matching docker-compose
  - [ ] Image tags use placeholder format `<ECR_URL>/service:sha-<commit>`
  - [ ] `kubectl kustomize k8s/base/` includes both Deployments and Services

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Go service manifests are valid
    Tool: Bash
    Preconditions: k8s/base/ directory with Go service manifests
    Steps:
      1. kubectl kustomize k8s/base/ > /tmp/base-output.yaml
      2. grep -A5 'name: api-gateway' /tmp/base-output.yaml | grep 'httpGet'
      3. Verify NO 'exec' probes in api-gateway deployment
      4. Verify ingestion deployment has httpGet probes on port 8001
    Expected Result: Both deployments valid, api-gateway uses httpGet probes only
    Failure Indicators: exec probes found in api-gateway, or kustomize error
    Evidence: .sisyphus/evidence/task-4-go-manifests.txt
  ```

  **Commit**: YES (groups with Tasks 3, 5, 6)
  - Message: `feat(k8s): add Kubernetes base manifests with Kustomize`
  - Files: `k8s/base/api-gateway-*.yaml`, `k8s/base/ingestion-*.yaml`

- [ ] 5. K8s Base Manifests — Python Services (Agent, Indexing, Model, Metrics, Finetune)

  **What to do**:
  - Create `k8s/base/agent-orchestrator-deployment.yaml`: agent-orchestrator Deployment
    - Image: `<ECR_URL>/agent-orchestrator:sha-<commit>`
    - Port 8002, 1 replica
    - `httpGet` readiness/liveness probe on `/health` port 8002
    - Environment from ConfigMap: REDIS_URL, ELASTICSEARCH_URL, MODEL_SERVICE_URL, USE_LOCAL_MODEL=true
    - Environment from Secret: OPENAI_API_KEY
    - Volume mount: `agent-cache` PVC at `/app/cache`
    - Resource limits: memory 1Gi, cpu 1000m (matching docker-compose)
  - Create `k8s/base/agent-orchestrator-service.yaml`: ClusterIP service, port 8002
  - Create `k8s/base/indexing-deployment.yaml`: indexing Deployment
    - Image: `<ECR_URL>/indexing:sha-<commit>`
    - Port 8003, 1 replica
    - `httpGet` readiness/liveness probe on `/health` port 8003
    - Environment from ConfigMap: ELASTICSEARCH_URL, EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2, DEVICE=cpu
    - Volume mount: `indexing-cache` PVC at `/app/cache`
    - Resource limits: memory 1Gi, cpu 1000m
  - Create `k8s/base/indexing-service.yaml`: ClusterIP service, port 8003
  - Create `k8s/base/model-service-deployment.yaml`: model-service Deployment
    - Image: `<ECR_URL>/model-service:sha-<commit>`
    - Port 8004, 1 replica
    - `httpGet` readiness/liveness probe on `/health` port 8004
    - Environment from ConfigMap: MODEL_NAME=Qwen/Qwen2.5-1.5B-Instruct, DEVICE=cpu, MAX_MODEL_LEN=4096
    - Volume mount: `model-cache` PVC at `/app/cache` (model download survives pod rescheduling)
    - Resource limits: memory 2Gi, cpu 2000m (matching docker-compose)
  - Create `k8s/base/model-service-service.yaml`: ClusterIP service, port 8004
  - Create `k8s/base/metrics-deployment.yaml`: metrics Deployment
    - Image: `<ECR_URL>/metrics:sha-<commit>`
    - Port 8005, 1 replica
    - `httpGet` readiness/liveness probe on `/health` port 8005
    - Environment from ConfigMap: DATABASE_URL (reference Secret for password portion)
    - Resource limits: memory 512Mi, cpu 1000m
  - Create `k8s/base/metrics-service.yaml`: ClusterIP service, port 8005
  - Create `k8s/base/finetune-deployment.yaml`: finetune Deployment
    - Image: `<ECR_URL>/finetune:sha-<commit>`
    - Port 8006, 1 replica
    - `httpGet` readiness/liveness probe on `/health` port 8006
    - Resource limits: memory 1Gi, cpu 1000m
  - Create `k8s/base/finetune-service.yaml`: ClusterIP service, port 8006
  - Create PVC manifests for agent-cache, indexing-cache, model-cache (each 5Gi, ReadWriteOnce)
  - Update `k8s/base/kustomization.yaml` to include all new resources

  **Must NOT do**:
  - Do NOT modify Python service source code
  - Do NOT use `:latest` image tags
  - Do NOT hardcode DATABASE_URL password — reference from Secret
  - Do NOT create GPU resource requests (all services run on CPU)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`superpowers/verification-before-completion`]
    - `superpowers/verification-before-completion`: Must validate all 5 service manifests + PVCs
  - **Skills Evaluated but Omitted**:
    - `quick`: Too many manifests for a quick task

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4, 6)
  - **Blocks**: Task 7 (production overlay)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `docker-compose.yml:113-175` — agent-orchestrator, indexing: ports, env vars, volumes (cache dirs), resource limits
  - `docker-compose.yml:176-209` — model-service: port 8004, MODEL_NAME, DEVICE, MAX_MODEL_LEN, model_cache volume, resource limits (2G, 2.00 cpu)
  - `docker-compose.yml:211-232` — metrics: port 8005, DATABASE_URL, resource limits (512M, 1.00 cpu)
  - `services/finetune/pyproject.toml` — finetune service config (has tests but needs Dockerfile and K8s manifests)

  **API/Type References**:
  - `services/agent-orchestrator/.env.example` — All env vars needed (REDIS_URL, ELASTICSEARCH_URL, MODEL_SERVICE_URL, etc.)
  - `services/model-service/.env.example` — MODEL_NAME, DEVICE, MAX_MODEL_LEN env vars
  - `services/indexing/.env.example` — ELASTICSEARCH_URL, EMBEDDING_MODEL env vars

  **WHY Each Reference Matters**:
  - docker-compose volumes show which services need PVCs (/app/cache directories for model downloads and embeddings)
  - Resource limits from docker-compose are calibrated for the workload — K8s should match
  - model-service is the heaviest Python service (2G memory, 2 CPU) — must set resource requests properly
  - metrics needs DATABASE_URL with async driver (postgresql+asyncpg://) — must reference Secret for password

  **Acceptance Criteria**:
  - [ ] 5 Python service Deployments + 5 Services in kustomize output
  - [ ] All use `httpGet` probes on respective ports
  - [ ] model-service has 2Gi memory limit and model-cache PVC
  - [ ] agent-orchestrator and indexing have cache PVCs
  - [ ] No hardcoded passwords in DATABASE_URL
  - [ ] 3 PVC manifests created (agent-cache, indexing-cache, model-cache)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Python service manifests build correctly
    Tool: Bash
    Preconditions: All k8s/base/ Python service manifests created
    Steps:
      1. kubectl kustomize k8s/base/ > /tmp/base-output.yaml
      2. Count Deployment objects with 'kind: Deployment' (should be 7 total: 2 Go + 5 Python)
      3. Count PersistentVolumeClaim objects (should be 3: agent-cache, indexing-cache, model-cache)
      4. grep for ':latest' in /tmp/base-output.yaml (should return empty)
    Expected Result: 7 Deployments, 3 PVCs, zero :latest tags
    Failure Indicators: Wrong counts or :latest found
    Evidence: .sisyphus/evidence/task-5-python-manifests.txt

  Scenario: Model service has correct resource limits
    Tool: Bash
    Steps:
      1. kubectl kustomize k8s/base/ > /tmp/base-output.yaml
      2. Extract model-service Deployment, check resources.limits.memory = 2Gi
      3. Check model-service has volumeMount for /app/cache
    Expected Result: memory limit 2Gi, cpu limit 2000m, /app/cache mount present
    Evidence: .sisyphus/evidence/task-5-model-resources.txt
  ```

  **Commit**: YES (groups with Tasks 3, 4, 6)
  - Message: `feat(k8s): add Kubernetes base manifests with Kustomize`
  - Files: `k8s/base/*-deployment.yaml`, `k8s/base/*-service.yaml`, `k8s/base/*-pvc.yaml`

- [ ] 6. Finetune Dockerfile + K8s Base Manifests — Frontend

  **What to do**:
  - Create `services/finetune/Dockerfile`:
    - Multi-stage build following same pattern as other Python services
    - Base: python:3.11-slim
    - Install uv, copy pyproject.toml, install dependencies
    - Copy source, expose port 8006
    - CMD: gunicorn with uvicorn workers (same pattern as metrics/indexing/model-service)
    - Health check endpoint: /health
  - Create `k8s/base/frontend-deployment.yaml`: frontend Deployment
    - Image: `<ECR_URL>/frontend:sha-<commit>`
    - Port 3000 (nginx serves on 3000, see docker-compose)
    - `httpGet` readiness/liveness probe on `/` port 3000
    - Resource limits: memory 128Mi, cpu 250m (matching docker-compose)
    - **CRITICAL**: Frontend nginx config must proxy `/api` to `http://api-gateway:8000`
    - This means the frontend Dockerfile's nginx.conf must have a `location /api/` proxy_pass block
    - The existing frontend Dockerfile already uses nginx — we need to check if it has proxy config
    - If not, create `k8s/base/frontend-nginx-configmap.yaml` with nginx config that adds the proxy
  - Create `k8s/base/frontend-service.yaml`: ClusterIP service, port 3000
  - Update `k8s/base/kustomization.yaml` to include frontend resources

  **Must NOT do**:
  - Do NOT modify frontend source code (src/**)
  - Do NOT change the existing `frontend/Dockerfile` for docker-compose use
  - Do NOT use REACT_APP_API_URL env var in K8s (nginx proxy handles API routing instead)
  - Do NOT use `:latest` image tags

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`superpowers/verification-before-completion`]
    - `superpowers/verification-before-completion`: Validate Dockerfile builds and nginx config
  - **Skills Evaluated but Omitted**:
    - `visual-engineering`: No UI changes, just infra files

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Tasks 1, 2, 3, 4, 5)
  - **Blocks**: Task 7 (production overlay)
  - **Blocked By**: None

  **References**:

  **Pattern References**:
  - `services/metrics/Dockerfile` — Multi-stage Python Dockerfile pattern with uv + gunicorn (follow this for finetune)
  - `frontend/Dockerfile` — Existing frontend Dockerfile (nginx-based, check for proxy config)
  - `docker-compose.yml:284-303` — Frontend service definition: port 3000, REACT_APP_API_URL env var, resource limits

  **API/Type References**:
  - `services/finetune/pyproject.toml` — Dependencies and project config for finetune service
  - `services/finetune/main.py` — FastAPI app entry point (find the health endpoint path)

  **WHY Each Reference Matters**:
  - metrics/Dockerfile is the best template for finetune (both are Python, similar structure)
  - Frontend's existing nginx Dockerfile may already handle proxying — check before creating configmap
  - REACT_APP_API_URL is baked at build time — on K8s we MUST use nginx proxy instead

  **Acceptance Criteria**:
  - [ ] `services/finetune/Dockerfile` exists and follows multi-stage pattern
  - [ ] Frontend Deployment has nginx proxy config for `/api` -> `api-gateway:8000`
  - [ ] Frontend uses `httpGet` probe on `/` port 3000
  - [ ] Finetune Deployment uses `httpGet` probe on `/health` port 8006
  - [ ] Both added to kustomization.yaml

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Finetune Dockerfile is valid
    Tool: Bash
    Steps:
      1. cat services/finetune/Dockerfile
      2. Verify FROM python:3.11-slim (or similar)
      3. Verify EXPOSE 8006
      4. Verify CMD contains gunicorn or uvicorn
    Expected Result: Valid Dockerfile matching project patterns
    Evidence: .sisyphus/evidence/task-6-finetune-dockerfile.txt

  Scenario: Frontend nginx proxies API
    Tool: Bash
    Steps:
      1. Check frontend K8s manifests for nginx config
      2. Verify location /api/ with proxy_pass http://api-gateway:8000
      3. kubectl kustomize k8s/base/ includes frontend Deployment
    Expected Result: nginx config proxies /api to api-gateway service
    Failure Indicators: No proxy_pass directive, or REACT_APP_API_URL still used
    Evidence: .sisyphus/evidence/task-6-frontend-nginx.txt
  ```

  **Commit**: YES
  - Message: `feat(finetune): add Dockerfile for finetune service`
  - Files: `services/finetune/Dockerfile`
  - Second commit groups with Tasks 3, 4, 5: `feat(k8s): add Kubernetes base manifests with Kustomize`
  - Files: `k8s/base/frontend-*.yaml`, `k8s/base/frontend-nginx-configmap.yaml`

### Wave 2 — Overlay + GitOps + CD (After Wave 1, 4 tasks parallel)

- [ ] 7. K8s Production Overlay (Kustomization, Ingress, HPA)

  **What to do**:
  - Create `k8s/overlays/production/kustomization.yaml`:
    - Reference `../../base` as base
    - Set namespace: `workflowai` for all resources
    - Add common labels: `app.kubernetes.io/part-of: workflowai`, `environment: production`
    - Patch resource limits for production (can be same as base for now)
    - Set image names with newName pointing to ECR URLs (will be overridden by CD pipeline)
  - Create `k8s/overlays/production/ingress.yaml`: ALB Ingress
    - apiVersion: networking.k8s.io/v1
    - Annotations for AWS ALB:
      - `kubernetes.io/ingress.class: alb`
      - `alb.ingress.kubernetes.io/scheme: internet-facing`
      - `alb.ingress.kubernetes.io/target-type: ip`
      - `alb.ingress.kubernetes.io/listen-ports: '[{"HTTP": 80}]'`
      - `alb.ingress.kubernetes.io/healthcheck-path: /health`
    - Rules:
      - Path `/` → frontend service, port 3000
      - Path `/health` → api-gateway service, port 8000
      - Path `/api/*` → api-gateway service, port 8000
  - Create `k8s/overlays/production/hpa-api-gateway.yaml`: HPA for api-gateway
    - Min 2, Max 5 replicas
    - Target CPU utilization: 70%
  - Create `k8s/overlays/production/hpa-frontend.yaml`: HPA for frontend
    - Min 2, Max 4 replicas
    - Target CPU utilization: 70%

  **Must NOT do**:
  - Do NOT create Ingress with TLS/SSL configuration
  - Do NOT use nginx ingress controller (use ALB)
  - Do NOT create multiple namespaces (single workflowai namespace)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`superpowers/verification-before-completion`]
    - `superpowers/verification-before-completion`: Must validate overlay builds on top of base
  - **Skills Evaluated but Omitted**:
    - `deep`: Overlay is pattern-based, not complex logic

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 8, 9, 10)
  - **Blocks**: Tasks 8, 10, 12
  - **Blocked By**: Tasks 3, 4, 5, 6 (base manifests must exist)

  **References**:

  **Pattern References**:
  - `k8s/base/kustomization.yaml` — Base kustomization that this overlay extends
  - `docker-compose.yml:62-88` — api-gateway service (primary HPA target)

  **External References**:
  - AWS ALB Ingress: https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/ingress/annotations/
  - K8s HPA: https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/
  - K8s Kustomize overlays: https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization/#bases-and-overlays

  **WHY Each Reference Matters**:
  - ALB Ingress annotations are AWS-specific — must match what the ALB Controller expects
  - HPA targets api-gateway and frontend because they handle user traffic
  - Production overlay sets namespace globally so base manifests stay namespace-agnostic

  **Acceptance Criteria**:
  - [ ] `kubectl kustomize k8s/overlays/production/` builds successfully
  - [ ] All resources have `namespace: workflowai`
  - [ ] Ingress has ALB annotations and 3 path rules (/, /health, /api/*)
  - [ ] 2 HPA objects present (api-gateway, frontend)
  - [ ] HPA min replicas >= 2

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Production overlay builds on base
    Tool: Bash
    Steps:
      1. kubectl kustomize k8s/overlays/production/ > /tmp/prod-output.yaml
      2. grep -c 'namespace: workflowai' /tmp/prod-output.yaml
      3. grep 'kind: Ingress' /tmp/prod-output.yaml
      4. grep -c 'kind: HorizontalPodAutoscaler' /tmp/prod-output.yaml
    Expected Result: All resources namespaced, 1 Ingress, 2 HPAs
    Failure Indicators: kustomize error, missing namespace, no Ingress/HPA
    Evidence: .sisyphus/evidence/task-7-production-overlay.txt

  Scenario: Ingress has correct ALB annotations
    Tool: Bash
    Steps:
      1. kubectl kustomize k8s/overlays/production/ > /tmp/prod-output.yaml
      2. grep 'alb.ingress.kubernetes.io/scheme' /tmp/prod-output.yaml
      3. grep 'internet-facing' /tmp/prod-output.yaml
    Expected Result: ALB annotations present with internet-facing scheme
    Evidence: .sisyphus/evidence/task-7-ingress-annotations.txt
  ```

  **Commit**: YES
  - Message: `feat(k8s): add production overlay, ingress, and HPA`
  - Files: `k8s/overlays/production/**`

- [ ] 8. ArgoCD Configuration (App-of-Apps Pattern)

  **What to do**:
  - Create `k8s/argocd/namespace.yaml`: argocd namespace (if not created by helm install)
  - Create `k8s/argocd/root-app.yaml`: ArgoCD Application CR (root app-of-apps)
    - Name: `workflowai-root`
    - Namespace: `argocd`
    - Source:
      - repoURL: `https://github.com/SilkLee/workflow-ai.git`
      - targetRevision: `main`
      - path: `k8s/argocd/apps`
    - Destination:
      - server: `https://kubernetes.default.svc`
      - namespace: `argocd`
    - SyncPolicy:
      - automated: prune=true, selfHeal=true
      - syncOptions: CreateNamespace=true
  - Create `k8s/argocd/apps/workflowai.yaml`: ArgoCD Application for the main app
    - Name: `workflowai`
    - Source:
      - repoURL: `https://github.com/SilkLee/workflow-ai.git`
      - targetRevision: `main`
      - path: `k8s/overlays/production`
    - Destination:
      - server: `https://kubernetes.default.svc`
      - namespace: `workflowai`
    - SyncPolicy: automated with prune and selfHeal
  - Create `k8s/argocd/projects/workflowai-project.yaml`: ArgoCD AppProject
    - Allow only workflowai namespace as destination
    - Allow only the workflowai Git repo as source

  **Must NOT do**:
  - Do NOT install ArgoCD via these manifests (that's in bootstrap script — Task 10)
  - Do NOT include ArgoCD admin credentials in these files
  - Do NOT reference private registries without IRSA in the Application CRs

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`superpowers/verification-before-completion`]
    - `superpowers/verification-before-completion`: Must validate YAML against ArgoCD CRD schema
  - **Skills Evaluated but Omitted**:
    - `deep`: ArgoCD config is declarative YAML, not complex logic

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7, 9, 10)
  - **Blocks**: Task 12 (deploy)
  - **Blocked By**: Task 7 (overlay must exist for ArgoCD to reference)

  **References**:

  **Pattern References**:
  - `k8s/overlays/production/kustomization.yaml` — Path that ArgoCD Application points to (must match exactly)

  **External References**:
  - ArgoCD Application CRD: https://argo-cd.readthedocs.io/en/stable/operator-manual/declarative-setup/
  - ArgoCD App-of-Apps: https://argo-cd.readthedocs.io/en/stable/operator-manual/cluster-bootstrapping/#app-of-apps-pattern

  **WHY Each Reference Matters**:
  - ArgoCD Application path must point to `k8s/overlays/production` (not base) — it runs kustomize build on that path
  - App-of-apps pattern enables managing the entire stack as a single ArgoCD root application
  - Git repo URL must match exactly (including .git suffix) for ArgoCD to connect

  **Acceptance Criteria**:
  - [ ] Root Application CR points to `k8s/argocd/apps` directory
  - [ ] App Application CR points to `k8s/overlays/production` path
  - [ ] Both use `automated` sync with prune and selfHeal
  - [ ] Git repo URL: `https://github.com/SilkLee/workflow-ai.git`
  - [ ] AppProject restricts to workflowai namespace only

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: ArgoCD manifests are valid YAML
    Tool: Bash
    Steps:
      1. python -c "import yaml; [yaml.safe_load(open(f)) for f in ['k8s/argocd/root-app.yaml', 'k8s/argocd/apps/workflowai.yaml']]"
      2. Verify apiVersion: argoproj.io/v1alpha1 in both files
      3. Verify kind: Application in both files
      4. Verify source.path matches expected directories
    Expected Result: Valid YAML, correct apiVersion, paths match
    Failure Indicators: YAML parse error, wrong apiVersion, wrong source.path
    Evidence: .sisyphus/evidence/task-8-argocd-config.txt

  Scenario: ArgoCD app references correct overlay path
    Tool: Bash
    Steps:
      1. grep 'path:' k8s/argocd/apps/workflowai.yaml
      2. Verify it contains 'k8s/overlays/production'
    Expected Result: path: k8s/overlays/production
    Evidence: .sisyphus/evidence/task-8-argocd-path.txt
  ```

  **Commit**: YES (groups with Task 9)
  - Message: `feat(cd): add ArgoCD config and CD pipeline`
  - Files: `k8s/argocd/**`

- [ ] 9. GitHub Actions CD Pipeline

  **What to do**:
  - Create `.github/workflows/cd.yml`:
    - Trigger: `workflow_run` on successful CI completion on `main` branch
    - OR: `push` to `main` with `paths` filter (services/**, frontend/**)
    - Concurrency: same group as CI, cancel-in-progress: false (don't cancel deploys)
    - Jobs:
      1. `detect-changes`: Use `dorny/paths-filter@v3` or diff to detect which services changed
      2. `build-push`: Matrix job for each changed service
         - Configure AWS credentials via OIDC (role from Terraform output: github_actions_role_arn)
         - Login to ECR: `aws ecr get-login-password | docker login`
         - Build: `docker build -t <ECR_URL>/<service>:sha-${{ github.sha }}` 
         - Push: `docker push <ECR_URL>/<service>:sha-${{ github.sha }}`
      3. `update-manifests`: After build-push
         - Use `kustomize edit set image` to update image tags in `k8s/overlays/production/kustomization.yaml`
         - Commit and push the tag update back to main
         - ArgoCD auto-syncs on git change (no explicit ArgoCD API call needed)
    - Environment variables from GitHub Secrets:
      - `AWS_ACCOUNT_ID`, `AWS_REGION` (ap-southeast-1)
      - OIDC: uses `aws-actions/configure-aws-credentials@v4` with `role-to-assume`

  **Must NOT do**:
  - Do NOT use static AWS access keys (use OIDC)
  - Do NOT deploy to anything other than main branch
  - Do NOT skip CI (CD only runs after successful CI)
  - Do NOT call ArgoCD API directly (rely on Git-triggered auto-sync)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`superpowers/verification-before-completion`]
    - `superpowers/verification-before-completion`: CD pipeline is critical — must validate YAML and job dependencies
  - **Skills Evaluated but Omitted**:
    - `git-master`: No complex git operations

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7, 8, 10)
  - **Blocks**: Task 12 (deploy)
  - **Blocked By**: Tasks 1 (CI pipeline), 2 (Terraform — needs ECR URLs and OIDC role ARN)

  **References**:

  **Pattern References**:
  - `.github/workflows/ci.yml` — CI pipeline (CD triggers after CI success, follow same YAML patterns)
  - `infra/terraform/outputs.tf` — Outputs: ecr_repository_urls, github_actions_role_arn, cluster_name

  **External References**:
  - aws-actions/configure-aws-credentials: https://github.com/aws-actions/configure-aws-credentials
  - GitHub OIDC: https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
  - kustomize set image: https://kubectl.docs.kubernetes.io/references/kustomize/cmd/edit/set/image/

  **WHY Each Reference Matters**:
  - CI pipeline patterns ensure consistency between CI and CD workflows
  - Terraform outputs provide the ECR URLs and IAM role ARN needed for CD
  - OIDC removes need for static AWS credentials in GitHub Secrets

  **Acceptance Criteria**:
  - [ ] CD triggers only after successful CI on main
  - [ ] Uses OIDC for AWS authentication (no static keys)
  - [ ] Builds and pushes to ECR with `sha-<commit>` tags
  - [ ] Updates kustomize image tags and commits back to main
  - [ ] ArgoCD auto-syncs (no direct ArgoCD API calls)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: CD pipeline YAML is valid
    Tool: Bash
    Steps:
      1. python -c "import yaml; yaml.safe_load(open('.github/workflows/cd.yml'))"
      2. Verify 'workflow_run' or 'push' trigger exists
      3. Verify 'aws-actions/configure-aws-credentials' step uses role-to-assume (OIDC)
      4. Verify docker build uses sha-${{ github.sha }} tag
    Expected Result: Valid YAML with OIDC auth and sha-tagged images
    Failure Indicators: YAML error, static credentials, :latest tags
    Evidence: .sisyphus/evidence/task-9-cd-pipeline.txt

  Scenario: No static AWS credentials
    Tool: Bash
    Steps:
      1. grep -r 'AWS_ACCESS_KEY_ID' .github/workflows/
      2. grep -r 'AWS_SECRET_ACCESS_KEY' .github/workflows/
    Expected Result: No matches (OIDC only)
    Evidence: .sisyphus/evidence/task-9-no-static-creds.txt
  ```

  **Commit**: YES (groups with Task 8)
  - Message: `feat(cd): add ArgoCD config and CD pipeline`
  - Files: `.github/workflows/cd.yml`

- [ ] 10. Cluster Bootstrap Script + Makefile

  **What to do**:
  - Create `infra/scripts/bootstrap-cluster.sh`:
    - Bash script with `set -euo pipefail`
    - Prerequisites check: aws, kubectl, helm, terraform (print versions)
    - Step 1: Update kubeconfig from EKS cluster
      - `aws eks update-kubeconfig --name workflowai --region ap-southeast-1`
    - Step 2: Install AWS Load Balancer Controller via Helm
      - `helm repo add eks https://aws.github.io/eks-charts`
      - `helm install aws-load-balancer-controller eks/aws-load-balancer-controller -n kube-system --set clusterName=workflowai --set serviceAccount.create=true --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=<ALB_CONTROLLER_ROLE_ARN>`
    - Step 3: Install ArgoCD via Helm
      - `helm repo add argo https://argoproj.github.io/argo-helm`
      - `helm install argocd argo/argo-cd -n argocd --create-namespace --set server.service.type=ClusterIP`
    - Step 4: Install kube-prometheus-stack via Helm
      - `helm repo add prometheus-community https://prometheus-community.github.io/helm-charts`
      - `helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace`
    - Step 5: Apply K8s secrets (prompt user or read from env)
    - Step 6: Apply ArgoCD root application
      - `kubectl apply -f k8s/argocd/root-app.yaml`
    - Step 7: Wait and verify
      - `kubectl get pods -n workflowai --watch` (with timeout)
      - Print ALB URL: `kubectl get ingress -n workflowai -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}'`
    - Make script executable: `chmod +x infra/scripts/bootstrap-cluster.sh`
  - Create `Makefile` at project root:
    - `make terraform-init`: `cd infra/terraform && terraform init`
    - `make terraform-plan`: `cd infra/terraform && terraform plan`
    - `make terraform-apply`: `cd infra/terraform && terraform apply -auto-approve`
    - `make terraform-destroy`: `cd infra/terraform && terraform destroy -auto-approve`
    - `make bootstrap`: `bash infra/scripts/bootstrap-cluster.sh`
    - `make deploy`: `kubectl apply -f k8s/argocd/root-app.yaml`
    - `make status`: `kubectl get pods -n workflowai && kubectl get ingress -n workflowai`
    - `make test-ci`: Run all tests locally (go test + pytest + jest)
    - `make docker-build`: Build all Docker images locally
    - `make clean`: `terraform destroy + kubectl delete namespace workflowai`

  **Must NOT do**:
  - Do NOT hardcode AWS account ID in scripts (read from env or terraform output)
  - Do NOT install tools (terraform, kubectl, helm) — just check they exist
  - Do NOT store secrets in the bootstrap script

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: [`superpowers/verification-before-completion`]
    - `superpowers/verification-before-completion`: Script must be checked with bash -n
  - **Skills Evaluated but Omitted**:
    - `deep`: Shell scripting + Makefile, not deep logic

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 2 (with Tasks 7, 8, 9)
  - **Blocks**: Task 12 (bootstrap is needed for deploy)
  - **Blocked By**: Tasks 2 (Terraform outputs), 7 (overlay for deploy targets)

  **References**:

  **Pattern References**:
  - `infra/terraform/outputs.tf` — Terraform outputs needed by bootstrap script (cluster_name, alb_controller_role_arn, kubeconfig_command)
  - `k8s/argocd/root-app.yaml` — ArgoCD root app that bootstrap applies

  **External References**:
  - AWS LB Controller Helm: https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/deploy/installation/
  - ArgoCD Helm: https://github.com/argoproj/argo-helm/tree/main/charts/argo-cd
  - kube-prometheus-stack: https://github.com/prometheus-community/helm-charts/tree/main/charts/kube-prometheus-stack

  **WHY Each Reference Matters**:
  - Terraform outputs provide the role ARNs and cluster name needed in the bootstrap script
  - ArgoCD Helm chart values determine how ArgoCD server is exposed and configured
  - Bootstrap script is the single entry point for going from bare EKS to fully running stack

  **Acceptance Criteria**:
  - [ ] `bash -n infra/scripts/bootstrap-cluster.sh` passes (no syntax errors)
  - [ ] Script checks prerequisites (aws, kubectl, helm)
  - [ ] Installs ALB Controller, ArgoCD, Prometheus via Helm
  - [ ] Makefile has all documented targets
  - [ ] `make help` or comments describe each target

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Bootstrap script has no syntax errors
    Tool: Bash
    Steps:
      1. bash -n infra/scripts/bootstrap-cluster.sh
      2. Verify script starts with #!/bin/bash and set -euo pipefail
      3. grep 'aws eks update-kubeconfig' infra/scripts/bootstrap-cluster.sh
      4. grep 'helm install' infra/scripts/bootstrap-cluster.sh (should appear 3 times)
    Expected Result: No syntax errors, proper shebang, 3 helm install commands
    Failure Indicators: bash -n returns errors, missing helm installs
    Evidence: .sisyphus/evidence/task-10-bootstrap-syntax.txt

  Scenario: Makefile has all targets
    Tool: Bash
    Steps:
      1. grep '^[a-z].*:' Makefile
      2. Verify targets include: terraform-init, terraform-plan, terraform-apply, terraform-destroy, bootstrap, deploy, status, test-ci, docker-build, clean
    Expected Result: All 10 targets present
    Failure Indicators: Missing targets
    Evidence: .sisyphus/evidence/task-10-makefile-targets.txt
  ```

  **Commit**: YES
  - Message: `feat(infra): add cluster bootstrap script and Makefile`
  - Files: `infra/scripts/bootstrap-cluster.sh`, `Makefile`

### Wave 3 — Deployment (After Wave 2, sequential)

- [ ] 11. Terraform Apply (Create AWS Resources)

  **What to do**:
  - **NOTE**: This task creates REAL AWS resources and costs money. Must be run from user's terminal (terraform, aws CLI not available in dev env).
  - Step 1: Bootstrap Terraform state backend
    - `cd infra/terraform/bootstrap && terraform init && terraform apply -auto-approve`
    - Creates S3 bucket and DynamoDB table for state locking
  - Step 2: Initialize main Terraform
    - `cd infra/terraform && terraform init`
    - Migrate to S3 backend
  - Step 3: Plan and review
    - `terraform plan -out=tfplan`
    - Review plan output for expected resources: VPC, EKS, 8 ECR repos, IAM roles, ALB-related resources
  - Step 4: Apply
    - `terraform apply tfplan`
    - Expected time: 15-25 minutes (EKS cluster creation is slow)
  - Step 5: Capture outputs
    - `terraform output -json > /tmp/terraform-outputs.json`
    - Record: cluster_endpoint, ecr_repository_urls, github_actions_role_arn, alb_controller_role_arn
  - Step 6: Configure GitHub Secrets
    - `gh secret set AWS_ACCOUNT_ID --body "<account-id>"`
    - `gh secret set AWS_REGION --body "ap-southeast-1"`
    - `gh secret set AWS_ROLE_ARN --body "<github_actions_role_arn from terraform output>"`

  **Must NOT do**:
  - Do NOT create resources outside ap-southeast-1
  - Do NOT use multiple NAT gateways
  - Do NOT skip `terraform plan` review
  - Do NOT commit terraform.tfstate or .terraform/ to git

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`superpowers/verification-before-completion`]
    - `superpowers/verification-before-completion`: Must verify terraform outputs and resource creation
  - **Skills Evaluated but Omitted**:
    - `quick`: AWS provisioning is multi-step and requires careful verification

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential with Task 12)
  - **Blocks**: Task 12 (need running EKS + ECR before bootstrap/deploy)
  - **Blocked By**: Task 2 (Terraform IaC files must exist)

  **References**:

  **Pattern References**:
  - `infra/terraform/bootstrap/main.tf` — State backend bootstrap (must run first)
  - `infra/terraform/variables.tf` — Variables with defaults (region, cluster_name, node type)
  - `infra/terraform/outputs.tf` — Outputs needed for subsequent tasks

  **WHY Each Reference Matters**:
  - Bootstrap must run BEFORE main terraform init (state backend must exist)
  - Terraform outputs feed into bootstrap script, CD pipeline, and GitHub Secrets
  - Plan review catches unexpected resources or costs before apply

  **Acceptance Criteria**:
  - [ ] S3 state bucket `workflowai-terraform-state` exists
  - [ ] DynamoDB table `workflowai-terraform-locks` exists
  - [ ] EKS cluster `workflowai` is ACTIVE
  - [ ] 8 ECR repositories created
  - [ ] `terraform plan -detailed-exitcode` exits 0 (no drift)
  - [ ] GitHub Secrets configured (AWS_ACCOUNT_ID, AWS_REGION, AWS_ROLE_ARN)

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Terraform created all expected resources
    Tool: Bash
    Steps:
      1. cd infra/terraform && terraform output -json
      2. Verify cluster_name = "workflowai"
      3. Count ecr_repository_urls (should be 8)
      4. Verify github_actions_role_arn is not empty
      5. aws eks describe-cluster --name workflowai --query 'cluster.status'
    Expected Result: cluster status ACTIVE, 8 ECR URLs, role ARN present
    Failure Indicators: Cluster not ACTIVE, missing ECR repos, empty role ARN
    Evidence: .sisyphus/evidence/task-11-terraform-outputs.txt

  Scenario: No Terraform drift
    Tool: Bash
    Steps:
      1. cd infra/terraform && terraform plan -detailed-exitcode
    Expected Result: Exit code 0 (no changes needed)
    Failure Indicators: Exit code 2 (changes detected)
    Evidence: .sisyphus/evidence/task-11-no-drift.txt
  ```

  **Commit**: YES
  - Message: `feat: deploy to EKS — live URL verified`
  - Files: (any deployment fixes, .gitignore updates for terraform state)

- [ ] 12. Cluster Bootstrap + Deploy Services

  **What to do**:
  - **NOTE**: Must be run from user's terminal with kubectl, helm, aws CLI available.
  - Step 1: Run bootstrap script
    - `make bootstrap` (or `bash infra/scripts/bootstrap-cluster.sh`)
    - This installs: ALB Controller, ArgoCD, kube-prometheus-stack
    - Wait for all bootstrap pods to be Ready
  - Step 2: Create K8s secrets
    - `kubectl create secret generic workflowai-secrets -n workflowai --from-literal=POSTGRES_USER=workflowai --from-literal=POSTGRES_PASSWORD=<password> --from-literal=POSTGRES_DB=workflowai --from-literal=JWT_SECRET=<secret> --from-literal=OPENAI_API_KEY=<key>`
    - OR apply the secrets.yaml with real base64 values
  - Step 3: Push Docker images to ECR (first time)
    - For each service: build locally and push to ECR with `sha-<commit>` tag
    - OR: Push to main to trigger CD pipeline which builds and pushes automatically
  - Step 4: Apply ArgoCD root application
    - `kubectl apply -f k8s/argocd/root-app.yaml`
    - ArgoCD picks up the root app, discovers child apps, syncs all
  - Step 5: Wait for pods
    - `kubectl get pods -n workflowai -w` (watch until all Running)
    - Expected: 7 Deployments running + 3 StatefulSets running
  - Step 6: Get ALB URL
    - `kubectl get ingress -n workflowai -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}'`
    - Takes 2-5 minutes for ALB to provision
    - Test: `curl http://<ALB_URL>/health`

  **Must NOT do**:
  - Do NOT expose ArgoCD server externally (ClusterIP only, use port-forward)
  - Do NOT skip waiting for bootstrap pods before deploying app
  - Do NOT hardcode secrets in any committed file

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`superpowers/verification-before-completion`]
    - `superpowers/verification-before-completion`: Must verify all pods running and ALB accessible
  - **Skills Evaluated but Omitted**:
    - `quick`: Multi-step deployment with waits and verification

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (sequential after Task 11)
  - **Blocks**: Task 13 (verification needs running services)
  - **Blocked By**: Tasks 7, 8, 9, 10, 11 (all infrastructure + manifests + AWS resources)

  **References**:

  **Pattern References**:
  - `infra/scripts/bootstrap-cluster.sh` — Bootstrap script to run
  - `k8s/argocd/root-app.yaml` — ArgoCD root application to apply
  - `k8s/base/secrets.yaml` — Template for K8s secrets (replace placeholders)

  **WHY Each Reference Matters**:
  - Bootstrap script is the single entry point for cluster setup
  - Secrets must be created BEFORE ArgoCD syncs (pods will fail without them)
  - ArgoCD root-app triggers cascading deployment of all services

  **Acceptance Criteria**:
  - [ ] ALB Controller pods running in kube-system
  - [ ] ArgoCD pods running in argocd namespace
  - [ ] kube-prometheus-stack pods running in monitoring namespace
  - [ ] All 7 Deployment pods Running in workflowai namespace
  - [ ] All 3 StatefulSet pods Running in workflowai namespace
  - [ ] ALB URL provisioned and accessible
  - [ ] `curl http://<ALB_URL>/health` returns healthy response

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: All pods are running
    Tool: Bash
    Steps:
      1. kubectl get pods -n workflowai --no-headers
      2. Count total pods (should be 10: 7 deployments + 3 statefulsets)
      3. Count pods NOT in Running/Completed state
    Expected Result: 10 pods, all Running
    Failure Indicators: Pods in CrashLoopBackOff, Pending, or ImagePullBackOff
    Evidence: .sisyphus/evidence/task-12-pod-status.txt

  Scenario: ALB URL is accessible
    Tool: Bash
    Steps:
      1. ALB_URL=$(kubectl get ingress -n workflowai -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}')
      2. curl -s -o /dev/null -w '%{http_code}' http://$ALB_URL/
      3. curl -s http://$ALB_URL/health
    Expected Result: HTTP 200 for frontend, healthy response for /health
    Failure Indicators: Connection refused, 503, 504, or non-200 status
    Evidence: .sisyphus/evidence/task-12-alb-accessible.txt

  Scenario: ArgoCD shows Synced
    Tool: Bash
    Steps:
      1. kubectl get applications -n argocd
      2. Check all applications show Synced and Healthy
    Expected Result: All ArgoCD applications Synced/Healthy
    Evidence: .sisyphus/evidence/task-12-argocd-status.txt
  ```

  **Commit**: YES (groups with Task 11)
  - Message: `feat: deploy to EKS — live URL verified`
  - Files: (any fixes needed during deployment)

### Wave 4 — Verification + Docs (After Wave 3)

- [ ] 13. End-to-End Verification

  **What to do**:
  - Comprehensive verification of the entire deployed stack:
  - Step 1: Infrastructure verification
    - `kubectl get nodes` — 2+ nodes Ready
    - `kubectl get pods -A` — All system pods healthy
    - `kubectl top nodes` — Resource usage within limits
  - Step 2: Application verification
    - `curl http://<ALB_URL>/` — Frontend loads (200)
    - `curl http://<ALB_URL>/health` — API Gateway healthy
    - `curl http://<ALB_URL>/api/v1/health` — If proxied correctly
    - Verify each service pod logs show successful startup
  - Step 3: CI/CD verification
    - Push a minor change to trigger CI
    - `gh run list --workflow=ci.yml --limit=1` — CI passes
    - Verify CD triggers after CI success
    - Verify new images appear in ECR
    - Verify ArgoCD detects and syncs the change
  - Step 4: Monitoring verification
    - `kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n monitoring 9090:9090`
    - Verify Prometheus has active scrape targets
    - `kubectl port-forward svc/prometheus-grafana -n monitoring 3001:80`
    - Verify Grafana loads with data sources configured
  - Step 5: ArgoCD verification
    - `kubectl port-forward svc/argocd-server -n argocd 8080:443`
    - Access ArgoCD UI, verify all apps Synced/Healthy
  - Step 6: Screenshot/evidence capture
    - Capture terminal output of all verification commands
    - Screenshot ArgoCD UI showing sync status (if possible)

  **Must NOT do**:
  - Do NOT skip any verification step
  - Do NOT modify application code to "fix" issues (flag them instead)

  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: [`superpowers/verification-before-completion`]
    - `superpowers/verification-before-completion`: This IS the verification task
  - **Skills Evaluated but Omitted**:
    - `playwright`: No browser-based verification needed (curl-based)

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (sequential)
  - **Blocks**: Task 14
  - **Blocked By**: Task 12 (all services must be deployed)

  **References**:

  **Pattern References**:
  - This plan's "Success Criteria" section — Contains all verification commands to run
  - `k8s/overlays/production/ingress.yaml` — ALB URL and path routing rules

  **WHY Each Reference Matters**:
  - Success criteria define exactly what "done" looks like — run every command listed there
  - Ingress rules determine what paths are available on the ALB URL

  **Acceptance Criteria**:
  - [ ] All Success Criteria verification commands pass
  - [ ] CI pipeline triggered and passed on push
  - [ ] CD pipeline built and pushed images to ECR
  - [ ] ArgoCD auto-synced the new images
  - [ ] Prometheus has active scrape targets
  - [ ] Evidence files captured in .sisyphus/evidence/

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: Full stack E2E verification
    Tool: Bash
    Steps:
      1. kubectl get nodes (2+ Ready)
      2. kubectl get pods -n workflowai --no-headers | wc -l (10+ pods)
      3. curl -s http://<ALB_URL>/ (HTTP 200)
      4. curl -s http://<ALB_URL>/health (healthy)
      5. gh run list --workflow=ci.yml --limit=1 --json conclusion (success)
      6. kubectl get applications -n argocd -o jsonpath='{.items[*].status.sync.status}' (Synced)
    Expected Result: All checks pass
    Failure Indicators: Any check returns unexpected result
    Evidence: .sisyphus/evidence/task-13-e2e-verification.txt

  Scenario: Monitoring stack operational
    Tool: Bash
    Steps:
      1. kubectl get pods -n monitoring (all Running)
      2. kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n monitoring 9090:9090 &
      3. curl -s http://localhost:9090/api/v1/targets | python -c "import json,sys; d=json.load(sys.stdin); print(len(d['data']['activeTargets']))"
    Expected Result: 1+ active Prometheus targets
    Evidence: .sisyphus/evidence/task-13-monitoring.txt
  ```

  **Commit**: NO (verification only, no file changes)

- [ ] 14. Update README + Final Commit + Push

  **What to do**:
  - Update `README.md` Week 11 section:
    - Change `📝 **Week 11**` to `✅ **Week 11**: CI/CD pipeline + cloud deployment`
    - Add Week 11 details:
      - ✅ GitHub Actions CI (matrix: Go, Python, Frontend tests + linting)
      - ✅ GitHub Actions CD (auto-deploy on push to main)
      - ✅ Terraform IaC (VPC, EKS, ECR, IAM — ap-southeast-1)
      - ✅ Kubernetes manifests (Kustomize: Deployments, Services, StatefulSets, Ingress, HPA)
      - ✅ ArgoCD GitOps (app-of-apps, automated sync + prune + selfHeal)
      - ✅ Finetune Dockerfile added
      - ✅ Cluster bootstrap (ALB Controller, kube-prometheus-stack, ArgoCD)
      - ✅ Live deployment: `http://<ALB_URL>` (EKS, ap-southeast-1)
    - Add deployment section to README (how to deploy from scratch)
    - Add teardown instructions (`make terraform-destroy`)
  - Update "Last Updated" date
  - Final commit and push

  **Must NOT do**:
  - Do NOT remove or modify any previous Week entries
  - Do NOT add the actual ALB URL to the README (it changes)
  - Do NOT commit any secret values

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: [`superpowers/verification-before-completion`, `git-master`]
    - `superpowers/verification-before-completion`: Verify README renders correctly
    - `git-master`: Final commit + push with proper message
  - **Skills Evaluated but Omitted**:
    - `writing`: README update is structured, not creative writing

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 4 (after Task 13)
  - **Blocks**: None (final task)
  - **Blocked By**: Task 13 (all verification must pass first)

  **References**:

  **Pattern References**:
  - `README.md` — Current README with Week 10 as latest complete week
  - Previous week entries in README — Follow same format for Week 11 entry

  **WHY Each Reference Matters**:
  - README format must be consistent with previous weeks
  - Deployment instructions enable anyone to reproduce the setup

  **Acceptance Criteria**:
  - [ ] README shows Week 11 as ✅ complete
  - [ ] Deployment instructions added
  - [ ] Teardown instructions added
  - [ ] All changes committed and pushed to origin/main
  - [ ] `git status` shows clean working directory

  **QA Scenarios (MANDATORY):**

  ```
  Scenario: README is updated correctly
    Tool: Bash
    Steps:
      1. grep 'Week 11' README.md
      2. Verify ✅ prefix (not 📝)
      3. grep 'terraform-destroy' README.md (teardown docs present)
      4. grep 'Last Updated' README.md (date updated)
    Expected Result: Week 11 marked complete, teardown docs present, date current
    Failure Indicators: Still shows 📝, missing teardown, old date
    Evidence: .sisyphus/evidence/task-14-readme.txt

  Scenario: All changes pushed to remote
    Tool: Bash
    Steps:
      1. git status (clean working directory)
      2. git log --oneline -5 (verify Week 11 commits)
      3. git push origin main --dry-run (verify pushable)
    Expected Result: Clean status, Week 11 commits visible, push succeeds
    Evidence: .sisyphus/evidence/task-14-git-status.txt
  ```

  **Commit**: YES
  - Message: `docs: update README — mark Week 11 complete with deployment instructions`
  - Files: `README.md`
  - Post-commit: `git push origin main`

---

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

> 4 review agents run in PARALLEL. ALL must APPROVE. Rejection → fix → re-run.

- [ ] F1. **Plan Compliance Audit** — `oracle`
  Read the plan end-to-end. For each "Must Have": verify implementation exists (read file, curl endpoint, run command). For each "Must NOT Have": search codebase for forbidden patterns — reject with file:line if found. Check evidence files exist in .sisyphus/evidence/. Compare deliverables against plan.
  Output: `Must Have [N/N] | Must NOT Have [N/N] | Tasks [N/N] | VERDICT: APPROVE/REJECT`

- [ ] F2. **Code Quality Review** — `unspecified-high`
  Run terraform validate + terraform fmt -check. Validate all YAML (K8s manifests, GitHub Actions). Check for hardcoded secrets in any committed file. Check all K8s manifests use specific image tags (no `:latest`). Verify all health probes use `httpGet`. Check Terraform uses pinned versions.
  Output: `Terraform [PASS/FAIL] | K8s YAML [PASS/FAIL] | Secrets [CLEAN/LEAK] | VERDICT`

- [ ] F3. **Real Manual QA** — `unspecified-high`
  Verify: CI pipeline passes on GitHub. All ECR repos have images. kubectl get nodes shows Ready. kubectl get pods -n workflowai shows all Running. ALB URL returns frontend (200) and /health (healthy). ArgoCD shows Synced/Healthy. Prometheus has active targets.
  Output: `CI [PASS/FAIL] | ECR [N/N images] | Pods [N/N running] | ALB [PASS/FAIL] | VERDICT`

- [ ] F4. **Scope Fidelity Check** — `deep`
  For each task: read "What to do", read actual files created. Verify 1:1 — everything in spec was built (no missing), nothing beyond spec was built (no creep). Check "Must NOT do" compliance (no app code changes, no Helm charts for app, no `:latest` tags). Flag unaccounted changes.
  Output: `Tasks [N/N compliant] | Guardrails [CLEAN/N violations] | VERDICT`

---

## Commit Strategy

- **Commit 1**: `feat(ci): add GitHub Actions CI pipeline with matrix testing` — .github/workflows/ci.yml
- **Commit 2**: `feat(infra): add Terraform IaC for VPC, EKS, ECR, IAM` — infra/terraform/**
- **Commit 3**: `feat(k8s): add Kubernetes base manifests with Kustomize` — k8s/base/**
- **Commit 4**: `feat(k8s): add production overlay, ingress, and HPA` — k8s/overlays/**, k8s/base/ingress.yaml
- **Commit 5**: `feat(cd): add ArgoCD config and CD pipeline` — k8s/argocd/**, .github/workflows/cd.yml
- **Commit 6**: `feat(infra): add cluster bootstrap script and Makefile` — infra/scripts/**, Makefile
- **Commit 7**: `feat(finetune): add Dockerfile for finetune service` — services/finetune/Dockerfile
- **Commit 8**: `feat: deploy to EKS — live URL verified` — (any deployment fixes)
- **Commit 9**: `docs: update README — mark Week 11 complete with deployment instructions`

---

## Success Criteria

### Verification Commands
```bash
# CI passes
gh run list --workflow=ci.yml --limit=1 --json conclusion -q '.[0].conclusion'  # Expected: "success"

# Terraform is clean
cd infra/terraform && terraform plan -detailed-exitcode  # Expected: exit 0

# EKS cluster healthy
kubectl get nodes  # Expected: 2+ nodes in Ready status

# All pods running
kubectl get pods -n workflowai --no-headers | grep -v Running | wc -l  # Expected: 0

# Frontend accessible
curl -s -o /dev/null -w '%{http_code}' http://<ALB_URL>/  # Expected: 200

# API health
curl -s http://<ALB_URL>/health | jq -r '.status'  # Expected: "healthy"

# ArgoCD synced
kubectl get applications -n argocd -o jsonpath='{.items[*].status.sync.status}'  # Expected: "Synced"

# Prometheus scraping
kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n monitoring 9090:9090 &
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets | length'  # Expected: > 0
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] All existing 470 tests still pass in CI
- [ ] Live URL accessible from browser
- [ ] README updated with Week 11 section
