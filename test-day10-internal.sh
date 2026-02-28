#!/bin/bash

# WorkflowAI - Day 10 RAG Integration Test (Docker Internal)
# Runs INSIDE Docker network to bypass corporate proxy

set -e

echo "========================================"
echo "Day 10 RAG Test (Docker Internal)"
echo "========================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
PASSED=0
FAILED=0

# Service URLs (Docker internal DNS)
INDEXING_URL="http://indexing:8000"
AGENT_URL="http://agent-orchestrator:8000"
ES_URL="http://elasticsearch:9200"

# Helper functions
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $2"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $2"
        ((FAILED++))
    fi
}

print_section() {
    echo ""
    echo -e "${BLUE}=== $1 ===${NC}"
    echo ""
}

# Wait for services to be ready
wait_for_service() {
    local url=$1
    local name=$2
    local max_attempts=30
    local attempt=0
    
    echo "Waiting for $name..."
    while [ $attempt -lt $max_attempts ]; do
        if curl -sf "$url" > /dev/null 2>&1; then
            echo "  ✓ $name is ready"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 2
    done
    
    echo "  ✗ $name failed to start after ${max_attempts} attempts"
    return 1
}

print_section "Step 1: Wait for Services"

wait_for_service "$ES_URL/_cluster/health" "Elasticsearch"
wait_for_service "$INDEXING_URL/health" "Indexing Service"
wait_for_service "$AGENT_URL/health" "Agent Orchestrator"

print_section "Step 2: Check Services Health"

# Test 1: Elasticsearch Health
echo "Testing Elasticsearch Health..."
response=$(curl -s -w "%{http_code}" -o /dev/null "$ES_URL/_cluster/health")
if [ "$response" = "200" ]; then
    print_result 0 "Elasticsearch Health (HTTP $response)"
else
    print_result 1 "Elasticsearch Health (HTTP $response)"
fi

# Test 2: Indexing Service Health
echo "Testing Indexing Service Health..."
health_response=$(curl -s "$INDEXING_URL/health")
if echo "$health_response" | grep -q '"status":"healthy"'; then
    print_result 0 "Indexing Service Health"
    
    # Check ES connection
    if echo "$health_response" | grep -q '"elasticsearch_connected":true'; then
        echo "  ✓ Elasticsearch connected"
    else
        echo "  ✗ Elasticsearch not connected"
    fi
    
    # Check model loaded
    if echo "$health_response" | grep -q '"model_loaded":true'; then
        echo "  ✓ Embedding model loaded"
    else
        echo "  ⚠ Embedding model not loaded yet (may still be loading)"
    fi
else
    print_result 1 "Indexing Service Health"
    echo "  Response: $health_response"
fi

# Test 3: Agent Orchestrator Health
echo "Testing Agent Orchestrator Health..."
response=$(curl -s -w "%{http_code}" -o /dev/null "$AGENT_URL/health")
if [ "$response" = "200" ]; then
    print_result 0 "Agent Orchestrator Health (HTTP $response)"
else
    print_result 1 "Agent Orchestrator Health (HTTP $response)"
fi

print_section "Step 3: Populate Knowledge Base"

# Test 4: Check if knowledge base is populated
echo "Checking Knowledge Base statistics..."
stats_response=$(curl -s "$INDEXING_URL/stats")
doc_count=$(echo "$stats_response" | grep -o '"document_count":[0-9]*' | grep -o '[0-9]*')

if [ -z "$doc_count" ] || [ "$doc_count" -eq 0 ]; then
    echo -e "${YELLOW}Knowledge base is empty. Populating with sample data...${NC}"
    
    # Run populate script inside indexing container
    echo "Running populate_kb.py inside indexing container..."
    docker exec workflowai-indexing python /app/populate_kb.py
    
    # Wait a bit for indexing to complete
    sleep 5
    
    # Check again
    stats_response=$(curl -s "$INDEXING_URL/stats")
    doc_count=$(echo "$stats_response" | grep -o '"document_count":[0-9]*' | grep -o '[0-9]*')
fi

if [ "$doc_count" -gt 0 ]; then
    print_result 0 "Knowledge Base Population ($doc_count documents)"
    echo "  Index: $(echo "$stats_response" | grep -o '"index":"[^"]*"' | cut -d'"' -f4)"
    size_bytes=$(echo "$stats_response" | grep -o '"size_bytes":[0-9]*' | grep -o '[0-9]*')
    if [ -n "$size_bytes" ] && [ "$size_bytes" -gt 0 ]; then
        size_mb=$(awk "BEGIN {printf \"%.2f\", $size_bytes/1024/1024}")
        echo "  Size: ${size_mb} MB"
    fi
else
    print_result 1 "Knowledge Base Population (0 documents)"
fi

print_section "Step 4: Test Hybrid Search"

# Test 5: Semantic search
echo "Testing Semantic Search..."
search_response=$(curl -s -X POST "$INDEXING_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "NullPointerException error in Java",
        "top_k": 3,
        "search_type": "semantic"
    }')

if echo "$search_response" | grep -q '"results"'; then
    result_count=$(echo "$search_response" | grep -o '"id"' | wc -l)
    print_result 0 "Semantic Search ($result_count results)"
    
    if [ "$result_count" -gt 0 ]; then
        top_title=$(echo "$search_response" | grep -o '"title":"[^"]*"' | head -1 | cut -d'"' -f4)
        top_score=$(echo "$search_response" | grep -o '"score":[0-9.]*' | head -1 | grep -o '[0-9.]*')
        echo "  Top result: $top_title (score: $top_score)"
    fi
else
    print_result 1 "Semantic Search"
    echo "  Response: $search_response"
fi

# Test 6: Hybrid search
echo "Testing Hybrid Search..."
search_response=$(curl -s -X POST "$INDEXING_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "database connection timeout PostgreSQL",
        "top_k": 3,
        "search_type": "hybrid"
    }')

if echo "$search_response" | grep -q '"results"'; then
    result_count=$(echo "$search_response" | grep -o '"id"' | wc -l)
    print_result 0 "Hybrid Search ($result_count results)"
    
    if [ "$result_count" -gt 0 ]; then
        top_title=$(echo "$search_response" | grep -o '"title":"[^"]*"' | head -1 | cut -d'"' -f4)
        echo "  Top result: $top_title"
    fi
else
    print_result 1 "Hybrid Search"
    echo "  Response: $search_response"
fi

print_section "Step 5: Test RAG Integration"

# Test 7: Agent log analysis WITH RAG
echo "Testing Agent Analysis WITH RAG..."
rag_response=$(curl -s -X POST "$AGENT_URL/workflows/analyze-log" \
    -H "Content-Type: application/json" \
    -d '{
        "log_content": "Exception in thread \"main\" java.lang.NullPointerException: Cannot invoke method getName() on null object\n\tat com.example.UserService.getProfile(UserService.java:42)\n\tat com.example.Main.main(Main.java:15)",
        "log_type": "runtime",
        "use_knowledge_base": true
    }')

if echo "$rag_response" | grep -q '"root_cause"'; then
    print_result 0 "Agent Analysis WITH RAG"
    
    # Check if knowledge base was used
    if echo "$rag_response" | grep -qi "similar\|reference\|knowledge base\|documented\|context"; then
        echo "  ✓ RAG context detected in response"
    else
        echo "  ⚠ RAG context not clearly visible (check logs)"
    fi
    
    root_cause=$(echo "$rag_response" | grep -o '"root_cause":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "  Root Cause: ${root_cause:0:100}..."
else
    print_result 1 "Agent Analysis WITH RAG"
    echo "  Response: ${rag_response:0:200}..."
fi

# Test 8: RAG with OOM error
echo "Testing RAG with OutOfMemoryError..."
oom_response=$(curl -s -X POST "$AGENT_URL/workflows/analyze-log" \
    -H "Content-Type: application/json" \
    -d '{
        "log_content": "java.lang.OutOfMemoryError: Java heap space\n\tat com.example.BatchProcessor.processRecords(BatchProcessor.java:156)\n\tat com.example.DataPipeline.run(DataPipeline.java:89)",
        "log_type": "runtime",
        "use_knowledge_base": true
    }')

if echo "$oom_response" | grep -q '"root_cause"'; then
    print_result 0 "RAG with OutOfMemoryError"
    
    # Check for memory-specific suggestions
    if echo "$oom_response" | grep -qi "heap\|memory\|pagination\|batch\|streaming"; then
        echo "  ✓ Memory-specific suggestions found"
    fi
else
    print_result 1 "RAG with OutOfMemoryError"
fi

print_section "Test Summary"

echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Day 10 Implementation Complete:"
    echo "- ✓ Elasticsearch knowledge base populated ($doc_count documents)"
    echo "- ✓ Hybrid search (semantic + keyword)"
    echo "- ✓ RAG pipeline integrated with Agent"
    echo "- ✓ Context-aware failure analysis"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Check container logs:"
    echo "  docker logs workflowai-indexing"
    echo "  docker logs workflowai-agent-orchestrator"
    echo "  docker logs workflowai-elasticsearch"
    echo ""
    exit 1
fi
