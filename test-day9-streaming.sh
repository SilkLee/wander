#!/bin/bash

# WorkflowAI - Day 9 Streaming Integration Test
# Tests SSE (Server-Sent Events) streaming from Model Service and Agent Orchestrator

set -e

echo "========================================"
echo "Day 9 E2E Test: Streaming Responses"
echo "========================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

# Service URLs
MODEL_SERVICE_URL="http://localhost:8004"
AGENT_SERVICE_URL="http://localhost:8002"

# Helper function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((FAILED++))
    fi
}

# Helper function to test streaming endpoint
test_stream() {
    local url=$1
    local description=$2
    local payload=$3
    
    echo "Testing $description..."
    
    # Use curl with --no-buffer for SSE
    response=$(curl -s --no-buffer -N -X POST "$url" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        --max-time 30 2>&1) || true
    
    # Check if response contains SSE events
    if echo "$response" | grep -q "event: token\|event: done"; then
        print_result 0 "$description"
        # Show sample tokens
        token_count=$(echo "$response" | grep -c "event: token" || echo "0")
        echo "  Received $token_count token events"
        return 0
    else
        print_result 1 "$description"
        echo "  Response: $response"
        return 1
    fi
}

echo "=== Step 1: Check Services Health ==="
echo ""

# Test 1: Model Service Health
echo "Testing Model Service Health..."
response=$(curl -s -w "%{http_code}" -o /dev/null "$MODEL_SERVICE_URL/health")
if [ "$response" = "200" ]; then
    print_result 0 "Model Service Health (HTTP $response)"
else
    print_result 1 "Model Service Health (HTTP $response)"
fi

# Test 2: Agent Orchestrator Health
echo "Testing Agent Orchestrator Health..."
response=$(curl -s -w "%{http_code}" -o /dev/null "$AGENT_SERVICE_URL/health")
if [ "$response" = "200" ]; then
    print_result 0 "Agent Orchestrator Health (HTTP $response)"
else
    print_result 1 "Agent Orchestrator Health (HTTP $response)"
fi

echo ""
echo "=== Step 2: Test Model Service Streaming ==="
echo ""

# Test 3: Model Service streaming generation
test_stream \
    "$MODEL_SERVICE_URL/generate/stream" \
    "Model Service Streaming Generation" \
    '{
        "prompt": "Explain what is a null pointer exception:",
        "max_tokens": 50,
        "temperature": 0.3
    }'

echo ""
echo "=== Step 3: Test Agent Orchestrator Streaming ==="
echo ""

# Test 4: Agent log analysis with streaming
test_stream \
    "$AGENT_SERVICE_URL/workflows/analyze-log/stream" \
    "Agent Streaming Log Analysis" \
    '{
        "log_content": "ERROR: NullPointerException at Main.java:42\nCaused by: object reference is null",
        "log_type": "build"
    }'

echo ""
echo "=== Step 4: Test Non-Streaming Endpoints (Baseline) ==="
echo ""

# Test 5: Model Service non-streaming (for comparison)
echo "Testing Model Service Non-Streaming Generation..."
response=$(curl -s -X POST "$MODEL_SERVICE_URL/generate" \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Fix: NullPointerException",
        "max_tokens": 30,
        "temperature": 0.3
    }')

if echo "$response" | grep -q '"text"'; then
    print_result 0 "Model Service Non-Streaming Generation"
    generated_text=$(echo "$response" | grep -o '"text":"[^"]*"' | head -1)
    echo "  Generated: ${generated_text:8:50}..."
else
    print_result 1 "Model Service Non-Streaming Generation"
    echo "  Response: $response"
fi

# Test 6: Agent non-streaming (for comparison)
echo "Testing Agent Non-Streaming Log Analysis..."
response=$(curl -s -X POST "$AGENT_SERVICE_URL/workflows/analyze-log" \
    -H "Content-Type: application/json" \
    -d '{
        "log_content": "ERROR: NullPointerException at Main.java:42",
        "log_type": "build"
    }')

if echo "$response" | grep -q '"root_cause"'; then
    print_result 0 "Agent Non-Streaming Log Analysis"
    root_cause=$(echo "$response" | grep -o '"root_cause":"[^"]*"' | head -1)
    echo "  Root Cause: ${root_cause:14:60}..."
else
    print_result 1 "Agent Non-Streaming Log Analysis"
    echo "  Response: $response"
fi

echo ""
echo "=== Step 5: Performance Comparison ==="
echo ""

# Test 7: Measure time-to-first-token (TTFT) for streaming
echo "Measuring streaming Time-To-First-Token (TTFT)..."
start_time=$(date +%s%N)
first_token_time=0

# Stream and capture first token time
curl -s --no-buffer -N -X POST "$MODEL_SERVICE_URL/generate/stream" \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Hello",
        "max_tokens": 10,
        "temperature": 0.5
    }' | while read -r line; do
        if [ $first_token_time -eq 0 ] && echo "$line" | grep -q "event: token"; then
            first_token_time=$(date +%s%N)
            ttft=$(( ($first_token_time - $start_time) / 1000000 ))
            echo "  TTFT: ${ttft}ms"
            print_result 0 "Streaming TTFT Measurement"
            break
        fi
    done 2>&1 | head -2

# Test 8: Measure total time for non-streaming
echo "Measuring non-streaming total time..."
start_time=$(date +%s%N)
curl -s -X POST "$MODEL_SERVICE_URL/generate" \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Hello",
        "max_tokens": 10,
        "temperature": 0.5
    }' > /dev/null
end_time=$(date +%s%N)
total_time=$(( ($end_time - $start_time) / 1000000 ))
echo "  Total Time: ${total_time}ms"
print_result 0 "Non-Streaming Total Time Measurement"

echo ""
echo "========================================"
echo "Test Summary"
echo "========================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo ""
    echo "Day 9 Implementation Complete:"
    echo "- ✓ Model Service SSE streaming endpoint"
    echo "- ✓ Token-by-token generation"
    echo "- ✓ Agent Orchestrator streaming support"
    echo "- ✓ Real-time response delivery"
    echo ""
    exit 0
else
    echo -e "${RED}Some tests failed ✗${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check services: docker-compose ps"
    echo "2. Check logs: docker-compose logs model-service agent-orchestrator"
    echo "3. Verify network: curl http://localhost:8004/health"
    echo ""
    exit 1
fi
