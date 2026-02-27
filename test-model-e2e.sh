#!/usr/bin/env bash
#
# End-to-End Test Script for Model Service
# Tests all API endpoints and validates model functionality
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost:8004"
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Helper functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_test() {
    ((TOTAL_TESTS++))
    echo -e "${YELLOW}[TEST $TOTAL_TESTS]${NC} $1"
}

print_success() {
    ((PASSED_TESTS++))
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    ((FAILED_TESTS++))
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Test function with retry
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local description=$4
    local expected_status=${5:-200}
    
    print_test "$description"
    
    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" == "$expected_status" ]; then
        print_success "HTTP $http_code - $description"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
        return 0
    else
        print_error "HTTP $http_code (expected $expected_status) - $description"
        echo "$body"
        return 1
    fi
}

# Main test execution
main() {
    print_header "Model Service E2E Test Suite"
    
    print_info "Testing Model Service at $BASE_URL"
    print_info "Make sure the service is running: docker compose up -d model-service"
    echo ""
    
    # Test 1: Root endpoint
    print_header "Test 1: Root Endpoint"
    test_endpoint "GET" "/" "" "Root endpoint should return service info"
    
    # Test 2: Liveness probe
    print_header "Test 2: Liveness Probe"
    test_endpoint "GET" "/live" "" "Liveness probe should return alive status"
    
    # Test 3: Readiness probe (may fail if model not loaded)
    print_header "Test 3: Readiness Probe"
    print_test "Check if service is ready (model loaded)"
    response=$(curl -s "$BASE_URL/ready")
    ready=$(echo "$response" | jq -r '.ready')
    
    if [ "$ready" == "true" ]; then
        print_success "Service is ready"
        echo "$response" | jq '.'
    else
        print_error "Service not ready (model may still be loading)"
        echo "$response" | jq '.'
        print_info "Waiting 30 seconds for model to load..."
        sleep 30
    fi
    
    # Test 4: Health check
    print_header "Test 4: Health Check"
    test_endpoint "GET" "/health" "" "Health check should return service status"
    
    print_test "Validate health response structure"
    health_response=$(curl -s "$BASE_URL/health")
    
    status=$(echo "$health_response" | jq -r '.status')
    service=$(echo "$health_response" | jq -r '.service')
    model_loaded=$(echo "$health_response" | jq -r '.model_loaded')
    model_name=$(echo "$health_response" | jq -r '.model_name')
    
    if [ "$service" == "model-service" ] && [ "$model_loaded" == "true" ]; then
        print_success "Health check structure valid"
        echo "  Status: $status"
        echo "  Service: $service"
        echo "  Model Loaded: $model_loaded"
        echo "  Model Name: $model_name"
    else
        print_error "Health check structure invalid or model not loaded"
        echo "$health_response" | jq '.'
    fi
    
    # Test 5: Model info
    print_header "Test 5: Model Information"
    test_endpoint "GET" "/model/info" "" "Model info should return model details"
    
    print_test "Validate model info structure"
    info_response=$(curl -s "$BASE_URL/model/info")
    
    name=$(echo "$info_response" | jq -r '.name')
    type=$(echo "$info_response" | jq -r '.type')
    device=$(echo "$info_response" | jq -r '.device')
    
    if [ "$type" == "transformers" ]; then
        print_success "Model info structure valid"
        echo "  Name: $name"
        echo "  Type: $type"
        echo "  Device: $device"
        echo "$info_response" | jq '.parameters'
    else
        print_error "Model info structure invalid"
        echo "$info_response" | jq '.'
    fi
    
    # Test 6: Text generation - simple prompt
    print_header "Test 6: Text Generation (Simple)"
    simple_prompt='{"prompt": "Hello, how are you?", "max_tokens": 50, "temperature": 0.7}'
    test_endpoint "POST" "/generate" "$simple_prompt" "Generate text from simple prompt"
    
    print_test "Validate generation response"
    gen_response=$(curl -s -X POST "$BASE_URL/generate" \
        -H "Content-Type: application/json" \
        -d "$simple_prompt")
    
    text=$(echo "$gen_response" | jq -r '.text')
    tokens=$(echo "$gen_response" | jq -r '.tokens_generated')
    finish_reason=$(echo "$gen_response" | jq -r '.finish_reason')
    
    if [ -n "$text" ] && [ "$tokens" -gt 0 ]; then
        print_success "Generation successful"
        echo "  Generated Text: $text"
        echo "  Tokens Generated: $tokens"
        echo "  Finish Reason: $finish_reason"
    else
        print_error "Generation failed or returned empty"
        echo "$gen_response" | jq '.'
    fi
    
    # Test 7: Text generation - coding prompt
    print_header "Test 7: Text Generation (Coding)"
    coding_prompt='{"prompt": "Write a Python function to calculate fibonacci numbers:", "max_tokens": 100, "temperature": 0.3}'
    test_endpoint "POST" "/generate" "$coding_prompt" "Generate code from prompt"
    
    # Test 8: Text generation - zero temperature (deterministic)
    print_header "Test 8: Text Generation (Deterministic)"
    deterministic_prompt='{"prompt": "The capital of France is", "max_tokens": 10, "temperature": 0.0}'
    test_endpoint "POST" "/generate" "$deterministic_prompt" "Generate with temperature=0"
    
    # Test 9: Text generation - with stop sequence
    print_header "Test 9: Text Generation (With Stop Sequence)"
    stop_prompt='{"prompt": "List three colors:\n1.", "max_tokens": 50, "temperature": 0.5, "stop": ["\n4."]}'
    test_endpoint "POST" "/generate" "$stop_prompt" "Generate with stop sequence"
    
    # Test 10: Invalid request (missing prompt)
    print_header "Test 10: Error Handling (Missing Prompt)"
    invalid_request='{"max_tokens": 50}'
    test_endpoint "POST" "/generate" "$invalid_request" "Invalid request should return 422" 422
    
    # Summary
    print_header "Test Summary"
    echo -e "Total Tests:  ${BLUE}$TOTAL_TESTS${NC}"
    echo -e "Passed:       ${GREEN}$PASSED_TESTS${NC}"
    echo -e "Failed:       ${RED}$FAILED_TESTS${NC}"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}✓ All tests passed!${NC}"
        exit 0
    else
        echo -e "\n${RED}✗ Some tests failed${NC}"
        exit 1
    fi
}

# Run main function
main
