# Decisions — Week 11 CI/CD + EKS Deployment

## [2026-03-15] Session Started: ses_31077bfdbffeX00Hgz5ysRHTV1

### User-Approved Architecture
- EKS + ArgoCD GitOps (max K8s sophistication)
- Full matrix CI (parallel Go/Python/Frontend test jobs)
- Auto-deploy on push to main
- Full AWS IaC (Terraform)
- ECR for Docker registry
- Deploy for real (terraform apply — live EKS cluster)
- ap-southeast-1 (Singapore)
- Add finetune to K8s (create Dockerfile + manifests)
- No new tests (wire existing tests into CI only)
- No Momus review — approved plan directly

### Architecture Guardrails (User Confirmed)
- No RDS/ElastiCache (in-cluster PG/Redis)
- No Route53/ACM (ALB URL only)
- No multi-NAT (single NAT, cost optimization)
- No service mesh
- No network policies
- No Atlantis (manual terraform apply only)
- No multi-env namespaces (single workflowai)
- No :latest image tags
- No hardcoded secrets in K8s manifests
