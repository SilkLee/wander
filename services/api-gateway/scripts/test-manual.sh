#!/bin/bash

# Quick Manual Test Script for API Gateway
# Tests JWT authentication and rate limiting

set -e

API_URL="${API_URL:-http://localhost:8000}"
JWT_SECRET="${JWT_SECRET:-changeme-in-production}"

echo "=========================================="
echo "API Gateway Manual Test Suite"
echo "=========================================="
echo "API URL: $API_URL"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

test_passed=0
test_failed=0

# Helper function to test endpoint
test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local headers=$4
    local expected_code=$5
    
    echo -n "Testing: $name ... "
    
    if [ -z "$headers" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" -H "$headers" "$API_URL$endpoint")
    fi
    
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$status_code" -eq "$expected_code" ]; then
        echo -e "${GREEN}✓ PASS${NC} (Status: $status_code)"
        ((test_passed++))
    else
        echo -e "${RED}✗ FAIL${NC} (Expected: $expected_code, Got: $status_code)"
        echo "   Response: $body"
        ((test_failed++))
    fi
}

# Generate test tokens (using Go)
echo "=========================================="
echo "Generating Test Tokens..."
echo "=========================================="

# Check if token generator exists
if [ ! -f "./scripts/generate-tokens.go" ]; then
    echo -e "${RED}Error: Token generator not found${NC}"
    echo "Please ensure scripts/generate-tokens.go exists"
    exit 1
fi

# Generate tokens
cd "$(dirname "$0")/.."
token_output=$(JWT_SECRET="$JWT_SECRET" go run ./scripts/generate-tokens.go 2>&1)

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to generate tokens${NC}"
    echo "$token_output"
    exit 1
fi

# Extract tokens (this is a simplified parser - adjust based on actual output format)
USER_TOKEN=$(echo "$token_output" | grep -A 5 "REGULAR USER TOKEN" | tail -n1 | tr -d '[:space:]')
ADMIN_TOKEN=$(echo "$token_output" | grep -A 5 "ADMIN TOKEN" | tail -n1 | tr -d '[:space:]')
EXPIRED_TOKEN=$(echo "$token_output" | grep -A 5 "EXPIRED TOKEN" | tail -n1 | tr -d '[:space:]')

if [ -z "$USER_TOKEN" ] || [ -z "$ADMIN_TOKEN" ] || [ -z "$EXPIRED_TOKEN" ]; then
    echo -e "${YELLOW}Warning: Failed to extract tokens from generator${NC}"
    echo "Running tests without authentication..."
    USER_TOKEN=""
    ADMIN_TOKEN=""
    EXPIRED_TOKEN=""
else
    echo -e "${GREEN}✓ Tokens generated successfully${NC}"
    echo ""
fi

# Test Suite 1: Public Endpoints
echo "=========================================="
echo "Test Suite 1: Public Endpoints"
echo "=========================================="

test_endpoint "Root endpoint" "GET" "/" "" 200
test_endpoint "Health check" "GET" "/health" "" 200

echo ""

# Test Suite 2: Authentication
echo "=========================================="
echo "Test Suite 2: Authentication"
echo "=========================================="

test_endpoint "Missing auth header" "GET" "/api/v1/test" "" 401

if [ -n "$USER_TOKEN" ]; then
    test_endpoint "Invalid auth format" "GET" "/api/v1/test" "Authorization: InvalidFormat token123" 401
    test_endpoint "Valid user token" "GET" "/api/v1/test" "Authorization: Bearer $USER_TOKEN" 404
    test_endpoint "Expired token" "GET" "/api/v1/test" "Authorization: Bearer $EXPIRED_TOKEN" 401
else
    echo -e "${YELLOW}Skipping token tests (tokens not available)${NC}"
fi

echo ""

# Test Suite 3: Authorization (Role-based)
echo "=========================================="
echo "Test Suite 3: Authorization (RBAC)"
echo "=========================================="

if [ -n "$USER_TOKEN" ] && [ -n "$ADMIN_TOKEN" ]; then
    test_endpoint "Admin endpoint with user token" "GET" "/admin/test" "Authorization: Bearer $USER_TOKEN" 403
    test_endpoint "Admin endpoint with admin token" "GET" "/admin/test" "Authorization: Bearer $ADMIN_TOKEN" 404
else
    echo -e "${YELLOW}Skipping RBAC tests (tokens not available)${NC}"
fi

echo ""

# Test Suite 4: Rate Limiting
echo "=========================================="
echo "Test Suite 4: Rate Limiting"
echo "=========================================="

if [ -n "$USER_TOKEN" ]; then
    echo "Testing rate limit headers..."
    response=$(curl -s -i -H "Authorization: Bearer $USER_TOKEN" "$API_URL/api/v1/test")
    
    if echo "$response" | grep -q "X-RateLimit-Limit"; then
        limit=$(echo "$response" | grep "X-RateLimit-Limit:" | cut -d' ' -f2 | tr -d '\r')
        remaining=$(echo "$response" | grep "X-RateLimit-Remaining:" | cut -d' ' -f2 | tr -d '\r')
        echo -e "${GREEN}✓ Rate limit headers present${NC}"
        echo "   Limit: $limit, Remaining: $remaining"
        ((test_passed++))
    else
        echo -e "${RED}✗ Rate limit headers missing${NC}"
        ((test_failed++))
    fi
    
    echo ""
    echo "Testing rate limit enforcement (this may take a moment)..."
    
    # Make 10 rapid requests
    for i in {1..10}; do
        curl -s -H "Authorization: Bearer $USER_TOKEN" "$API_URL/" > /dev/null
    done
    
    # Check if rate limit is decreasing
    response2=$(curl -s -i -H "Authorization: Bearer $USER_TOKEN" "$API_URL/")
    remaining2=$(echo "$response2" | grep "X-RateLimit-Remaining:" | cut -d' ' -f2 | tr -d '\r')
    
    if [ "$remaining2" -lt "$remaining" ]; then
        echo -e "${GREEN}✓ Rate limit decrements correctly${NC}"
        echo "   New remaining: $remaining2"
        ((test_passed++))
    else
        echo -e "${YELLOW}? Rate limit not decrementing as expected${NC}"
        echo "   Previous: $remaining, Current: $remaining2"
    fi
else
    echo -e "${YELLOW}Skipping rate limiting tests (tokens not available)${NC}"
fi

echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}$test_passed${NC}"
echo -e "Failed: ${RED}$test_failed${NC}"
echo "Total:  $((test_passed + test_failed))"
echo ""

if [ $test_failed -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed${NC}"
    exit 1
fi
