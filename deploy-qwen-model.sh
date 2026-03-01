#!/bin/bash
# Deploy Qwen2.5-1.5B-Instruct model upgrade to EC2
# Run this script on EC2 instance after SSM connection

set -e

echo "=== Qwen Model Deployment Script ==="
echo "Target: Qwen2.5-1.5B-Instruct (1.5B parameters, instruction-tuned)"
echo ""

# Navigate to project directory
cd /home/ec2-user/workflow-ai || {
    echo "ERROR: Project directory not found"
    exit 1
}

# Pull latest code
echo "Step 1: Pulling latest code from GitHub..."
git pull origin main

# Show what changed
echo ""
echo "Changes pulled:"
git log --oneline -1
echo ""

# Rebuild model service
echo "Step 2: Rebuilding model-service with Qwen configuration..."
docker-compose build --no-cache model-service

# Stop old model service
echo ""
echo "Step 3: Stopping old model service..."
docker-compose stop model-service

# Start new model service
echo ""
echo "Step 4: Starting new model service..."
docker-compose up -d model-service

# Monitor startup
echo ""
echo "Step 5: Monitoring model service startup (this may take 2-3 minutes)..."
echo "The Qwen model (1.5GB) will be downloaded on first inference request."
echo ""
sleep 5

# Wait for health check
MAX_WAIT=60
COUNTER=0
while [ $COUNTER -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8004/health > /dev/null 2>&1; then
        echo "✓ Model service health check passed"
        break
    fi
    echo "Waiting for model service... ($COUNTER/$MAX_WAIT)"
    sleep 2
    COUNTER=$((COUNTER + 2))
done

if [ $COUNTER -ge $MAX_WAIT ]; then
    echo "WARNING: Model service did not become healthy within $MAX_WAIT seconds"
    echo "Check logs: docker logs workflowai-model --tail 50"
    exit 1
fi

# Restart agent service
echo ""
echo "Step 6: Restarting agent-orchestrator to connect to new model..."
docker-compose restart agent-orchestrator
sleep 15

# Verify agent health
echo ""
echo "Step 7: Verifying agent service health..."
if curl -s http://localhost:8002/health | grep -q '"status":"healthy"'; then
    echo "✓ Agent service health check passed"
else
    echo "WARNING: Agent service may not be healthy"
    echo "Check logs: docker logs workflowai-agent --tail 50"
fi

# Show service status
echo ""
echo "Step 8: Current service status:"
docker ps --filter "name=workflowai-model" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
docker ps --filter "name=workflowai-agent" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "1. Test Agent workflow with:"
echo "   ./test-agent-workflow-qwen.sh"
echo ""
echo "2. Monitor model download during first request:"
echo "   docker logs workflowai-model --follow"
echo ""
echo "Note: First Agent request will take 2-3 minutes (model download + inference)"
