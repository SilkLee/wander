# CI/CD System Architecture

> Complete pipeline design: GitHub Actions CI matrix, CD with ECR + Kustomize, ArgoCD GitOps, security model, and operational runbook

---

## Pipeline Overview

```
                           Push / PR to any branch
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │         CI Pipeline            │
                    │   (GitHub Actions — ci.yml)    │
                    │                                │
                    │  ┌─── Test Matrix (8 jobs) ───┐│
                    │  │ Go ×2   Python ×5  React ×1││
                    │  └────────────────────────────┘│
                    │  ┌─── Lint Matrix (7 jobs) ───┐│
                    │  │ golangci ×2   ruff ×5      ││
                    │  └────────────────────────────┘│
                    │        Total: 15 jobs           │
                    └───────────────┬───────────────┘
                                    │ on success (main only)
                                    ▼
                    ┌───────────────────────────────┐
                    │         CD Pipeline            │
                    │   (GitHub Actions — cd.yml)    │
                    │                                │
                    │  1. Detect changed services     │
                    │  2. Build Docker images          │
                    │  3. Push to ECR (sha-<commit>)  │
                    │  4. Update kustomization.yaml   │
                    │  5. Commit + push tag update    │
                    └───────────────┬───────────────┘
                                    │ git change detected
                                    ▼
                    ┌───────────────────────────────┐
                    │     ArgoCD GitOps Sync         │
                    │                                │
                    │  • Auto-sync on git change      │
                    │  • selfHeal: true               │
                    │  • Prune orphaned resources     │
                    │  • app-of-apps pattern           │
                    └───────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────────┐
                    │    AWS EKS Cluster              │
                    │    Namespace: workflowai        │
                    │    13 pods (8 services + infra)  │
                    └───────────────────────────────┘
```

---

## CI Pipeline (`ci.yml`)

### Trigger & Concurrency

```yaml
on:
  push:
    branches: ["**"]        # All branches — every push triggers CI
  pull_request:
    branches: [main]        # PRs targeting main

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true  # Supersede stale runs on same branch
```

**Design rationale**: Every push gets tested — no "merge and pray". Concurrency cancellation prevents queue pileup during rapid iteration.

### Job Matrix (15 jobs total)

```
┌─────────────────────────────────────────────────────────────────┐
│                        CI Job Matrix                             │
├──────────────────────┬──────────────────────────────────────────┤
│  TEST JOBS (8)       │  LINT JOBS (7)                           │
├──────────────────────┼──────────────────────────────────────────┤
│  Test Go             │  Lint Go                                 │
│  ├── api-gateway     │  ├── api-gateway  (golangci-lint)        │
│  └── ingestion       │  └── ingestion    (golangci-lint)        │
│                      │                                          │
│  Test Python         │  Lint Python                             │
│  ├── agent-orchestr. │  ├── agent-orchestrator  (ruff)          │
│  ├── indexing        │  ├── indexing            (ruff)          │
│  ├── model-service   │  ├── model-service       (ruff)          │
│  └── finetune        │  ├── metrics             (ruff)          │
│                      │  └── finetune            (ruff)          │
│  Test Python (DB)    │                                          │
│  └── metrics  ←───── PostgreSQL 15 sidecar                      │
│                      │                                          │
│  Test Frontend       │                                          │
│  └── React (Jest)    │                                          │
└──────────────────────┴──────────────────────────────────────────┘
```

All jobs use `fail-fast: false` — one failure doesn't cancel siblings, so you get the full picture in a single run.

### Job Details

#### Go Tests (2 jobs)

| Setting | Value |
|---------|-------|
| Runner | `ubuntu-latest` |
| Go version | 1.22 |
| Cache | `~/.cache/go-build` + `~/go/pkg/mod`, keyed on `go.sum` |
| Command | `go test -v -short ./...` |
| Services | api-gateway, ingestion |

#### Python Tests (4 jobs, no DB)

| Setting | Value |
|---------|-------|
| Runner | `ubuntu-latest` |
| Python version | 3.11 |
| Cache | `~/.cache/pip`, keyed on `pyproject.toml` |
| Install | `pip install --extra-index-url https://download.pytorch.org/whl/cpu -e '.[dev]'` |
| Command | `python -m pytest tests/ -v --tb=short` |
| Services | agent-orchestrator, indexing, model-service, finetune |

**Note**: PyTorch CPU-only wheel index avoids downloading ~2GB GPU builds, cutting install time from ~4min to ~90s.

#### Python Tests — Metrics (1 job, with PostgreSQL)

| Setting | Value |
|---------|-------|
| Runner | `ubuntu-latest` + PostgreSQL 15 sidecar |
| Database | `postgresql+asyncpg://workflowai:test_password@localhost:5432/workflowai_test` |
| Health check | `pg_isready`, 10s interval, 5 retries |
| Service | metrics |

The metrics service is the only Python service requiring a real database in CI. All others mock their external dependencies.

#### Frontend Tests (1 job)

| Setting | Value |
|---------|-------|
| Runner | `ubuntu-latest` |
| Node.js | 20 |
| Cache | npm, keyed on `frontend/package-lock.json` |
| Install | `npm ci` |
| Command | `npx jest` |

#### Go Lint (2 jobs)

| Setting | Value |
|---------|-------|
| Linter | `golangci-lint` (latest via official action) |
| Services | api-gateway, ingestion |

#### Python Lint (5 jobs)

| Setting | Value |
|---------|-------|
| Linter | `ruff check .` |
| Services | agent-orchestrator, indexing, model-service, metrics, finetune |

### Test Suite Summary

| Category | Tests | Pass | Skip | Fail |
|----------|-------|------|------|------|
| Go (api-gateway) | ~60 | 60 | 0 | 0 |
| Go (ingestion) | ~40 | 40 | 0 | 0 |
| Python (agent-orchestrator) | ~80 | 73 | 7 | 0 |
| Python (indexing) | ~50 | 47 | 3 | 0 |
| Python (model-service) | ~40 | 38 | 2 | 0 |
| Python (metrics) | ~60 | 60 | 0 | 0 |
| Python (finetune) | ~30 | 30 | 0 | 0 |
| Frontend (React) | ~110 | 110 | 0 | 0 |
| **Total** | **~470** | **458** | **12** | **0** |

Skipped tests are for GPU-dependent or external-API features not available in CI.

---

## CD Pipeline (`cd.yml`)

### Trigger

```yaml
on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main]

concurrency:
  group: cd-${{ github.ref }}
  cancel-in-progress: false  # CD must finish — no cancellation
```

**Design**: CD only fires after CI **succeeds** on `main`. The `cancel-in-progress: false` ensures a deploy is never interrupted mid-push.

### Stage 1: Gate Check

```
┌──────────────────────────┐
│  check-ci                │
│  if: conclusion == 'success'
│  output: triggering SHA  │
└────────────┬─────────────┘
             │ SHA
             ▼
```

Extracts the triggering commit SHA for all downstream stages. If CI failed, the entire CD pipeline is skipped.

### Stage 2: Change Detection

```
┌──────────────────────────────────────────────────┐
│  detect-changes  (dorny/paths-filter@v3)          │
│                                                    │
│  services/api-gateway/**       → api-gateway       │
│  services/ingestion/**         → ingestion         │
│  services/agent-orchestrator/**→ agent-orchestrator │
│  services/indexing/**          → indexing           │
│  services/model-service/**     → model-service     │
│  services/metrics/**           → metrics           │
│  services/finetune/**          → finetune          │
│  frontend/**                   → frontend          │
│                                                    │
│  Output: boolean per service (changed/unchanged)   │
└──────────────────────────────────────────────────┘
```

**Why path filtering?** Only rebuild what changed. A metrics-only change doesn't rebuild all 8 images — saves ~15min and avoids unnecessary ECR pushes.

### Stage 3: Build & Push to ECR

```
┌───────────────────────────────────────────────────┐
│  build-push  (matrix: 8 services)                  │
│                                                     │
│  For each changed service:                          │
│  1. Checkout at triggering SHA                      │
│  2. AWS OIDC credentials (STS assume-role)          │
│  3. ECR login                                       │
│  4. docker build -t <ECR>/workflowai/<svc>:sha-xxx  │
│  5. docker push                                     │
│                                                     │
│  Unchanged services: skip (echo "unchanged")        │
└───────────────────────────────────────────────────┘
```

**Image tagging strategy**: `sha-<commit>` — no `:latest`, ever. Every image is traceable to an exact commit. Rollback = point to a previous SHA tag.

### Stage 4: Update Kustomize Manifests

```
┌──────────────────────────────────────────────────────┐
│  update-manifests                                     │
│                                                        │
│  1. Checkout main (latest)                             │
│  2. cd k8s/overlays/production                         │
│  3. kustomize edit set image (all 8 services)          │
│  4. git commit -m "chore(deploy): update tags [skip ci]"│
│  5. git push origin main                               │
│                                                        │
│  The [skip ci] suffix prevents infinite CI → CD loop   │
└──────────────────────────────────────────────────────┘
```

This commit updates `k8s/overlays/production/kustomization.yaml` with the new image tags. ArgoCD watches this file.

---

## ArgoCD GitOps

### Architecture

```
┌─── ArgoCD Namespace ─────────────────────────────────────┐
│                                                           │
│  root-app (Application)                                   │
│  ├── source: k8s/argocd/apps/                            │
│  ├── syncPolicy: automated (prune + selfHeal)            │
│  │                                                       │
│  ├──► workflowai (Application)                           │
│  │    ├── source: k8s/overlays/production/               │
│  │    ├── syncPolicy: automated (prune + selfHeal)       │
│  │    ├── ignoreDifferences:                             │
│  │    │   └── Secret/workflowai-secrets /data            │
│  │    │       (preserves runtime-applied secrets)        │
│  │    │                                                  │
│  │    └──► workflowai Namespace                          │
│  │         ├── 8 Deployments (services)                   │
│  │         ├── 8 Services (ClusterIP)                     │
│  │         ├── 3 StatefulSets (PG, Redis, ES)            │
│  │         ├── 3 PVCs (model-cache, index-cache, agent)  │
│  │         ├── 1 Ingress (ALB, path-based)               │
│  │         ├── 2 HPAs (api-gateway, frontend)            │
│  │         ├── ConfigMaps + Secrets                       │
│  │         └── Namespace manifest                         │
│  │                                                       │
│  └──► workflowai-policies (Application)                  │
│       ├── source: k8s/policies/                           │
│       ├── syncPolicy: automated (prune + selfHeal)       │
│       │                                                  │
│       └──► Cluster-scoped ClusterPolicies                │
│            ├── disallow-latest-tag                        │
│            ├── require-resource-limits                    │
│            ├── require-labels                             │
│            ├── require-probes                             │
│            ├── restrict-image-registries                  │
│            └── disallow-privilege-escalation              │
└───────────────────────────────────────────────────────────┘
```

### App-of-Apps Pattern

1. **Root App** (`k8s/argocd/root-app.yaml`): Points to `k8s/argocd/apps/` — manages child Application resources
2. **WorkflowAI App** (`k8s/argocd/apps/workflowai.yaml`): Points to `k8s/overlays/production/` — manages all workload manifests
3. **Policies App** (`k8s/argocd/apps/policies.yaml`): Points to `k8s/policies/` — manages Kyverno ClusterPolicy resources

This two-level structure means adding a new environment (staging, canary) or cross-cutting concern (policies, RBAC) only requires adding a new child Application YAML.

### Sync Policy

| Setting | Value | Rationale |
|---------|-------|-----------|
| `automated.prune` | `true` | Removes resources deleted from git |
| `automated.selfHeal` | `true` | Reverts any manual `kubectl` changes |
| `CreateNamespace` | `true` | Auto-creates namespace on first deploy |
| `RespectIgnoreDifferences` | `true` | Honors `ignoreDifferences` during sync |

### selfHeal Implications

**Critical lesson learned**: `selfHeal: true` means git is the **only** way to change cluster state. Direct `kubectl patch` on ConfigMaps or Deployments gets reverted within seconds. All changes must flow through:

```
Code change → git commit → git push → ArgoCD detects → sync
```

The `ignoreDifferences` on `Secret/workflowai-secrets /data` is the only exception — allows runtime-applied secrets (via `kubectl create secret`) to persist without being overwritten by git.

---

## Security Model

### Zero Long-Lived Credentials

```
┌── GitHub Actions ──────────────────────────────────────────┐
│                                                             │
│  CI Job                                                     │
│  └── No AWS credentials needed (tests only)                │
│                                                             │
│  CD Job                                                     │
│  └── OIDC Federation:                                       │
│      1. GitHub mints OIDC JWT token                         │
│      2. AWS STS validates token via OIDC Provider           │
│      3. AssumeRoleWithWebIdentity → temporary credentials  │
│      4. Credentials expire after job (~15min TTL)           │
│                                                             │
│  Role: arn:aws:iam::<ACCOUNT>:role/github-actions-workflowai│
│  Trust: GitHub OIDC provider (repo: SilkLee/workflow-ai)   │
│  Permissions: ECR push, EKS describe (least privilege)      │
└─────────────────────────────────────────────────────────────┘
```

**No `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` stored anywhere.** GitHub's OIDC token is exchanged for short-lived STS credentials on every CD run.

### Kubernetes Secrets

| Secret | Storage | Management |
|--------|---------|------------|
| `workflowai-secrets` | K8s Secret object | `kubectl create secret` at bootstrap |
| Database password | K8s Secret → env var | Referenced via `secretKeyRef` in Deployments |
| JWT signing key | K8s Secret → env var | Referenced via `secretKeyRef` in api-gateway |
| OpenRouter API key | K8s Secret → env var | Referenced via `secretKeyRef` in model-service |

Secrets are **never** committed to git. The ArgoCD `ignoreDifferences` on the Secret ensures runtime-created secrets survive syncs.

### IAM & IRSA

```
┌── AWS IAM ────────────────────────────────────────┐
│                                                     │
│  OIDC Provider                                      │
│  ├── GitHub Actions (CD pipeline authentication)   │
│  └── EKS cluster (pod-level AWS access via IRSA)   │
│                                                     │
│  IRSA Roles (IAM Roles for Service Accounts)       │
│  └── Pods assume AWS roles via K8s ServiceAccount  │
│      annotation → STS AssumeRoleWithWebIdentity    │
└─────────────────────────────────────────────────────┘
```

---

## Kubernetes Manifest Structure

### Kustomize Layout

```
k8s/
├── base/                              # Shared manifests (all environments)
│   ├── kustomization.yaml             # Resource list
│   ├── namespace.yaml                 # workflowai namespace
│   ├── configmap.yaml                 # Shared config (service URLs, ports)
│   ├── secrets.yaml                   # Secret template (empty, runtime-filled)
│   ├── postgres-init-configmap.yaml   # DB init SQL
│   │
│   ├── api-gateway-deployment.yaml    # Go service deployments
│   ├── ingestion-deployment.yaml
│   ├── agent-orchestrator-deployment.yaml  # Python service deployments
│   ├── indexing-deployment.yaml
│   ├── model-service-deployment.yaml
│   ├── metrics-deployment.yaml
│   ├── finetune-deployment.yaml
│   ├── frontend-deployment.yaml
│   │
│   ├── *-service.yaml                 # ClusterIP services (8 total)
│   ├── postgres-statefulset.yaml      # Database (PVC-backed)
│   ├── redis-statefulset.yaml         # Cache/queue (PVC-backed)
│   ├── elasticsearch-statefulset.yaml # Search (PVC-backed)
│   ├── *-pvc.yaml                     # Persistent volume claims (3)
│   └── frontend-nginx-configmap.yaml  # nginx reverse proxy config
│
├── overlays/
│   └── production/
│       ├── kustomization.yaml         # Image tags (sha-<commit>), patches
│       ├── resource-patches.yaml      # CPU/memory limits for production
│       ├── ingress.yaml               # ALB Ingress (internet-facing)
│       ├── hpa-api-gateway.yaml       # HorizontalPodAutoscaler
│       └── hpa-frontend.yaml          # HorizontalPodAutoscaler
│
├── policies/                           # Kyverno ClusterPolicy resources
│   ├── kustomization.yaml             # Policy resource list
│   ├── disallow-latest-tag.yaml       # Reject :latest image tags
│   ├── require-resource-limits.yaml   # Require CPU/memory limits
│   ├── require-labels.yaml            # Require app + part-of labels
│   ├── require-probes.yaml            # Require readiness + liveness probes
│   ├── restrict-image-registries.yaml # Allow only ECR + Docker Hub
│   └── disallow-privilege-escalation.yaml # Block privileged containers
│
└── argocd/
    ├── root-app.yaml                  # Root Application (app-of-apps)
    ├── apps/
    │   ├── workflowai.yaml            # Child Application (workloads)
    │   └── policies.yaml              # Child Application (Kyverno policies)
    └── projects/
        └── workflowai-project.yaml    # ArgoCD AppProject (RBAC)
```

### ALB Ingress Routing

```
ALB (internet-facing, HTTP:80)
│
├── /api/*     → api-gateway:8000     (all API traffic)
├── /health    → api-gateway:8000     (health check)
└── /*         → frontend:3000        (React SPA, catch-all)
```

---

## Complete GitOps Flow (End-to-End)

```
Developer pushes to main
        │
        ▼
  ┌─── CI Pipeline ───────────────────────────────────────┐
  │  1. Checkout code                                      │
  │  2. Run 15-job matrix in parallel (~3-5 min)           │
  │     • Go tests + lint (api-gateway, ingestion)         │
  │     • Python tests + lint (5 services)                 │
  │     • Frontend tests (React/Jest)                      │
  │  3. All 15 green? → trigger CD                         │
  └───────────────────────────┬───────────────────────────┘
                              │
        ▼
  ┌─── CD Pipeline ───────────────────────────────────────┐
  │  1. Gate: verify CI succeeded                          │
  │  2. Detect which services/ changed (path filter)       │
  │  3. OIDC → STS temporary AWS credentials               │
  │  4. ECR login                                          │
  │  5. Build + push changed images (sha-<commit> tag)     │
  │  6. kustomize edit set image (update tags)             │
  │  7. git commit + push "[skip ci]"                      │
  └───────────────────────────┬───────────────────────────┘
                              │
        ▼
  ┌─── ArgoCD ────────────────────────────────────────────┐
  │  1. Detects kustomization.yaml change in git           │
  │  2. Renders manifests (kustomize build)                │
  │  3. Diff against live cluster                          │
  │  4. Apply changes (rolling update)                     │
  │  5. Prune removed resources                            │
  │  6. selfHeal ensures drift = 0                         │
  └───────────────────────────┬───────────────────────────┘
                              │
        ▼
  ┌─── EKS Cluster ──────────────────────────────────────┐
  │  Rolling deployment completes                          │
  │  ALB health check passes                               │
  │  New version live                                      │
  └───────────────────────────────────────────────────────┘
```

**Total time**: Push → production: **~8-12 minutes** (3-5 CI + 3-5 CD + 1-2 ArgoCD sync)

---

---

## Kyverno Policy Enforcement

### Overview

Kyverno is deployed as a Kubernetes admission controller that enforces policies on all resources in the `workflowai` namespace. Policies run in **Enforce** mode — non-compliant resources are **rejected** at admission time, not just audited.

### Installation

Kyverno is installed via Helm during cluster bootstrap (Step 5 in `infra/scripts/bootstrap-cluster.sh`):

```bash
helm install kyverno kyverno/kyverno \
  -n kyverno \
  --create-namespace \
  --set admissionController.replicas=1 \
  --set backgroundController.replicas=1
```

### Policy Catalog (6 policies)

| Policy | Severity | What It Enforces |
|--------|----------|-----------------|
| `disallow-latest-tag` | Medium | All container images must have an explicit tag; `:latest` is rejected |
| `require-resource-limits` | Medium | CPU and memory limits required on every container |
| `require-labels` | Medium | `app` and `app.kubernetes.io/part-of` labels required on all pods |
| `require-probes` | Medium | `readinessProbe` and `livenessProbe` required on all containers |
| `restrict-image-registries` | High | Only ECR (`589528730663.dkr.ecr.ap-southeast-1.amazonaws.com`) and Docker Hub (for infra images) allowed |
| `disallow-privilege-escalation` | High | Blocks `privileged: true` and `allowPrivilegeEscalation: true` |

### Policy Management (GitOps)

Policies live in `k8s/policies/` and are managed by a dedicated ArgoCD Application (`k8s/argocd/apps/policies.yaml`). The GitOps flow for policy changes:

```
Edit policy YAML in k8s/policies/
        │
        ▼
  git commit + push
        │
        ▼
  ArgoCD detects change in k8s/policies/
        │
        ▼
  ArgoCD syncs ClusterPolicy resources
        │
        ▼
  Kyverno webhook picks up new/updated policies
        │
        ▼
  All subsequent pod admissions evaluated against updated policies
```

### Why Enforce Mode (not Audit)?

- **Shift-left**: Non-compliant manifests are caught before they reach the cluster, not after
- **Existing compliance**: All 13 running pods already comply with all 6 policies (verified before enabling Enforce)
- **CI/CD safety net**: Even if a developer bypasses code review, Kyverno blocks non-compliant deployments at admission time
- **No false positives**: Policies are scoped to `workflowai` namespace only — kube-system, argocd, monitoring, kyverno namespaces are unaffected

---

## Operational Runbook

### Check CI Status

```bash
# Latest runs
gh run list --limit 5

# Watch a specific run
gh run watch <run-id> --exit-status

# View failed job logs
gh run view <run-id> --log-failed
```

### Check Deployment Status

```bash
# Pod status
kubectl get pods -n workflowai

# Deployment rollout status
kubectl rollout status deployment/api-gateway -n workflowai

# ArgoCD app status
kubectl get applications -n argocd

# Current image tags
kubectl get deployment -n workflowai -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.template.spec.containers[0].image}{"\n"}{end}'
```

### Rollback

```bash
# Option 1: Revert kustomize tag to previous SHA
cd k8s/overlays/production
kustomize edit set image "<ECR>/workflowai/<service>=<ECR>/workflowai/<service>:sha-<prev>"
git commit -m "rollback: <service> to sha-<prev>"
git push  # ArgoCD auto-syncs

# Option 2: ArgoCD manual sync to previous revision
argocd app rollback workflowai <revision>
```

### Force Re-deploy (same image)

```bash
# Restart all pods without changing image
kubectl rollout restart deployment/<service> -n workflowai
# Note: selfHeal may revert this if the manifest hasn't changed
```

### Troubleshooting

| Symptom | Diagnosis | Fix |
|---------|-----------|-----|
| CI fails on Python | Check pip install logs — PyTorch index? | Verify `--extra-index-url` for CPU wheels |
| CD skipped | CI didn't succeed, or no changes on `main` | Check `workflow_run` trigger condition |
| Images not pushed | OIDC role trust policy mismatch | Verify GitHub OIDC provider in IAM |
| ArgoCD out of sync | Manual `kubectl` change reverted by selfHeal | Commit change to git instead |
| Pod CrashLoopBackOff | Missing secret or config | `kubectl logs <pod> -n workflowai` |
| ALB 404 | Ingress path not matching | Check `k8s/overlays/production/ingress.yaml` |
| `[skip ci]` not working | Commit message format wrong | Ensure exact `[skip ci]` in message |

---

## Key Design Decisions

### Why GitHub Actions (not Jenkins/GitLab)?

- **Native GitHub integration**: OIDC federation, `workflow_run` chaining, path-filter actions
- **Zero infrastructure**: No Jenkins server to maintain
- **Matrix strategy**: Parallel jobs scale automatically
- **Cost**: Free for public repos (this is a portfolio project)

### Why ArgoCD (not Flux/Spinnaker)?

- **UI**: Built-in web dashboard for sync status visualization
- **App-of-apps**: Hierarchical application management
- **selfHeal**: Automatic drift detection and correction
- **Kustomize native**: No plugins needed for our manifest strategy

### Why `sha-<commit>` Tags (not semver)?

- **Traceability**: Every running image maps to exactly one git commit
- **No ambiguity**: `:latest` or `:v1.2.3` can be overwritten; `sha-abc123` cannot
- **Rollback**: Point to any previous SHA — no version ordering needed
- **CI/CD simplicity**: Tag = commit SHA, no version bump logic

### Why `[skip ci]` on Tag Updates?

The CD pipeline commits updated kustomize tags back to `main`. Without `[skip ci]`, this would trigger another CI run → another CD run → infinite loop. The `[skip ci]` marker breaks the cycle.

### Why `cancel-in-progress: false` for CD?

A deploy in progress must complete — half-pushed images or partial kustomize updates leave the system in an inconsistent state. CI can be cancelled freely (newer code supersedes), but CD cannot.

---

## File Reference

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | CI pipeline definition (15 jobs) |
| `.github/workflows/cd.yml` | CD pipeline definition (4 stages) |
| `k8s/argocd/root-app.yaml` | ArgoCD root Application (app-of-apps) |
| `k8s/argocd/apps/workflowai.yaml` | ArgoCD child Application (workloads) |
| `k8s/argocd/apps/policies.yaml` | ArgoCD child Application (Kyverno policies) |
| `k8s/argocd/projects/workflowai-project.yaml` | ArgoCD AppProject (RBAC boundaries) |
| `k8s/policies/` | Kyverno ClusterPolicy resources (6 policies, Enforce mode) |
| `k8s/overlays/production/kustomization.yaml` | Production image tags (updated by CD) |
| `k8s/overlays/production/ingress.yaml` | ALB Ingress (path-based routing) |
| `k8s/base/kustomization.yaml` | Base resource list |
| `infra/scripts/bootstrap-cluster.sh` | Cluster bootstrap (8 steps incl. Kyverno) |
| `Makefile` | Local ops: terraform, bootstrap, deploy, status, clean |

---

**Last Updated**: 2026-03-16
