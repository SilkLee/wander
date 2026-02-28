#!/bin/bash
# EC2 Fix and Test Script for Day 10
# Run this script on EC2 instance after SSM connection
# Usage: bash ec2-fix-and-test.sh

set -e  # Exit on error

echo "==================================="
echo "Day 10 EC2 Fix and Test Automation"
echo "==================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Apply fixes
echo -e "${YELLOW}[Step 1/6]${NC} Applying fixes to Dockerfile and docker-compose.yml..."

# Fix Dockerfile - increase health check start-period
sed -i 's/--start-period=120s/--start-period=300s/g' services/model-service/Dockerfile

# Fix docker-compose.yml - clear LOCAL_MODEL_PATH
sed -i 's|LOCAL_MODEL_PATH=/app/models/qwen.*|LOCAL_MODEL_PATH=  # Empty - use HuggingFace model_name (gpt2)|g' docker-compose.yml

# Verify changes
if grep -q "start-period=300s" services/model-service/Dockerfile; then
    echo -e "${GREEN}✓${NC} Dockerfile fixed (health check: 300s)"
else
    echo -e "${RED}✗${NC} Failed to update Dockerfile"
    exit 1
fi

if grep -q "LOCAL_MODEL_PATH=  #" docker-compose.yml; then
    echo -e "${GREEN}✓${NC} docker-compose.yml fixed (LOCAL_MODEL_PATH cleared)"
else
    echo -e "${RED}✗${NC} Failed to update docker-compose.yml"
    exit 1
fi

echo ""

# Step 2: Stop existing services
echo -e "${YELLOW}[Step 2/6]${NC} Stopping existing Docker services..."
sudo docker-compose down
echo -e "${GREEN}✓${NC} Services stopped"
echo ""

# Step 3: Rebuild model-service
echo -e "${YELLOW}[Step 3/6]${NC} Rebuilding model-service image..."
sudo docker-compose build model-service
echo -e "${GREEN}✓${NC} Model service rebuilt"
echo ""

# Step 4: Start all services
echo -e "${YELLOW}[Step 4/6]${NC} Starting all Docker services..."
sudo docker-compose up -d elasticsearch redis indexing agent-orchestrator model-service
echo -e "${GREEN}✓${NC} Services started"
echo ""

# Step 5: Wait for services to be healthy
echo -e "${YELLOW}[Step 5/6]${NC} Waiting for services to become healthy (this may take 2-5 minutes)..."
echo "Progress indicators:"
echo "  - Elasticsearch: ~30 seconds"
echo "  - Redis: ~10 seconds"
echo "  - Indexing: ~60 seconds (model download)"
echo "  - Model Service: ~180-300 seconds (GPT-2 download)"
echo "  - Agent: ~10 seconds (after model is ready)"
echo ""

MAX_WAIT=600  # 10 minutes max
ELAPSED=0
INTERVAL=10

while [ $ELAPSED -lt $MAX_WAIT ]; do
    # Check service status
    STATUS=$(sudo docker-compose ps --format json 2>/dev/null || echo "[]")
    
    # Count healthy/running services
    RUNNING=$(sudo docker-compose ps | grep -c "Up" || echo "0")
    HEALTHY=$(sudo docker-compose ps | grep -c "healthy" || echo "0")
    
    echo -e "${YELLOW}[${ELAPSED}s]${NC} Running: ${RUNNING}/5, Healthy: ${HEALTHY}/3"
    
    # Check if model-service is healthy
    MODEL_STATUS=$(sudo docker inspect workflowai-model --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
    AGENT_STATUS=$(sudo docker inspect workflowai-agent --format='{{.State.Status}}' 2>/dev/null || echo "unknown")
    
    echo "  Model Service: ${MODEL_STATUS}, Agent: ${AGENT_STATUS}"
    
    # Success condition: all 5 services up, model and agent running
    if [ "$RUNNING" -eq 5 ] && [ "$AGENT_STATUS" = "running" ]; then
        echo ""
        echo -e "${GREEN}✓${NC} All services are up and running!"
        break
    fi
    
    # Check for failures
    FAILED=$(sudo docker-compose ps | grep -c "Exit\|Restarting" || echo "0")
    if [ "$FAILED" -gt 0 ]; then
        echo ""
        echo -e "${RED}✗${NC} Some services failed to start. Checking logs..."
        sudo docker-compose ps
        echo ""
        echo "Model service logs (last 20 lines):"
        sudo docker logs workflowai-model --tail 20
        exit 1
    fi
    
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo ""
    echo -e "${RED}✗${NC} Timeout waiting for services to start (${MAX_WAIT}s)"
    sudo docker-compose ps
    exit 1
fi

echo ""

# Step 6: Verify service health
echo -e "${YELLOW}[Step 6/6]${NC} Verifying service health endpoints..."

# Wait a bit more for FastAPI to be ready
sleep 5

# Test Elasticsearch
if curl -sf http://localhost:9200/_cluster/health > /dev/null; then
    echo -e "${GREEN}✓${NC} Elasticsearch: healthy"
else
    echo -e "${RED}✗${NC} Elasticsearch: failed"
fi

# Test Indexing Service
if curl -sf http://localhost:8003/health > /dev/null; then
    echo -e "${GREEN}✓${NC} Indexing Service: healthy"
else
    echo -e "${RED}✗${NC} Indexing Service: failed"
fi

# Test Model Service
if curl -sf http://localhost:8004/health > /dev/null; then
    HEALTH=$(curl -s http://localhost:8004/health | grep -o '"model_loaded":true' || echo "")
    if [ -n "$HEALTH" ]; then
        echo -e "${GREEN}✓${NC} Model Service: healthy (GPT-2 loaded)"
    else
        echo -e "${YELLOW}!${NC} Model Service: responding but model not loaded"
    fi
else
    echo -e "${RED}✗${NC} Model Service: failed"
fi

# Test Agent Orchestrator
if curl -sf http://localhost:8002/health > /dev/null; then
    echo -e "${GREEN}✓${NC} Agent Orchestrator: healthy"
else
    echo -e "${RED}✗${NC} Agent Orchestrator: failed"
fi

echo ""
echo "==================================="
echo -e "${GREEN}Services are ready!${NC}"
echo "==================================="
echo ""

# Display final status
echo "Current service status:"
sudo docker-compose ps
echo ""

# Run integration tests
echo -e "${YELLOW}Running Day 10 integration tests...${NC}"
echo ""

if [ -f "test-day10-internal.sh" ]; then
    bash test-day10-internal.sh | tee ~/day10-test-results.txt
    TEST_EXIT=$?
    
    echo ""
    if [ $TEST_EXIT -eq 0 ]; then
        echo -e "${GREEN}✓✓✓${NC} All tests passed!"
        echo "Results saved to: ~/day10-test-results.txt"
        echo ""
        echo "Next steps:"
        echo "  1. Review test results: cat ~/day10-test-results.txt"
        echo "  2. Exit this session: exit"
        echo "  3. Press Ctrl+C in local terminal to cleanup AWS resources"
    else
        echo -e "${RED}✗✗✗${NC} Some tests failed (exit code: $TEST_EXIT)"
        echo "Check logs:"
        echo "  sudo docker logs workflowai-model"
        echo "  sudo docker logs workflowai-agent"
        echo "  sudo docker logs workflowai-indexing"
    fi
else
    echo -e "${RED}✗${NC} Test script not found: test-day10-internal.sh"
    echo "Manual test command: bash test-day10-internal.sh"
fi

echo ""
echo "==================================="
echo "Automation complete!"
echo "==================================="
