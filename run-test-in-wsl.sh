#!/bin/bash
# This script runs the Day 5 test inside WSL2

echo "=================================================="
echo "WorkflowAI Day 5 - Running Test in WSL2"
echo "=================================================="
echo ""

# Create a script to run inside WSL
cat > /tmp/wsl-test-runner.sh << 'EOFINNER'
#!/bin/bash
set -e

echo "[1] Checking Docker..."
docker --version
docker compose version
echo ""

echo "[2] Navigating to project..."
cd /mnt/c/develop/workflow-ai
pwd
echo ""

echo "[3] Starting Docker services..."
docker compose up -d redis ingestion agent-orchestrator
echo ""

echo "[4] Waiting 20 seconds for services to start..."
sleep 20
echo ""

echo "[5] Checking running containers..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "[6] Running E2E Test..."
bash test-ingestion-e2e.sh
echo ""

echo "[7] Showing recent logs..."
echo "--- Ingestion Service Logs (last 20 lines) ---"
docker logs workflowai-ingestion --tail 20
echo ""
echo "--- Agent Orchestrator Logs (last 20 lines) ---"
docker logs workflowai-agent --tail 20
echo ""

echo "=================================================="
echo "Test Complete!"
echo "=================================================="
EOFINNER

# Copy script to Windows temp and run in WSL
cp /tmp/wsl-test-runner.sh /c/Users/uif16069/
wsl bash /mnt/c/Users/uif16069/wsl-test-runner.sh
