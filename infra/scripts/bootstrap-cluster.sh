#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# WorkflowAI Cluster Bootstrap Script
# Installs cluster-level tooling and deploys the ArgoCD root application.
# Prerequisites: aws, kubectl, helm, terraform must be installed.
# ─────────────────────────────────────────────────────────────────────────────

CLUSTER_NAME="${CLUSTER_NAME:-workflowai}"
AWS_REGION="${AWS_REGION:-ap-southeast-1}"
NAMESPACE="${NAMESPACE:-workflowai}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() { echo -e "${GREEN}[bootstrap]${NC} $*"; }
warn() { echo -e "${YELLOW}[bootstrap][WARN]${NC} $*"; }
die() { echo -e "${RED}[bootstrap][ERROR]${NC} $*" >&2; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
# Step 0: Prerequisites check
# ─────────────────────────────────────────────────────────────────────────────
log "Checking prerequisites..."

for tool in aws kubectl helm terraform; do
  if ! command -v "$tool" &>/dev/null; then
    die "'$tool' is not installed. Please install it and re-run."
  fi
  version=$("$tool" version 2>&1 | head -1)
  log "  $tool: $version"
done

# Verify AWS credentials are configured
if ! aws sts get-caller-identity &>/dev/null; then
  die "AWS credentials not configured. Run 'aws configure' or set environment variables."
fi
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
log "AWS Account: $AWS_ACCOUNT_ID"
log "AWS Region:  $AWS_REGION"

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Update kubeconfig from EKS cluster
# ─────────────────────────────────────────────────────────────────────────────
log ""
log "Step 1: Updating kubeconfig for EKS cluster '$CLUSTER_NAME'..."
aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$AWS_REGION"
kubectl cluster-info
log "kubeconfig updated."

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Install AWS Load Balancer Controller
# ─────────────────────────────────────────────────────────────────────────────
log ""
log "Step 2: Installing AWS Load Balancer Controller..."

# Get ALB controller role ARN from Terraform outputs
ALB_CONTROLLER_ROLE_ARN="${ALB_CONTROLLER_ROLE_ARN:-}"
if [[ -z "$ALB_CONTROLLER_ROLE_ARN" ]]; then
  log "  Fetching ALB controller role ARN from Terraform outputs..."
  ALB_CONTROLLER_ROLE_ARN=$(terraform -chdir=infra/terraform output -raw alb_controller_role_arn 2>/dev/null || echo "")
fi
if [[ -z "$ALB_CONTROLLER_ROLE_ARN" ]]; then
  die "ALB_CONTROLLER_ROLE_ARN is not set and could not be read from Terraform outputs."
fi
log "  ALB Controller Role ARN: $ALB_CONTROLLER_ROLE_ARN"

helm repo add eks https://aws.github.io/eks-charts 2>/dev/null || true
helm repo update eks

if helm status aws-load-balancer-controller -n kube-system &>/dev/null; then
  warn "  aws-load-balancer-controller already installed — upgrading..."
  helm upgrade aws-load-balancer-controller eks/aws-load-balancer-controller \
    -n kube-system \
    --set clusterName="$CLUSTER_NAME" \
    --set serviceAccount.create=true \
    --set "serviceAccount.annotations.eks\.amazonaws\.com/role-arn=${ALB_CONTROLLER_ROLE_ARN}"
else
  helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
    -n kube-system \
    --set clusterName="$CLUSTER_NAME" \
    --set serviceAccount.create=true \
    --set "serviceAccount.annotations.eks\.amazonaws\.com/role-arn=${ALB_CONTROLLER_ROLE_ARN}"
fi
log "  AWS Load Balancer Controller installed."

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Install ArgoCD
# ─────────────────────────────────────────────────────────────────────────────
log ""
log "Step 3: Installing ArgoCD..."

helm repo add argo https://argoproj.github.io/argo-helm 2>/dev/null || true
helm repo update argo

if helm status argocd -n argocd &>/dev/null; then
  warn "  ArgoCD already installed — upgrading..."
  helm upgrade argocd argo/argo-cd \
    -n argocd \
    --create-namespace \
    --set server.service.type=ClusterIP
else
  helm install argocd argo/argo-cd \
    -n argocd \
    --create-namespace \
    --set server.service.type=ClusterIP
fi
log "  ArgoCD installed."

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Install kube-prometheus-stack (monitoring)
# ─────────────────────────────────────────────────────────────────────────────
log ""
log "Step 4: Installing kube-prometheus-stack..."

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts 2>/dev/null || true
helm repo update prometheus-community

if helm status prometheus -n monitoring &>/dev/null; then
  warn "  kube-prometheus-stack already installed — skipping."
else
  helm install prometheus prometheus-community/kube-prometheus-stack \
    -n monitoring \
    --create-namespace
fi
log "  kube-prometheus-stack installed."

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Install Kyverno (policy engine)
# ─────────────────────────────────────────────────────────────────────────────
log ""
log "Step 5: Installing Kyverno policy engine..."

helm repo add kyverno https://kyverno.github.io/kyverno/ 2>/dev/null || true
helm repo update kyverno

if helm status kyverno -n kyverno &>/dev/null; then
  warn "  Kyverno already installed — upgrading..."
  helm upgrade kyverno kyverno/kyverno \
    -n kyverno \
    --create-namespace \
    --set admissionController.replicas=1 \
    --set backgroundController.replicas=1
else
  helm install kyverno kyverno/kyverno \
    -n kyverno \
    --create-namespace \
    --set admissionController.replicas=1 \
    --set backgroundController.replicas=1
fi

# Wait for Kyverno webhook to be ready before applying policies
log "  Waiting for Kyverno webhook to become ready..."
kubectl wait --for=condition=Ready --timeout=120s \
  -n kyverno pod -l app.kubernetes.io/component=admission-controller 2>/dev/null || true
log "  Kyverno installed."

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Apply Kubernetes secrets for workflowai namespace
# ─────────────────────────────────────────────────────────────────────────────
log ""
log "Step 6: Creating workflowai namespace and secrets..."

kubectl apply -f k8s/base/namespace.yaml

# Check for required environment variables
REQUIRED_VARS=(POSTGRES_PASSWORD JWT_SECRET OPENAI_API_KEY)
for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    die "Required environment variable '$var' is not set. Export it before running this script."
  fi
done

kubectl create secret generic workflowai-secrets \
  -n "$NAMESPACE" \
  --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD}" \
  --from-literal=JWT_SECRET="${JWT_SECRET}" \
  --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -
log "  Secrets created/updated."

# ─────────────────────────────────────────────────────────────────────────────
# Step 7: Apply ArgoCD AppProject and root application
# ─────────────────────────────────────────────────────────────────────────────
log ""
log "Step 7: Applying ArgoCD AppProject and root application..."

# Wait for ArgoCD CRDs to be ready
log "  Waiting for ArgoCD CRDs..."
kubectl wait --for=condition=established --timeout=120s \
  crd/applications.argoproj.io \
  crd/appprojects.argoproj.io 2>/dev/null || true

kubectl apply -f k8s/argocd/projects/workflowai-project.yaml
kubectl apply -f k8s/argocd/root-app.yaml
log "  ArgoCD root application applied."

# ─────────────────────────────────────────────────────────────────────────────
# Step 8: Wait for workflowai pods and print ALB URL
# ─────────────────────────────────────────────────────────────────────────────
log ""
log "Step 8: Waiting for workflowai pods to start (up to 5 minutes)..."
kubectl wait --for=condition=Available --timeout=300s \
  deployment/api-gateway deployment/frontend \
  -n "$NAMESPACE" 2>/dev/null || warn "  Some deployments not yet ready — ArgoCD may still be syncing."

log ""
log "Pod status:"
kubectl get pods -n "$NAMESPACE"

log ""
ALB_URL=$(kubectl get ingress -n "$NAMESPACE" \
  -o jsonpath='{.items[0].status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "")

if [[ -n "$ALB_URL" ]]; then
  log "✅ Bootstrap complete!"
  log "   Application URL: http://${ALB_URL}"
else
  warn "ALB hostname not yet assigned. Run 'kubectl get ingress -n $NAMESPACE' in a few minutes."
fi
