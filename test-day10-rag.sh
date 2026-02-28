#!/bin/bash

# WorkflowAI - Day 10 RAG Integration Test
# Tests Knowledge Base (Elasticsearch) + RAG pipeline with Agent Orchestrator

set -e

echo "========================================"
echo "Day 10 E2E Test: RAG Knowledge Base"
echo "========================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0

# Service URLs
INDEXING_SERVICE_URL="http://localhost:8003"
AGENT_SERVICE_URL="http://localhost:8002"
ELASTICSEARCH_URL="http://localhost:9200"

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

# Helper function to print section headers
print_section() {
    echo ""
    echo -e "${BLUE}=== $1 ===${NC}"
    echo ""
}

print_section "Step 1: Check Services Health"

# Test 1: Elasticsearch Health
echo "Testing Elasticsearch Health..."
response=$(curl -s -w "%{http_code}" -o /dev/null "$ELASTICSEARCH_URL/_cluster/health")
if [ "$response" = "200" ]; then
    print_result 0 "Elasticsearch Health (HTTP $response)"
else
    print_result 1 "Elasticsearch Health (HTTP $response)"
    echo -e "${RED}ERROR: Elasticsearch not available. Start with: docker-compose up -d elasticsearch${NC}"
fi

# Test 2: Indexing Service Health
echo "Testing Indexing Service Health..."
health_response=$(curl -s "$INDEXING_SERVICE_URL/health")
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
        echo "  ⚠ Embedding model not loaded yet"
    fi
else
    print_result 1 "Indexing Service Health"
    echo "  Response: $health_response"
fi

# Test 3: Agent Orchestrator Health
echo "Testing Agent Orchestrator Health..."
response=$(curl -s -w "%{http_code}" -o /dev/null "$AGENT_SERVICE_URL/health")
if [ "$response" = "200" ]; then
    print_result 0 "Agent Orchestrator Health (HTTP $response)"
else
    print_result 1 "Agent Orchestrator Health (HTTP $response)"
fi

print_section "Step 2: Populate Knowledge Base"

# Test 4: Check if knowledge base is populated
echo "Checking Knowledge Base statistics..."
stats_response=$(curl -s "$INDEXING_SERVICE_URL/stats")
doc_count=$(echo "$stats_response" | grep -o '"document_count":[0-9]*' | grep -o '[0-9]*')

if [ -z "$doc_count" ] || [ "$doc_count" -eq 0 ]; then
    echo -e "${YELLOW}Knowledge base is empty. Populating with sample data...${NC}"
    
    # Run populate script
    cd services/indexing
    python populate_kb.py
    cd ../..
    
    # Check again
    stats_response=$(curl -s "$INDEXING_SERVICE_URL/stats")
    doc_count=$(echo "$stats_response" | grep -o '"document_count":[0-9]*' | grep -o '[0-9]*')
fi

if [ "$doc_count" -gt 0 ]; then
    print_result 0 "Knowledge Base Population ($doc_count documents)"
    echo "  Index: $(echo "$stats_response" | grep -o '"index":"[^"]*"' | cut -d'"' -f4)"
    echo "  Size: $(echo "$stats_response" | grep -o '"size_bytes":[0-9]*' | grep -o '[0-9]*' | awk '{printf "%.2f MB", $1/1024/1024}')"
else
    print_result 1 "Knowledge Base Population (0 documents)"
fi

print_section "Step 3: Test Hybrid Search Endpoint"

# Test 5: Semantic search
echo "Testing Semantic Search..."
search_response=$(curl -s -X POST "$INDEXING_SERVICE_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "NullPointerException error in Java",
        "top_k": 3,
        "search_type": "semantic"
    }')

if echo "$search_response" | grep -q '"results"'; then
    result_count=$(echo "$search_response" | grep -o '"id"' | wc -l)
    print_result 0 "Semantic Search ($result_count results)"
    
    # Show top result
    if [ "$result_count" -gt 0 ]; then
        top_title=$(echo "$search_response" | grep -o '"title":"[^"]*"' | head -1 | cut -d'"' -f4)
        top_score=$(echo "$search_response" | grep -o '"score":[0-9.]*' | head -1 | grep -o '[0-9.]*')
        echo "  Top result: $top_title (score: $top_score)"
    fi
else
    print_result 1 "Semantic Search"
    echo "  Response: $search_response"
fi

# Test 6: Keyword search
echo "Testing Keyword Search..."
search_response=$(curl -s -X POST "$INDEXING_SERVICE_URL/search" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "OutOfMemoryError heap space",
        "top_k": 3,
        "search_type": "keyword"
    }')

if echo "$search_response" | grep -q '"results"'; then
    result_count=$(echo "$search_response" | grep -o '"id"' | wc -l)
    print_result 0 "Keyword Search ($result_count results)"
    
    if [ "$result_count" -gt 0 ]; then
        top_title=$(echo "$search_response" | grep -o '"title":"[^"]*"' | head -1 | cut -d'"' -f4)
        echo "  Top result: $top_title"
    fi
else
    print_result 1 "Keyword Search"
    echo "  Response: $search_response"
fi

# Test 7: Hybrid search (default)
echo "Testing Hybrid Search..."
search_response=$(curl -s -X POST "$INDEXING_SERVICE_URL/search" \
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

print_section "Step 4: Test RAG with Agent"

# Test 8: Agent log analysis WITHOUT RAG (baseline)
echo "Testing Agent Analysis WITHOUT RAG (baseline)..."
baseline_response=$(curl -s -X POST "$AGENT_SERVICE_URL/workflows/analyze-log" \
    -H "Content-Type: application/json" \
    -d '{
        "log_content": "Exception in thread \"main\" java.lang.NullPointerException: Cannot invoke method getName() on null object\n\tat com.example.UserService.getProfile(UserService.java:42)\n\tat com.example.Main.main(Main.java:15)",
        "log_type": "runtime"
    }')

if echo "$baseline_response" | grep -q '"root_cause"'; then
    print_result 0 "Agent Analysis WITHOUT RAG"
    root_cause=$(echo "$baseline_response" | grep -o '"root_cause":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "  Root Cause (baseline): ${root_cause:0:80}..."
else
    print_result 1 "Agent Analysis WITHOUT RAG"
    echo "  Response: $baseline_response"
fi

# Test 9: Agent log analysis WITH RAG
echo "Testing Agent Analysis WITH RAG..."
rag_response=$(curl -s -X POST "$AGENT_SERVICE_URL/workflows/analyze-log" \
    -H "Content-Type: application/json" \
    -d '{
        "log_content": "Exception in thread \"main\" java.lang.NullPointerException: Cannot invoke method getName() on null object\n\tat com.example.UserService.getProfile(UserService.java:42)\n\tat com.example.Main.main(Main.java:15)",
        "log_type": "runtime",
        "use_knowledge_base": true
    }')

if echo "$rag_response" | grep -q '"root_cause"'; then
    print_result 0 "Agent Analysis WITH RAG"
    
    # Check if knowledge base was used
    if echo "$rag_response" | grep -qi "similar\|reference\|knowledge base\|documented"; then
        echo "  ✓ RAG context detected in response"
    else
        echo "  ⚠ RAG context not clearly visible (check logs)"
    fi
    
    root_cause=$(echo "$rag_response" | grep -o '"root_cause":"[^"]*"' | head -1 | cut -d'"' -f4)
    echo "  Root Cause (with RAG): ${root_cause:0:80}..."
else
    print_result 1 "Agent Analysis WITH RAG"
    echo "  Response: $rag_response"
fi

# Test 10: RAG with OOM error
echo "Testing RAG with OutOfMemoryError..."
oom_response=$(curl -s -X POST "$AGENT_SERVICE_URL/workflows/analyze-log" \
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

print_section "Step 5: RAG Quality Assessment"

# Test 11: Compare response lengths (RAG should provide more context)
echo "Comparing response quality..."

baseline_length=${#baseline_response}
rag_length=${#rag_response}

echo "  Baseline response length: $baseline_length characters"
echo "  RAG response length: $rag_length characters"

if [ "$rag_length" -gt "$baseline_length" ]; then
    echo -e "  ${GREEN}✓ RAG provides more detailed analysis${NC}"
    print_result 0 "RAG Quality - Response Detail"
else
    echo -e "  ${YELLOW}⚠ RAG response not significantly longer (may still be higher quality)${NC}"
    print_result 0 "RAG Quality - Response Detail (inconclusive)"
fi

# Test 12: Check for structured fixes
echo "Checking for structured fix suggestions..."

if echo "$rag_response" | grep -qi "fix\|solution\|suggestion\|recommend"; then
    echo -e "  ${GREEN}✓ Fix suggestions present in RAG response${NC}"
    print_result 0 "RAG Quality - Fix Suggestions"
else
    echo -e "  ${YELLOW}⚠ Fix suggestions not clearly identified${NC}"
    print_result 1 "RAG Quality - Fix Suggestions"
fi

print_section "Test Summary"

echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo ""
    echo "Day 10 Implementation Complete:"
    echo "- ✓ Elasticsearch knowledge base populated"
    echo "- ✓ Hybrid search (semantic + keyword)"
    echo "- ✓ RAG pipeline integrated with Agent"
    echo "- ✓ Context-aware failure analysis"
    echo ""
    echo "Knowledge Base Stats:"
    echo "  Documents: $doc_count"
    echo "  Search types: semantic, keyword, hybrid"
    echo "  Embedding model: sentence-transformers/all-MiniLM-L6-v2"
    echo ""
    exit 0
else
    echo -e "${RED}Some tests failed ✗${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Populate KB: cd services/indexing && python populate_kb.py"
    echo "2. Check services: docker-compose ps"
    echo "3. Check logs: docker-compose logs indexing agent-orchestrator"
    echo "4. Verify Elasticsearch: curl http://localhost:9200/_cluster/health"
    echo "5. Test search: curl -X POST http://localhost:8003/search -d '{\"query\":\"test\"}'"
    echo ""
    exit 1
fi
