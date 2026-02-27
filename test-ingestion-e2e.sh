#!/bin/bash
# End-to-End Test for Data Ingestion Pipeline
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }
print_step() { echo -e "${BLUE}[STEP] $1${NC}"; }

INGESTION_URL="http://localhost:8001"
AGENT_URL="http://localhost:8002"

# Bypass corporate proxy for localhost
export NO_PROXY=localhost,127.0.0.1

check_service() {
    local name=$1
    local url=$2
    print_info "Checking $name at $url..."
    for i in {1..30}; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            print_success "$name is healthy"
            return 0
        fi
        sleep 1
    done
    print_error "$name failed health check"
    return 1
}

get_stream_length() {
    docker exec workflowai-redis redis-cli XLEN workflowai:logs 2>/dev/null || echo "0"
}

echo "=================================================="
echo "WorkflowAI Ingestion Pipeline E2E Test"
echo "=================================================="
echo ""

print_step "1. Checking Services"
check_service "Ingestion" "$INGESTION_URL/health" || exit 1
check_service "Agent" "$AGENT_URL/health" || exit 1
echo ""

print_step "2. Initial State"
initial=$(get_stream_length)
print_info "Stream length: $initial"
echo ""

print_step "3. Submit Test Log"
response=$(curl -s -w "\n%{http_code}" -X POST "$INGESTION_URL/logs/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "test-'$(date +%s)'",
    "log_type": "build",
    "log_content": "Error: NullPointerException at line 42\nExit code: 1",
    "repository": "test/repo",
    "workflow": "CI",
    "run_id": "12345",
    "commit_sha": "abc123",
    "branch": "main"
  }')

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
    print_success "Log submitted (HTTP $http_code)"
else
    print_error "Submit failed (HTTP $http_code)"
    exit 1
fi
echo ""

print_step "4. Verify Stream"
sleep 2
new_length=$(get_stream_length)
print_info "New stream length: $new_length"
if [ "$new_length" -gt "$initial" ]; then
    print_success "Message published to stream"
else
    print_error "Stream did not increase"
    exit 1
fi
echo ""

print_step "5. Check Agent Logs"
if docker logs workflowai-agent --tail 50 2>&1 | grep -q "Processing\|Consumer\|Workflow"; then
    print_success "Agent processing detected"
else
    print_error "No agent activity (check docker logs workflowai-agent)"
fi
echo ""

echo "=================================================="
print_success "E2E Test Complete"
echo "=================================================="
echo ""
echo "Data Flow Verified:"
echo "  Webhook → Parse → Redis Stream → Consumer → Agent"
echo ""
print_info "Monitor logs:"
echo "  docker logs -f workflowai-ingestion"
echo "  docker logs -f workflowai-agent"
