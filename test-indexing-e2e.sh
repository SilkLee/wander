#!/bin/bash

# E2E Test Script for Indexing Service
# Tests document indexing, batch operations, and all search types

set -e

# Configure proxy bypass for localhost
export NO_PROXY=localhost,127.0.0.1

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Base URL
INDEXING_URL="http://localhost:8003"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Utility functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_test() {
    echo -e "${YELLOW}TEST:${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
    ((TESTS_FAILED++))
}

# Wait for service to be ready
wait_for_service() {
    print_header "Waiting for Indexing Service to be ready..."
    
    MAX_RETRIES=30
    RETRY_COUNT=0
    
    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -sf "$INDEXING_URL/health" > /dev/null 2>&1; then
            print_success "Indexing service is ready"
            return 0
        fi
        
        echo "Waiting for service... (attempt $((RETRY_COUNT+1))/$MAX_RETRIES)"
        sleep 2
        ((RETRY_COUNT++))
    done
    
    print_fail "Service did not become ready in time"
    exit 1
}

# Test 1: Health Check
test_health_check() {
    print_header "Test 1: Health Check Endpoints"
    
    # Test /health
    print_test "GET /health"
    RESPONSE=$(curl -s -w "\n%{http_code}" "$INDEXING_URL/health")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "/health returned 200 OK"
        echo "Response: $BODY"
    else
        print_fail "/health returned $HTTP_CODE"
    fi
    
    # Test /ready
    print_test "GET /ready"
    RESPONSE=$(curl -s -w "\n%{http_code}" "$INDEXING_URL/ready")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "/ready returned 200 OK"
    else
        print_fail "/ready returned $HTTP_CODE"
    fi
    
    # Test /live
    print_test "GET /live"
    RESPONSE=$(curl -s -w "\n%{http_code}" "$INDEXING_URL/live")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "/live returned 200 OK"
    else
        print_fail "/live returned $HTTP_CODE"
    fi
}

# Test 2: Index Single Document
test_index_single() {
    print_header "Test 2: Index Single Document"
    
    print_test "POST /index - Index test document"
    
    REQUEST_BODY='{
        "doc_id": "test-001",
        "title": "Test Document for E2E Testing",
        "content": "This is a test document created during end-to-end testing of the indexing service. It contains sample content for validation purposes.",
        "metadata": {
            "source": "e2e-test",
            "category": "testing",
            "tags": ["test", "e2e", "validation"]
        }
    }'
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$INDEXING_URL/index" \
        -H "Content-Type: application/json" \
        -d "$REQUEST_BODY")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Document indexed successfully"
        echo "Response: $BODY"
    else
        print_fail "Failed to index document (HTTP $HTTP_CODE)"
        echo "Response: $BODY"
    fi
}

# Test 3: Batch Index
test_batch_index() {
    print_header "Test 3: Batch Index Documents"
    
    print_test "POST /index/batch - Index multiple documents"
    
    REQUEST_BODY='{
        "documents": [
            {
                "doc_id": "test-002",
                "title": "Python FastAPI Performance Tips",
                "content": "FastAPI is a modern, fast web framework for building APIs with Python. Performance tips include using async/await properly, enabling gzip compression, and implementing caching strategies.",
                "metadata": {
                    "source": "e2e-test",
                    "category": "programming",
                    "language": "python",
                    "tags": ["fastapi", "performance", "python"]
                }
            },
            {
                "doc_id": "test-003",
                "title": "Docker Container Networking Basics",
                "content": "Docker containers can communicate using bridge networks, host networks, or overlay networks. Understanding container networking is essential for microservices architecture.",
                "metadata": {
                    "source": "e2e-test",
                    "category": "devops",
                    "technology": "docker",
                    "tags": ["docker", "networking", "containers"]
                }
            },
            {
                "doc_id": "test-004",
                "title": "Elasticsearch Query DSL Tutorial",
                "content": "Elasticsearch Query DSL provides a powerful way to query documents. Common query types include match, term, range, and bool queries for complex searches.",
                "metadata": {
                    "source": "e2e-test",
                    "category": "database",
                    "technology": "elasticsearch",
                    "tags": ["elasticsearch", "query", "search"]
                }
            }
        ]
    }'
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$INDEXING_URL/index/batch" \
        -H "Content-Type: application/json" \
        -d "$REQUEST_BODY")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Batch indexing completed"
        echo "Response: $BODY"
    else
        print_fail "Batch indexing failed (HTTP $HTTP_CODE)"
        echo "Response: $BODY"
    fi
}

# Test 4: Semantic Search
test_semantic_search() {
    print_header "Test 4: Semantic Search"
    
    print_test "POST /search - Semantic search for 'python api performance'"
    
    REQUEST_BODY='{
        "query": "python api performance",
        "search_type": "semantic",
        "top_k": 3
    }'
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$INDEXING_URL/search" \
        -H "Content-Type: application/json" \
        -d "$REQUEST_BODY")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Semantic search successful"
        echo "Response: $BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    else
        print_fail "Semantic search failed (HTTP $HTTP_CODE)"
        echo "Response: $BODY"
    fi
}

# Test 5: Keyword Search
test_keyword_search() {
    print_header "Test 5: Keyword Search"
    
    print_test "POST /search - Keyword search for 'docker networking'"
    
    REQUEST_BODY='{
        "query": "docker networking",
        "search_type": "keyword",
        "top_k": 3
    }'
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$INDEXING_URL/search" \
        -H "Content-Type: application/json" \
        -d "$REQUEST_BODY")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Keyword search successful"
        echo "Response: $BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    else
        print_fail "Keyword search failed (HTTP $HTTP_CODE)"
        echo "Response: $BODY"
    fi
}

# Test 6: Hybrid Search
test_hybrid_search() {
    print_header "Test 6: Hybrid Search (Semantic + Keyword)"
    
    print_test "POST /search - Hybrid search for 'elasticsearch query language'"
    
    REQUEST_BODY='{
        "query": "elasticsearch query language",
        "search_type": "hybrid",
        "top_k": 5,
        "semantic_weight": 0.6
    }'
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$INDEXING_URL/search" \
        -H "Content-Type: application/json" \
        -d "$REQUEST_BODY")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Hybrid search successful"
        echo "Response: $BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    else
        print_fail "Hybrid search failed (HTTP $HTTP_CODE)"
        echo "Response: $BODY"
    fi
}

# Test 7: Search with Filters
test_filtered_search() {
    print_header "Test 7: Search with Metadata Filters"
    
    print_test "POST /search - Search with category filter"
    
    REQUEST_BODY='{
        "query": "performance optimization",
        "search_type": "hybrid",
        "top_k": 3,
        "filters": {
            "category": "programming"
        }
    }'
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$INDEXING_URL/search" \
        -H "Content-Type: application/json" \
        -d "$REQUEST_BODY")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Filtered search successful"
        echo "Response: $BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    else
        print_fail "Filtered search failed (HTTP $HTTP_CODE)"
        echo "Response: $BODY"
    fi
}

# Test 8: Stats Endpoint
test_stats() {
    print_header "Test 8: Index Statistics"
    
    print_test "GET /stats - Get index statistics"
    
    RESPONSE=$(curl -s -w "\n%{http_code}" "$INDEXING_URL/stats")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_success "Stats endpoint successful"
        echo "Response: $BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    else
        print_fail "Stats endpoint failed (HTTP $HTTP_CODE)"
        echo "Response: $BODY"
    fi
}

# Test 9: Error Handling
test_error_handling() {
    print_header "Test 9: Error Handling"
    
    # Test missing required field
    print_test "POST /index - Test with missing required field"
    
    REQUEST_BODY='{
        "doc_id": "test-invalid",
        "title": "Missing Content Field"
    }'
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$INDEXING_URL/index" \
        -H "Content-Type: application/json" \
        -d "$REQUEST_BODY")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    
    if [ "$HTTP_CODE" = "422" ]; then
        print_success "Validation error correctly returned 422"
    else
        print_fail "Expected 422 validation error, got $HTTP_CODE"
    fi
    
    # Test invalid search type
    print_test "POST /search - Test with invalid search type"
    
    REQUEST_BODY='{
        "query": "test",
        "search_type": "invalid_type",
        "top_k": 3
    }'
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$INDEXING_URL/search" \
        -H "Content-Type: application/json" \
        -d "$REQUEST_BODY")
    
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    
    if [ "$HTTP_CODE" = "422" ]; then
        print_success "Invalid search type correctly returned 422"
    else
        print_fail "Expected 422 validation error, got $HTTP_CODE"
    fi
}

# Main test execution
main() {
    print_header "Indexing Service E2E Tests"
    echo "Testing service at: $INDEXING_URL"
    
    # Wait for service
    wait_for_service
    
    # Run all tests
    test_health_check
    test_index_single
    test_batch_index
    
    # Wait a bit for indexing to complete
    echo -e "\nWaiting 3 seconds for documents to be indexed..."
    sleep 3
    
    test_semantic_search
    test_keyword_search
    test_hybrid_search
    test_filtered_search
    test_stats
    test_error_handling
    
    # Print summary
    print_header "Test Summary"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo -e "Total: $((TESTS_PASSED + TESTS_FAILED))"
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "\n${GREEN}All tests passed! ✓${NC}\n"
        exit 0
    else
        echo -e "\n${RED}Some tests failed! ✗${NC}\n"
        exit 1
    fi
}

# Run main
main
