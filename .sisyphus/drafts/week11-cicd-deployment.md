# Draft: Week 11 — CI/CD Pipeline + Cloud Deployment

## Requirements (confirmed)
- **Primary Goal**: Both CI/CD showcase AND live demo deployment
- **Cloud Budget**: Cost doesn't matter — optimize for impression
- **AWS Setup**: IAM roles preserved from Week 2 Day 10 EC2 deployment
- **Scope**: Full pipeline: CI tests → build Docker images → deploy to cloud → live URL
- **Deploy for real**: Actually `terraform apply` — live EKS cluster with running services

## Technical Decisions (ALL CONFIRMED)
- **Cloud Architecture**: EKS (Elastic Kubernetes Service) — maximum K8s showcase
- **GitOps**: ArgoCD for continuous deployment from Git
- **CI Pipeline**: Full matrix CI — Go, Python, Frontend tests in parallel jobs
- **CD Strategy**: Auto-deploy on push to main (CI → build images → ArgoCD sync)
- **Docker Registry**: ECR (AWS-native, integrates with EKS IAM)
- **Terraform**: Full AWS IaC (VPC, EKS, ECR, ALB)
- **New Tests**: None — wire existing 470 tests into CI
- **K8s Features**: HPA, Ingress Controller (ALB), Secrets Management, Namespaces, Monitoring

## Research Findings

### What ALREADY EXISTS:
- **No GitHub Actions** — `.github/workflows/` doesn't exist yet
- **No Terraform** — `infra/terraform/.gitkeep` only (empty placeholder)
- **No deploy scripts** — No deploy.sh or similar
- **No Makefile** — No unified build/test runner
- **7 Dockerfiles** — All services + frontend have Dockerfiles (multi-stage, gunicorn, nginx)
- **Full docker-compose.yml** — 13 services: postgres, redis, elasticsearch, api-gateway, ingestion, agent-orchestrator, indexing, model-service, metrics, prometheus, grafana, jaeger, frontend
- **Infra configs exist** — postgres/init.sql, prometheus/prometheus.yml, grafana/datasources.yml
- **.env.example** for 5 services — api-gateway, agent-orchestrator, model-service, indexing, ingestion
- **Health checks** — postgres, redis, elasticsearch have health checks in compose
- **Resource limits** — Added in Week 10 (CPU + memory limits per service)
- **IAM roles preserved** — From Week 2 Day 10 AWS EC2 deployment

### What NEEDS to be built:
- GitHub Actions CI workflow (matrix: Go tests, Python tests ×4, Frontend Jest, linting)
- ECR repositories for 7 service images
- Terraform: VPC, EKS cluster, ECR, ALB, security groups
- Kubernetes manifests (Helm charts) for all services
- ArgoCD installation + app-of-apps config
- HPA for auto-scaling
- nginx-ingress or ALB Ingress Controller
- Kubernetes Secrets / ConfigMaps
- Namespace strategy (dev/staging/prod)
- Prometheus + Grafana on K8s
- CD workflow: build → push ECR → ArgoCD sync

## Scope Boundaries
- **INCLUDE**: GitHub Actions CI, ECR image builds, EKS + Terraform, Helm charts, ArgoCD, HPA, Ingress, Secrets, Namespaces, Monitoring, ACTUAL DEPLOYMENT
- **EXCLUDE**: Custom domain, SSL/TLS (ACM + Route53), RDS (use in-cluster PG), ElastiCache (use in-cluster Redis)
