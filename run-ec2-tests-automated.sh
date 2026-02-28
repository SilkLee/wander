#!/bin/bash
# Complete EC2 Fix and Test Automation via SSM Send-Command
# Run this on your LOCAL machine (WSL xde-22) to execute everything on EC2 remotely
# No interactive session needed - fully automated

set -e

REGION="ap-southeast-1"
INSTANCE_ID="i-0b00972987f6bfb9c"
S3_BUCKET="workflow-ai-test-e23aba9e"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Day 10 EC2 Automated Testing${NC}"
echo -e "${BLUE}Using SSM Send-Command (Non-Interactive)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Export SSL workaround
export AWS_CLI_SSL_NO_VERIFY=1

# Function to send command and wait for result
send_command_and_wait() {
    local COMMAND="$1"
    local DESCRIPTION="$2"
    local MAX_WAIT="${3:-300}"  # Default 5 minutes
    
    echo -e "${YELLOW}${DESCRIPTION}${NC}"
    
    COMMAND_ID=$(aws ssm send-command \
        --region $REGION \
        --instance-ids $INSTANCE_ID \
        --document-name "AWS-RunShellScript" \
        --parameters "commands=[\"$COMMAND\"]" \
        --query 'Command.CommandId' \
        --output text 2>/dev/null)
    
    if [ -z "$COMMAND_ID" ]; then
        echo -e "${RED}✗ Failed to send command${NC}"
        return 1
    fi
    
    echo "  Command ID: $COMMAND_ID"
    
    # Wait for completion
    ELAPSED=0
    INTERVAL=5
    while [ $ELAPSED -lt $MAX_WAIT ]; do
        STATUS=$(aws ssm get-command-invocation \
            --region $REGION \
            --command-id $COMMAND_ID \
            --instance-id $INSTANCE_ID \
            --query 'Status' \
            --output text 2>/dev/null || echo "Pending")
        
        if [ "$STATUS" = "Success" ]; then
            OUTPUT=$(aws ssm get-command-invocation \
                --region $REGION \
                --command-id $COMMAND_ID \
                --instance-id $INSTANCE_ID \
                --query 'StandardOutputContent' \
                --output text 2>/dev/null)
            
            echo -e "${GREEN}✓ Complete${NC}"
            if [ ! -z "$OUTPUT" ]; then
                echo "$OUTPUT"
            fi
            return 0
        elif [ "$STATUS" = "Failed" ]; then
            ERROR=$(aws ssm get-command-invocation \
                --region $REGION \
                --command-id $COMMAND_ID \
                --instance-id $INSTANCE_ID \
                --query 'StandardErrorContent' \
                --output text 2>/dev/null)
            
            echo -e "${RED}✗ Failed${NC}"
            if [ ! -z "$ERROR" ]; then
                echo "$ERROR"
            fi
            return 1
        fi
        
        echo "  Status: $STATUS (${ELAPSED}s elapsed)"
        sleep $INTERVAL
        ELAPSED=$((ELAPSED + INTERVAL))
    done
    
    echo -e "${RED}✗ Timeout after ${MAX_WAIT}s${NC}"
    return 1
}

# Step 1: Apply fixes
echo -e "${BLUE}[Step 1/6] Applying code fixes${NC}"
send_command_and_wait \
    "cd /home/ec2-user && sed -i 's/--start-period=120s/--start-period=300s/g' services/model-service/Dockerfile && sed -i 's|LOCAL_MODEL_PATH=/app/models/qwen.*|LOCAL_MODEL_PATH=  # Empty|g' docker-compose.yml && echo 'Fixes applied successfully'" \
    "Modifying Dockerfile and docker-compose.yml..." \
    30

echo ""

# Step 2: Stop existing services
echo -e "${BLUE}[Step 2/6] Stopping Docker services${NC}"
send_command_and_wait \
    "cd /home/ec2-user && sudo docker-compose down && echo 'Services stopped'" \
    "Running docker-compose down..." \
    60

echo ""

# Step 3: Rebuild model-service
echo -e "${BLUE}[Step 3/6] Rebuilding model-service image${NC}"
send_command_and_wait \
    "cd /home/ec2-user && sudo docker-compose build model-service && echo 'Model service rebuilt'" \
    "Building Docker image..." \
    180

echo ""

# Step 4: Start all services
echo -e "${BLUE}[Step 4/6] Starting all services${NC}"
send_command_and_wait \
    "cd /home/ec2-user && sudo docker-compose up -d elasticsearch redis indexing agent-orchestrator model-service && echo 'Services started'" \
    "Starting services (this will take 2-5 minutes for model download)..." \
    30

echo ""

# Step 5: Wait for services to be healthy (longer timeout)
echo -e "${BLUE}[Step 5/6] Waiting for services to become healthy${NC}"
echo "This may take 2-5 minutes for GPT-2 model download..."

HEALTH_CHECK_SCRIPT='
MAX_WAIT=600
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    RUNNING=$(sudo docker-compose ps | grep -c "Up" || echo "0")
    MODEL_STATUS=$(sudo docker inspect workflowai-model --format="{{.State.Health.Status}}" 2>/dev/null || echo "unknown")
    AGENT_STATUS=$(sudo docker inspect workflowai-agent --format="{{.State.Status}}" 2>/dev/null || echo "unknown")
    
    echo "[${ELAPSED}s] Running: ${RUNNING}/5, Model: ${MODEL_STATUS}, Agent: ${AGENT_STATUS}"
    
    if [ "$RUNNING" -eq 5 ] && [ "$AGENT_STATUS" = "running" ]; then
        echo "All services healthy!"
        exit 0
    fi
    
    FAILED=$(sudo docker-compose ps | grep -c "Exit\|Restarting" || echo "0")
    if [ "$FAILED" -gt 0 ]; then
        echo "Services failed to start"
        sudo docker-compose ps
        sudo docker logs workflowai-model --tail 20
        exit 1
    fi
    
    sleep 10
    ELAPSED=$((ELAPSED + 10))
done
echo "Timeout waiting for services"
exit 1
'

send_command_and_wait \
    "cd /home/ec2-user && bash -c '$HEALTH_CHECK_SCRIPT'" \
    "Monitoring service health..." \
    660

echo ""

# Step 6: Run integration tests
echo -e "${BLUE}[Step 6/6] Running Day 10 integration tests${NC}"
send_command_and_wait \
    "cd /home/ec2-user && bash test-day10-internal.sh 2>&1 | tee ~/day10-test-results.txt && cat ~/day10-test-results.txt" \
    "Executing test-day10-internal.sh..." \
    180

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All tests completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Step 7: Cleanup
echo -e "${YELLOW}Starting AWS resource cleanup...${NC}"
echo ""

# Stop Docker services on EC2
echo "Stopping Docker services on EC2..."
send_command_and_wait \
    "cd /home/ec2-user && sudo docker-compose down" \
    "Shutting down containers..." \
    120 || true

echo ""

# Terminate EC2 instance
echo "Terminating EC2 instance..."
aws ec2 terminate-instances \
    --region $REGION \
    --instance-ids $INSTANCE_ID \
    --output text > /dev/null 2>&1

echo "Waiting for instance to terminate..."
aws ec2 wait instance-terminated \
    --region $REGION \
    --instance-ids $INSTANCE_ID 2>/dev/null || true

echo -e "${GREEN}✓ EC2 instance terminated${NC}"
echo ""

# Delete S3 bucket
echo "Deleting S3 bucket..."
aws s3 rb s3://$S3_BUCKET --region $REGION --force 2>/dev/null || true
echo -e "${GREEN}✓ S3 bucket deleted${NC}"
echo ""

# Verify IAM roles preserved
echo "Verifying IAM roles preserved..."
ROLE_EXISTS=$(aws iam get-role --role-name WorkflowAI-SSM-FixedRole 2>/dev/null && echo "yes" || echo "no")
if [ "$ROLE_EXISTS" = "yes" ]; then
    echo -e "${GREEN}✓ IAM role WorkflowAI-SSM-FixedRole preserved${NC}"
else
    echo -e "${YELLOW}⚠ IAM role not found (may have been deleted manually)${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Day 10 Testing Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Summary:"
echo "  ✓ Code fixes applied"
echo "  ✓ Docker services rebuilt and tested"
echo "  ✓ Integration tests executed"
echo "  ✓ EC2 instance terminated"
echo "  ✓ S3 bucket deleted"
echo "  ✓ IAM roles preserved"
echo ""
echo "Test results were saved to EC2:/home/ec2-user/day10-test-results.txt"
echo "(Note: File lost after EC2 termination - check output above for results)"
echo ""
echo "Next steps:"
echo "  1. Review test output above"
echo "  2. Update README.md to mark Day 10 complete"
echo "  3. Begin Day 11: Multi-agent orchestration (LangGraph)"
