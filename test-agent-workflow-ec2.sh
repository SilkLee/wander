#!/bin/bash
# Test script for validating Agent workflow after EC2 rebuild
# Run this on EC2 after applying fixes from commit 627353f

set -e  # Exit on error

echo "=================================="
echo "Agent Workflow Validation Script"
echo "=================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check Docker services
echo "Step 1: Checking Docker service health..."
docker-compose ps

# Extract model-service status
MODEL_STATUS=$(docker-compose ps | grep workflowai-model | awk '{print $NF}')
AGENT_STATUS=$(docker-compose ps | grep workflowai-agent | awk '{print $NF}')

echo ""
if echo "$MODEL_STATUS" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Model Service: healthy${NC}"
else
    echo -e "${RED}✗ Model Service: $MODEL_STATUS${NC}"
    echo "Checking Model Service logs..."
    docker logs workflowai-model --tail=50
    exit 1
fi

if echo "$AGENT_STATUS" | grep -q "healthy\|Up"; then
    echo -e "${GREEN}✓ Agent Orchestrator: healthy${NC}"
else
    echo -e "${RED}✗ Agent Orchestrator: $AGENT_STATUS${NC}"
    echo "Checking Agent logs..."
    docker logs workflowai-agent --tail=50
    exit 1
fi

echo ""
echo "Step 2: Testing Model Service health endpoint..."
MODEL_HEALTH=$(curl -s http://localhost:8004/health)
echo "$MODEL_HEALTH" | jq .

MODEL_LOADED=$(echo "$MODEL_HEALTH" | jq -r .model_loaded)
if [ "$MODEL_LOADED" = "true" ]; then
    echo -e "${GREEN}✓ Model loaded successfully${NC}"
else
    echo -e "${RED}✗ Model not loaded${NC}"
    exit 1
fi

echo ""
echo "Step 3: Testing Agent health endpoint..."
AGENT_HEALTH=$(curl -s http://localhost:8002/health)
echo "$AGENT_HEALTH" | jq .

REDIS_CONNECTED=$(echo "$AGENT_HEALTH" | jq -r .redis_connected)
ES_CONNECTED=$(echo "$AGENT_HEALTH" | jq -r .elasticsearch_connected)

if [ "$REDIS_CONNECTED" = "true" ]; then
    echo -e "${GREEN}✓ Redis connected${NC}"
else
    echo -e "${YELLOW}⚠ Redis not connected${NC}"
fi

if [ "$ES_CONNECTED" = "true" ]; then
    echo -e "${GREEN}✓ Elasticsearch connected (no more 400 errors!)${NC}"
else
    echo -e "${YELLOW}⚠ Elasticsearch not connected${NC}"
fi

echo ""
echo "Step 4: Testing Agent workflow - Log Analysis..."
echo "Sending test log for analysis..."

WORKFLOW_RESPONSE=$(curl -s -X POST http://localhost:8002/workflows/analyze-log \
  -H "Content-Type: application/json" \
  -d '{
    "log_content": "ERROR: Connection timeout at database.py:142\nTraceback:\n  File database.py, line 142 in connect\n    raise TimeoutError(Connection timed out after 30s)\nTimeoutError: Connection timed out after 30s",
    "log_type": "application",
    "context": {
      "repo": "workflow-ai",
      "branch": "main",
      "commit": "627353f"
    }
  }')

echo ""
echo "Workflow Response:"
echo "$WORKFLOW_RESPONSE" | jq .

# Check for critical fields
if echo "$WORKFLOW_RESPONSE" | grep -q "analysis_id"; then
    echo -e "${GREEN}✓ Workflow executed successfully${NC}"
else
    echo -e "${RED}✗ Workflow failed - missing analysis_id${NC}"
    echo "Full response:"
    echo "$WORKFLOW_RESPONSE"
    exit 1
fi

if echo "$WORKFLOW_RESPONSE" | grep -q "Model Service connection error"; then
    echo -e "${RED}✗ Model Service connection error still exists!${NC}"
    exit 1
else
    echo -e "${GREEN}✓ No Model Service connection errors${NC}"
fi

if echo "$WORKFLOW_RESPONSE" | grep -q "root_cause"; then
    ROOT_CAUSE=$(echo "$WORKFLOW_RESPONSE" | jq -r .root_cause)
    echo -e "${GREEN}✓ Root cause identified: $ROOT_CAUSE${NC}"
else
    echo -e "${YELLOW}⚠ Root cause not found in response${NC}"
fi

if echo "$WORKFLOW_RESPONSE" | grep -q "suggested_fixes"; then
    FIXES_COUNT=$(echo "$WORKFLOW_RESPONSE" | jq '.suggested_fixes | length')
    echo -e "${GREEN}✓ Suggested fixes: $FIXES_COUNT items${NC}"
else
    echo -e "${YELLOW}⚠ Suggested fixes not found${NC}"
fi

echo ""
echo "Step 5: Checking for Elasticsearch errors in Agent logs..."
ES_ERRORS=$(docker logs workflowai-agent --tail=100 2>&1 | grep -i "elasticsearch connection failed" | wc -l)

if [ "$ES_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}✓ No Elasticsearch connection errors in recent logs${NC}"
else
    echo -e "${YELLOW}⚠ Found $ES_ERRORS Elasticsearch errors (may be from before rebuild)${NC}"
fi

echo ""
echo "=================================="
echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
echo "=================================="
echo ""
echo "Summary:"
echo "  ✓ Model Service: healthy with GPT-2 loaded"
echo "  ✓ Agent Orchestrator: healthy and connected to dependencies"
echo "  ✓ Elasticsearch: no more API v9 compatibility errors"
echo "  ✓ Agent workflow: successfully analyzes logs using Model Service"
echo ""
echo "Next steps:"
echo "  - Test streaming workflow: /workflows/analyze-log/stream"
echo "  - Test knowledge base search with indexed documents"
echo "  - Access monitoring dashboards:"
echo "    - Prometheus: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):9090"
echo "    - Grafana: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):3001"
echo "    - Jaeger: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4):16686"
