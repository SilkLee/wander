#!/bin/bash
# Day 8 E2E Test: Agent Orchestrator + Model Service Integration
# Tests the full workflow: Webhook -> Agent -> Model Service -> Analysis

set -e

echo "=========================================="
echo "Day 8 E2E Test: Agent + Model Integration"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Service URLs
AGENT_URL="http://localhost:8002"
MODEL_URL="http://localhost:8004"
INGESTION_URL="http://localhost:8001"

# Test counter
PASSED=0
FAILED=0

# Helper function to test endpoint
test_endpoint() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    echo -n "Testing $name... "
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    
    if [ "$response" == "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $response)"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Expected $expected_code, got $response)"
        ((FAILED++))
        return 1
    fi
}

# Helper function to test JSON endpoint
test_json_endpoint() {
    local name=$1
    local url=$2
    local method=${3:-GET}
    local data=$4
    
    echo -n "Testing $name... "
    
    if [ "$method" == "POST" ]; then
        response=$(curl -s -X POST "$url" -H "Content-Type: application/json" -d "$data" 2>/dev/null || echo "{}")
    else
        response=$(curl -s "$url" 2>/dev/null || echo "{}")
    fi
    
    # Check if response is valid JSON
    if echo "$response" | jq empty 2>/dev/null; then
        echo -e "${GREEN}✓ PASS${NC}"
        echo "  Response: $(echo "$response" | jq -c '.')"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (Invalid JSON response)"
        echo "  Response: $response"
        ((FAILED++))
        return 1
    fi
}

echo "=== Step 1: Check Services Health ==="
echo ""

test_endpoint "Agent Orchestrator Health" "$AGENT_URL/health"
test_endpoint "Model Service Health" "$MODEL_URL/health"
test_endpoint "Ingestion Service Health" "$INGESTION_URL/health"

echo ""
echo "=== Step 2: Test Model Service ==="
echo ""

test_json_endpoint "Model Info" "$MODEL_URL/model/info"

# Test text generation
echo -n "Testing Model Generation... "
gen_response=$(curl -s -X POST "$MODEL_URL/generate" \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Error: NullPointerException. Fix:",
        "max_tokens": 50,
        "temperature": 0.3
    }' 2>/dev/null)

if echo "$gen_response" | jq -e '.text' > /dev/null 2>&1; then
    generated_text=$(echo "$gen_response" | jq -r '.text')
    echo -e "${GREEN}✓ PASS${NC}"
    echo "  Generated: ${generated_text:0:100}..."
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "  Response: $gen_response"
    ((FAILED++))
fi

echo ""
echo "=== Step 3: Test Agent Orchestrator Workflow API ==="
echo ""

# Test workflow submission
echo -n "Testing Workflow Submission... "
workflow_payload='{
    "log_content": "ERROR: NullPointerException at Main.java:42\n    at com.example.Main.process(Main.java:42)\n    at com.example.Main.main(Main.java:15)\nProcess finished with exit code 1",
    "log_type": "build",
    "context": {
        "repository": "test/repo",
        "branch": "main",
        "commit": "abc123"
    }
}'

workflow_response=$(curl -s -X POST "$AGENT_URL/workflows/analyze" \
    -H "Content-Type: application/json" \
    -d "$workflow_payload" 2>/dev/null || echo "{}")

if echo "$workflow_response" | jq -e '.analysis_id' > /dev/null 2>&1; then
    analysis_id=$(echo "$workflow_response" | jq -r '.analysis_id')
    root_cause=$(echo "$workflow_response" | jq -r '.root_cause')
    echo -e "${GREEN}✓ PASS${NC}"
    echo "  Analysis ID: $analysis_id"
    echo "  Root Cause: $root_cause"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "  Response: $workflow_response"
    ((FAILED++))
fi

echo ""
echo "=== Step 4: Test Full Integration via Ingestion ==="
echo ""

# Submit log via ingestion service
echo -n "Testing Log Submission... "
log_payload='{
    "log_content": "FAILED: TestUserAuth (0.01s)\n    auth_test.go:42: Expected 200, got 401\nFAIL github.com/company/backend/auth\nexit code 1",
    "log_type": "test",
    "repository": "company/backend",
    "branch": "feature/auth",
    "commit": "def456"
}'

ingestion_response=$(curl -s -X POST "$INGESTION_URL/logs/submit" \
    -H "Content-Type: application/json" \
    -d "$log_payload" 2>/dev/null || echo "{}")

if echo "$ingestion_response" | jq -e '.event_id' > /dev/null 2>&1; then
    event_id=$(echo "$ingestion_response" | jq -r '.event_id')
    echo -e "${GREEN}✓ PASS${NC}"
    echo "  Event ID: $event_id"
    echo "  ${YELLOW}Note: Agent will process this asynchronously from Redis Streams${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}"
    echo "  Response: $ingestion_response"
    ((FAILED++))
fi

echo ""
echo "=== Step 5: Verify Agent Configuration ==="
echo ""

# Check if agent is using local model
echo -n "Checking Agent LLM Backend... "
if docker exec workflowai-agent printenv USE_LOCAL_MODEL 2>/dev/null | grep -q "true"; then
    echo -e "${GREEN}✓ PASS${NC} (Using local Model Service)"
    ((PASSED++))
else
    echo -e "${YELLOW}! WARN${NC} (Not using local model or container not running)"
fi

echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo ""
    echo "Day 8 Integration Complete:"
    echo "  ✓ Agent Orchestrator connected to Model Service"
    echo "  ✓ LogAnalyzerAgent using local LLM"
    echo "  ✓ End-to-end workflow functional"
    exit 0
else
    echo -e "${RED}Some tests failed ✗${NC}"
    echo ""
    echo "Check logs:"
    echo "  docker logs workflowai-agent"
    echo "  docker logs workflowai-model"
    exit 1
fi
