.PHONY: terraform-init terraform-plan terraform-apply terraform-destroy bootstrap deploy status test-ci docker-build clean help

# ─────────────────────────────────────────────────────────────────────────────
# Variables
# ─────────────────────────────────────────────────────────────────────────────
TERRAFORM_DIR    := infra/terraform
BOOTSTRAP_SCRIPT := infra/scripts/bootstrap-cluster.sh
NAMESPACE        := workflowai
CLUSTER_NAME     ?= workflowai
AWS_REGION       ?= ap-southeast-1

# ─────────────────────────────────────────────────────────────────────────────
# Terraform targets
# ─────────────────────────────────────────────────────────────────────────────

## terraform-init: Initialize Terraform (download providers, set up backend)
terraform-init:
	cd $(TERRAFORM_DIR) && terraform init

## terraform-plan: Show Terraform execution plan
terraform-plan:
	cd $(TERRAFORM_DIR) && terraform plan

## terraform-apply: Apply Terraform configuration (creates VPC, EKS, ECR, IAM)
terraform-apply:
	cd $(TERRAFORM_DIR) && terraform apply -auto-approve

## terraform-destroy: Destroy all Terraform-managed infrastructure
terraform-destroy:
	cd $(TERRAFORM_DIR) && terraform destroy -auto-approve

# ─────────────────────────────────────────────────────────────────────────────
# Cluster lifecycle
# ─────────────────────────────────────────────────────────────────────────────

## bootstrap: Install cluster tooling (ALB Controller, ArgoCD, Prometheus) and deploy root app
bootstrap:
	bash $(BOOTSTRAP_SCRIPT)

## deploy: Apply ArgoCD root application (triggers ArgoCD sync of entire stack)
deploy:
	kubectl apply -f k8s/argocd/root-app.yaml

## status: Show pod and ingress status for workflowai namespace
status:
	kubectl get pods -n $(NAMESPACE)
	kubectl get ingress -n $(NAMESPACE)

# ─────────────────────────────────────────────────────────────────────────────
# Development & testing
# ─────────────────────────────────────────────────────────────────────────────

## test-ci: Run all tests locally (Go + Python + Frontend)
test-ci:
	@echo "=== Go: api-gateway ==="
	cd services/api-gateway && go test -v -short ./...
	@echo "=== Go: ingestion ==="
	cd services/ingestion && go test -v -short ./...
	@echo "=== Python: agent-orchestrator ==="
	cd services/agent-orchestrator && python -m pytest tests/ -v --tb=short
	@echo "=== Python: indexing ==="
	cd services/indexing && python -m pytest tests/ -v --tb=short
	@echo "=== Python: model-service ==="
	cd services/model-service && python -m pytest tests/ -v --tb=short
	@echo "=== Python: metrics ==="
	cd services/metrics && python -m pytest tests/ -v --tb=short
	@echo "=== Python: finetune ==="
	cd services/finetune && python -m pytest tests/ -v --tb=short
	@echo "=== Frontend ==="
	cd frontend && npx jest

## docker-build: Build all Docker images locally
docker-build:
	docker build -t workflowai/api-gateway:local services/api-gateway
	docker build -t workflowai/ingestion:local services/ingestion
	docker build -t workflowai/agent-orchestrator:local services/agent-orchestrator
	docker build -t workflowai/indexing:local services/indexing
	docker build -t workflowai/model-service:local services/model-service
	docker build -t workflowai/metrics:local services/metrics
	docker build -t workflowai/finetune:local services/finetune
	docker build -t workflowai/frontend:local frontend

# ─────────────────────────────────────────────────────────────────────────────
# Cleanup
# ─────────────────────────────────────────────────────────────────────────────

## clean: Destroy infrastructure and delete workflowai namespace
clean:
	-kubectl delete namespace $(NAMESPACE) --ignore-not-found
	cd $(TERRAFORM_DIR) && terraform destroy -auto-approve

## help: Show this help message
help:
	@grep -E '^## ' $(MAKEFILE_LIST) | sed 's/## //' | column -t -s ':'
