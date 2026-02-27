#!/bin/bash
#
# Docker Compose Services Testing Script
# Tests all Python microservices in the WorkflowAI platform
#
# Usage: ./test-services.sh
#

set -e

echo "=================================================="
echo "WorkflowAI Services Testing Script"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${YELLOW}→ $1${NC}"
}

# Function to check if service is responding
check_service() {
    local service_name=$1
    local url=$2
    local max_retries=30
    local retry=0
    
    print_info "Checking $service_name at $url..."
    
    while [ $retry -lt $max_retries ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            print_success "$service_name is healthy"
            return 0
        fi
        retry=$((retry + 1))
        echo -n "."
        sleep 2
    done
    
    print_error "$service_name failed to start after ${max_retries} retries"
    return 1
}

# Function to test API endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local method=${3:-GET}
    local data=${4:-}
    
    print_info "Testing $name..."
    
    if [ "$method" = "POST" ] && [ -n "$data" ]; then
        response=$(curl -s -X POST "$url" \
            -H "Content-Type: application/json" \
            -d "$data" 2>&1)
    else
        response=$(curl -s "$url" 2>&1)
    fi
    
    if [ $? -eq 0 ] && [ -n "$response" ]; then
        print_success "$name works"
        echo "  Response: ${response:0:100}..."
        return 0
    else
        print_error "$name failed"
        echo "  Error: $response"
        return 1
    fi
}

echo "Step 1: Starting infrastructure services"
echo "=========================================="
print_info "Starting PostgreSQL, Redis, Elasticsearch..."
docker compose up -d postgres redis elasticsearch

echo ""
echo "Waiting for infrastructure to be ready (30s)..."
sleep 30

echo ""
echo "Step 2: Building Python services"
echo "================================="
print_info "Building agent-orchestrator..."
docker compose build agent-orchestrator

print_info "Building indexing..."
docker compose build indexing

print_info "Building model-service..."
docker compose build model-service

echo ""
echo "Step 3: Starting Python services"
echo "================================="
print_info "Starting all Python services..."
docker compose up -d agent-orchestrator indexing model-service

echo ""
echo "Waiting for services to start (60s)..."
sleep 60

echo ""
echo "Step 4: Health Check Tests"
echo "=========================="

# Test infrastructure
check_service "PostgreSQL" "localhost:5432" || true
check_service "Redis" "http://localhost:6379" || true
check_service "Elasticsearch" "http://localhost:9200" || true

# Test Python services
check_service "Agent Orchestrator" "http://localhost:8002/health"
check_service "Indexing Service" "http://localhost:8003/health"
check_service "Model Service" "http://localhost:8004/health"

echo ""
echo "Step 5: API Endpoint Tests"
echo "=========================="

# Test Agent Orchestrator
test_endpoint "Agent Orchestrator - Root" "http://localhost:8002/"
test_endpoint "Agent Orchestrator - Ready" "http://localhost:8002/ready"
test_endpoint "Agent Orchestrator - Workflow Types" "http://localhost:8002/workflows/types"

# Test Indexing Service
test_endpoint "Indexing Service - Root" "http://localhost:8003/"
test_endpoint "Indexing Service - Ready" "http://localhost:8003/ready"
test_endpoint "Indexing Service - Stats" "http://localhost:8003/stats"

# Test Model Service
test_endpoint "Model Service - Root" "http://localhost:8004/"
test_endpoint "Model Service - Ready" "http://localhost:8004/ready"
test_endpoint "Model Service - Model Info" "http://localhost:8004/model/info"

echo ""
echo "Step 6: Functional Tests"
echo "========================"

# Test Indexing - Index a document
print_info "Testing document indexing..."
INDEX_RESPONSE=$(curl -s -X POST "http://localhost:8003/index" \
    -H "Content-Type: application/json" \
    -d '{"title":"Test Document","content":"This is a test document for verification"}' 2>&1)

if echo "$INDEX_RESPONSE" | grep -q "indexed"; then
    print_success "Document indexing works"
    echo "  Response: ${INDEX_RESPONSE:0:100}..."
else
    print_error "Document indexing failed"
    echo "  Response: $INDEX_RESPONSE"
fi

# Test Indexing - Search
print_info "Testing document search..."
SEARCH_RESPONSE=$(curl -s -X POST "http://localhost:8003/search" \
    -H "Content-Type: application/json" \
    -d '{"query":"test document","top_k":5}' 2>&1)

if echo "$SEARCH_RESPONSE" | grep -q "results"; then
    print_success "Document search works"
    echo "  Response: ${SEARCH_RESPONSE:0:100}..."
else
    print_error "Document search failed"
    echo "  Response: $SEARCH_RESPONSE"
fi

# Test Model Service - Text generation (only if model is small enough)
print_info "Testing text generation (may take time if model loads)..."
GEN_RESPONSE=$(curl -s -X POST "http://localhost:8004/generate" \
    -H "Content-Type: application/json" \
    -d '{"prompt":"Hello, how are","max_tokens":10}' \
    --max-time 60 2>&1)

if echo "$GEN_RESPONSE" | grep -q "text"; then
    print_success "Text generation works"
    echo "  Response: ${GEN_RESPONSE:0:100}..."
else
    print_error "Text generation failed (this is expected if model is too large)"
    echo "  Response: $GEN_RESPONSE"
fi

# Test Agent Orchestrator - Log analysis (requires OpenAI API key)
if [ -n "$OPENAI_API_KEY" ]; then
    print_info "Testing log analysis workflow..."
    ANALYSIS_RESPONSE=$(curl -s -X POST "http://localhost:8002/workflows/analyze-log" \
        -H "Content-Type: application/json" \
        -d '{"log_content":"ERROR: NullPointerException at line 42","log_type":"build"}' \
        --max-time 30 2>&1)
    
    if echo "$ANALYSIS_RESPONSE" | grep -q "analysis_id"; then
        print_success "Log analysis works"
        echo "  Response: ${ANALYSIS_RESPONSE:0:100}..."
    else
        print_error "Log analysis failed"
        echo "  Response: $ANALYSIS_RESPONSE"
    fi
else
    print_info "Skipping log analysis test (OPENAI_API_KEY not set)"
fi

echo ""
echo "Step 7: Service Logs Check"
echo "=========================="
print_info "Checking for errors in service logs..."

for service in agent-orchestrator indexing model-service; do
    echo ""
    echo "--- $service logs (last 20 lines) ---"
    docker compose logs --tail=20 $service
done

echo ""
echo "=================================================="
echo "Testing Complete!"
echo "=================================================="
echo ""
print_info "Services Status:"
docker compose ps

echo ""
print_success "All tests completed. Review output above for any failures."
echo ""
echo "To view live logs:"
echo "  docker compose logs -f agent-orchestrator"
echo "  docker compose logs -f indexing"
echo "  docker compose logs -f model-service"
echo ""
echo "To stop services:"
echo "  docker compose down"
echo ""
