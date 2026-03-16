# Interview Preparation

> Technical deep-dive Q&A for NVIDIA Senior Software Engineer — AI Workflow (IPP)

---

## How to Use This Guide

This document covers 13 questions across 5 NVIDIA IPP interview categories. Each answer includes the concise response, technical depth, and follow-up anticipation.

For the full interactive version with expandable answers, see the [Portfolio Website](../portfolio/interview.html).

---

## Category 1: System Architecture

### Q1: Why did you choose a polyglot Go + Python architecture?

**Answer**: I separated concerns by technical requirement. The network layer (API Gateway, Ingestion) needs high-throughput I/O — Go delivers 40k RPS with 30MB memory. The AI layer needs LangChain, vLLM, and Transformers — Python is the only viable choice. Standard microservices patterns (HTTP + Redis Streams + OpenTelemetry) make the language boundary transparent.

**Key Numbers**: 5× throughput improvement (40k vs 8k RPS), 6× memory efficiency, ~40 hours of polyglot overhead across 12 weeks.

**Follow-up**: "What if you could only use one language?" — Python with uvicorn would cap at ~8k RPS. Acceptable for many workloads, but for an interview showcasing scale, the Go layer demonstrates real systems thinking.

### Q2: How do services communicate?

**Answer**: Synchronous HTTP for request-response (Gateway → Agent Orchestrator → Model Service). Redis Streams for event-driven async (Ingestion → downstream consumers with consumer groups). OpenTelemetry for distributed tracing across both patterns.

**Why not gRPC?** HTTP is simpler to debug, and our inter-service latency (~15ms network hop) is dominated by LLM inference (~1.2s). gRPC's binary protocol would save microseconds on a seconds-long pipeline — not worth the complexity.

### Q3: How would you scale this to 10× traffic?

**Answer**: 
1. **Gateway**: Already at 40k RPS on a single instance. HPA scales horizontally to 100k+ trivially.
2. **AI Layer**: CPU-bound. Add GPU nodes for vLLM (PagedAttention enables batch inference). HPA on CPU utilization.
3. **Data Layer**: PostgreSQL read replicas for DORA queries. Redis Cluster for distributed caching. Elasticsearch multi-node for search throughput.
4. **Infrastructure**: Upgrade from 2× t3.large to 4× m5.xlarge + 2× g4dn.xlarge (GPU).

---

## Category 2: AI/ML Implementation

### Q4: How does your RAG pipeline work?

**Answer**: 
1. **Indexing** — CI logs → chunked → Sentence Transformers (dense vectors) + Elasticsearch (BM25 terms)
2. **Retrieval** — Query embeds → parallel BM25 + kNN search → Reciprocal Rank Fusion (RRF) merge
3. **Generation** — Top-k context + query → LLM prompt → structured JSON output (root cause, fix steps, confidence)

**Why hybrid search?** BM25 catches exact error strings ("ModuleNotFoundError"). Dense vectors catch semantic matches ("missing dependency" ≈ "package not installed"). RRF combines both without manual weight tuning.

### Q5: How did you implement fine-tuning?

**Answer**: LoRA (Low-Rank Adaptation) on Qwen2.5-7B using PEFT library. 4-bit quantization (QLoRA) enables training on a single consumer GPU. The fine-tuned adapter classifies CI failure types (build, test, deploy, dependency) and is loaded at inference time via PEFT's adapter merging.

**Key Decision**: Fine-tuning a classifier rather than the generation model. Classification accuracy directly improves triage routing; generation quality is better handled by prompt engineering + RAG context.

### Q6: How does the LangGraph incident response work?

**Answer**: Four-node state machine: Triage → Diagnosis → Remediation → Report. Each node is a separate agent with its own prompt and tool access. LangGraph manages state transitions and conditional edges (e.g., critical severity skips diagnosis and goes straight to remediation).

**Why LangGraph over vanilla LangChain?** Explicit state machine > implicit chain-of-thought. LangGraph gives us controllable, debuggable, and testable multi-agent workflows with cycle support (retry diagnosis if remediation fails).

---

## Category 3: Performance & Optimization

### Q7: How did you achieve 40k RPS on the API Gateway?

**Answer**: 
1. **Connection Pooling** — `http.Transport` with `MaxIdleConns: 100` (eliminates TCP handshake per request)
2. **Client Reuse** — Singleton `http.Client` per downstream service
3. **Server Tuning** — `ReadTimeout: 15s`, `WriteTimeout: 30s`, `IdleTimeout: 120s`
4. **Response Caching** — Redis 30s TTL for read-heavy endpoints (~95% hit rate on DORA metrics)
5. **Goroutines** — Go's M:N scheduler handles 400+ concurrent connections without thread-per-request overhead

Before optimization: ~8k RPS. After: ~40k RPS (5× improvement).

### Q8: How do you profile and find bottlenecks?

**Answer**: Layer-by-layer profiling:
- **Gateway**: Go's `pprof` for CPU/memory profiling, `wrk` for load testing
- **Python services**: `cProfile` + `py-spy` for hot paths, `locust` for concurrent load
- **End-to-end**: OpenTelemetry traces in Jaeger show per-service latency waterfall
- **Infrastructure**: Prometheus metrics for CPU/memory/network per pod, Grafana dashboards for visualization

**Example**: Identified that 70% of end-to-end latency was in LLM inference. Solution: batch inference via vLLM's PagedAttention + response caching for repeated queries.

---

## Category 4: DevOps & Infrastructure

### Q9: Walk me through your CI/CD pipeline.

**Answer**:
1. **CI** (GitHub Actions): Push to any branch → matrix build (Go ×2, Python ×4, Frontend) → lint + test + type-check → 15/15 jobs must pass
2. **CD** (on main merge): Build Docker images → push to ECR with `sha-<commit>` tag → update `k8s/overlays/production/kustomization.yaml` → commit back to main
3. **GitOps** (ArgoCD): Detects kustomization.yaml change → auto-sync cluster → selfHeal ensures git is single source of truth

**Key Design**: No `:latest` tags. Every deployment is traceable to a specific commit SHA. Rollback = revert the kustomization.yaml commit.

### Q10: How do you manage infrastructure as code?

**Answer**: Terraform for AWS resources (VPC, EKS, ECR ×8, IAM OIDC, IRSA). State in S3 with DynamoDB locking. Kustomize for K8s manifests (base + dev/production overlays). Helm only for third-party tools (ALB Controller, ArgoCD, Prometheus stack).

**Why Kustomize over Helm for apps?** Our manifests are simple enough that Kustomize overlays are clearer than Helm templates. ArgoCD has native Kustomize support. PRs review plain YAML diffs, not template logic.

### Q11: How do you handle secrets?

**Answer**: 
- **Runtime**: Kubernetes Secrets (no hardcoded values in manifests)
- **CI/CD**: GitHub OIDC federation → AWS STS temporary credentials (no long-lived keys)
- **Pod-level**: IRSA (IAM Roles for Service Accounts) via OIDC provider

**What I'd add for production**: AWS Secrets Manager + External Secrets Operator for automatic rotation. KMS encryption for Kubernetes etcd secrets at rest.

---

## Category 5: DORA Metrics & Business Impact

### Q12: How do you quantify AI impact on engineering?

**Answer**: DORA metrics — the four key metrics from the Accelerate research:
1. **Deployment Frequency**: 3.5 deploys/week (High performer)
2. **Lead Time for Changes**: 2.4 hours (Elite)
3. **Change Failure Rate**: 8% (Elite)
4. **MTTR**: 30 minutes (Elite)

**AI-specific impact**: Automated failure triage reduces MTTR from 45 min (manual) to 8 min (AI-assisted) — 5.6× improvement. PR risk assessment catches 72% of high-risk changes before merge.

### Q13: What would you build next?

**Answer** (prioritized):
1. **GPU inference layer** — Move from OpenRouter to on-cluster vLLM for lower latency and cost control
2. **Fine-tuned retrieval** — Train a domain-specific embedding model on internal CI logs for better RAG recall
3. **Feedback loop** — Collect user accept/reject on AI suggestions to continuously improve classifier and prompts
4. **Multi-tenant support** — Namespace isolation per team with RBAC on workflows
5. **Cost optimization** — Spot instances for non-critical services, Karpenter for autoscaling

---

## Demo Script (5-Minute Walkthrough)

```bash
# 1. Show the running cluster
kubectl get pods -n workflowai

# 2. Build Failure Triage
curl -X POST http://ALB_URL/api/v1/workflows/analyze-log \
  -H "Content-Type: application/json" \
  -d '{"log_content": "ERROR: ModuleNotFoundError: No module named torch", "workflow_type": "build_failure_triage"}'

# 3. PR Risk Assessment
curl -X POST http://ALB_URL/api/v1/workflows/execute \
  -H "Content-Type: application/json" \
  -d '{"workflow_type": "pr_risk_assessment", "input": {"pr_diff": "diff --git a/auth.py ...", "pr_metadata": {"files_changed": 12}}}'

# 4. DORA Metrics Dashboard
curl http://ALB_URL/api/metrics/dora

# 5. Show CI pipeline (15/15 green)
# Open: https://github.com/SilkLee/workflow-ai/actions
```

---

## Resources

- **[Portfolio Website](../portfolio/index.html)** — Interactive project showcase
- **[Architecture Doc](../architecture.md)** — System design deep-dive
- **[Performance Report](../performance-report.md)** — Full benchmarks
- **[API Reference](../api.md)** — Endpoint documentation
- **[Tech Stack](../tech-stack.md)** — Technology selection rationale
