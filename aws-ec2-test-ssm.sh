#!/bin/bash

# AWS EC2 Automated Testing for Day 10 RAG Integration (SSM Version)
# Uses AWS Systems Manager instead of SSH (bypasses port 22 firewall blocks)
# Creates temporary EC2 instance, runs tests, and cleans up

set -e

REGION="ap-southeast-1"
INSTANCE_TYPE="t3.large"
AMI_ID="ami-0ac0e4288aa341886"  # Amazon Linux 2023 in ap-southeast-1 (Docker + SSM Agent pre-installed)
INSTANCE_NAME="workflow-ai-day10-test"
ROLE_NAME="WorkflowAI-SSM-FixedRole"
INSTANCE_PROFILE_NAME="WorkflowAI-SSM-InstanceProfile"
S3_BUCKET_NAME="workflow-ai-test-$(date +%s | md5sum | head -c 8)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Day 10 RAG Test - EC2 SSM Automation${NC}"
echo -e "${BLUE}(No SSH required - uses HTTPS/443)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verify AWS credentials
echo "Verifying AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}ERROR: AWS credentials not configured${NC}"
    echo "Run: wsl -d xde-22 -e bash aws-setup.sh"
    exit 1
fi
echo -e "${GREEN}✓ AWS credentials verified${NC}"
echo ""

# Cleanup function
cleanup() {
    local EXIT_CODE=$?
    echo ""
    echo -e "${YELLOW}Cleaning up AWS resources...${NC}"
    
    # Terminate instance
    if [ ! -z "$INSTANCE_ID" ]; then
        echo "Terminating EC2 instance..."
        aws ec2 terminate-instances --region $REGION --instance-ids $INSTANCE_ID --output text > /dev/null 2>&1 || true
        echo "Waiting for instance to terminate..."
        aws ec2 wait instance-terminated --region $REGION --instance-ids $INSTANCE_ID 2>/dev/null || true
        echo -e "${GREEN}✓ Instance terminated${NC}"
    fi
    
    # Delete S3 bucket
    if [ ! -z "$S3_BUCKET_NAME" ]; then
        echo "Deleting S3 bucket..."
        aws s3 rb s3://${S3_BUCKET_NAME} --force --region $REGION 2>/dev/null || true
        echo -e "${GREEN}✓ S3 bucket deleted${NC}"
    fi
    
    # Note: NOT deleting IAM role and instance profile (will be reused)
    echo -e "${YELLOW}Note: IAM role and instance profile preserved for reuse${NC}"
    
    # Delete temporary files
    rm -f /tmp/workflow-ai.tar.gz
    rm -f /tmp/workflow-ai.tar.gz
    
    exit $EXIT_CODE
}

trap cleanup EXIT INT TERM

# Check if IAM role already exists
echo "[1/8] Checking IAM role for SSM access..."
if aws iam get-role --role-name $ROLE_NAME &>/dev/null; then
    echo -e "${YELLOW}IAM role ${ROLE_NAME} already exists, reusing...${NC}"
else
    echo "Creating new IAM role..."
    TRUST_POLICY=$(cat <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
)

    aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document "$TRUST_POLICY" \
        --output text > /dev/null

    # Attach SSM policy
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

    # Attach S3 read policy (for downloading code archive)
    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

    echo -e "${GREEN}✓ IAM role created: ${ROLE_NAME}${NC}"
fi
echo ""

# Check if instance profile already exists
echo "[2/8] Checking instance profile..."
if aws iam get-instance-profile --instance-profile-name $INSTANCE_PROFILE_NAME &>/dev/null; then
    echo -e "${YELLOW}Instance profile ${INSTANCE_PROFILE_NAME} already exists, reusing...${NC}"
else
    echo "Creating new instance profile..."
    aws iam create-instance-profile \
        --instance-profile-name $INSTANCE_PROFILE_NAME \
        --output text > /dev/null

    # Add role to instance profile
    aws iam add-role-to-instance-profile \
        --instance-profile-name $INSTANCE_PROFILE_NAME \
        --role-name $ROLE_NAME

    echo -e "${GREEN}✓ Instance profile created: ${INSTANCE_PROFILE_NAME}${NC}"
fi
echo ""

# Wait for instance profile to propagate
echo "Waiting for IAM propagation (10 seconds)..."
sleep 10

# Create S3 bucket for code transfer
echo "[3/8] Creating temporary S3 bucket..."
aws s3 mb s3://${S3_BUCKET_NAME} --region $REGION
echo -e "${GREEN}✓ S3 bucket created: ${S3_BUCKET_NAME}${NC}"
echo ""

# Package and upload code to S3
echo "[4/8] Uploading code to S3..."
cd /mnt/c/develop/workflow-ai
tar czf /tmp/workflow-ai.tar.gz \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='venv' \
    --exclude='aws' \
    --exclude='*.zip' \
    --exclude='*.msi' \
    .

aws s3 cp /tmp/workflow-ai.tar.gz s3://${S3_BUCKET_NAME}/workflow-ai.tar.gz --region $REGION
echo -e "${GREEN}✓ Code uploaded to S3${NC}"
echo ""

# UserData script to install Docker and download code from S3
USER_DATA=$(cat <<EOF
#!/bin/bash
set -e

# Install Docker
yum install -y docker git amazon-cloudwatch-agent

# Start Docker (creates docker group)
systemctl start docker
systemctl enable docker

# Install Docker Compose
curl -SL https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Add ec2-user to docker group
usermod -aG docker ec2-user

# Download code from S3
echo '[1/2] Downloading code from S3...' > /tmp/userdata-progress
aws s3 cp s3://${S3_BUCKET_NAME}/workflow-ai.tar.gz /home/ec2-user/workflow-ai.tar.gz --region ${REGION}
cd /home/ec2-user
tar xzf workflow-ai.tar.gz
chown -R ec2-user:ec2-user /home/ec2-user
rm -f /home/ec2-user/workflow-ai.tar.gz

# Signal ready for manual build
echo '[2/2] Code downloaded. Ready for manual Docker build via SSM Session Manager.' > /tmp/userdata-progress
echo 'READY_FOR_MANUAL_BUILD' > /tmp/userdata-complete
EOF
)

# Launch EC2 instance with SSM
echo "[5/8] Launching EC2 instance with SSM..."
echo -e "${YELLOW}Instance type: ${INSTANCE_TYPE} (~\$0.05/hour)${NC}"
echo -e "${YELLOW}Region: ${REGION}${NC}"
echo ""

INSTANCE_ID=$(aws ec2 run-instances \
    --region $REGION \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --iam-instance-profile Name=$INSTANCE_PROFILE_NAME \
    --user-data "$USER_DATA" \
    --block-device-mappings '[{"DeviceName":"/dev/xvda","Ebs":{"VolumeSize":30,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

echo -e "${GREEN}✓ Instance launched: ${INSTANCE_ID}${NC}"
echo ""

# Wait for instance to be running
echo "[6/8] Waiting for instance to start and register with SSM (1-2 minutes)..."
aws ec2 wait instance-running --region $REGION --instance-ids $INSTANCE_ID
echo -e "${GREEN}✓ Instance running${NC}"

# Wait for SSM agent to be online
MAX_ATTEMPTS=80  # 20 minutes total (80 × 15s)
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    SSM_STATUS=$(aws ssm describe-instance-information \
        --region $REGION \
        --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
        --query 'InstanceInformationList[0].PingStatus' \
        --output text 2>/dev/null || echo "Unknown")
    
    if [ "$SSM_STATUS" == "Online" ]; then
        echo -e "${GREEN}✓ SSM agent online${NC}"
        break
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    echo "  Waiting for SSM agent... Attempt $ATTEMPT/$MAX_ATTEMPTS (Status: $SSM_STATUS)"
    sleep 10
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}✗ SSM agent did not come online in time${NC}"
    exit 1
fi

# Wait for UserData to complete
echo "Waiting for UserData script to complete..."
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    COMMAND_ID=$(aws ssm send-command \
        --region $REGION \
        --instance-ids $INSTANCE_ID \
        --document-name "AWS-RunShellScript" \
        --parameters 'commands=["cat /tmp/userdata-complete 2>/dev/null || echo WAITING"]' \
        --query 'Command.CommandId' \
        --output text 2>/dev/null)
    
    if [ ! -z "$COMMAND_ID" ]; then
        sleep 5
        RESULT=$(aws ssm get-command-invocation \
            --region $REGION \
            --command-id $COMMAND_ID \
            --instance-id $INSTANCE_ID \
            --query 'StandardOutputContent' \
            --output text 2>/dev/null || echo "WAITING")
        
        
        if echo "$RESULT" | grep -q "COMPLETE\|READY_FOR_MANUAL_BUILD"; then
            if echo "$RESULT" | grep -q "READY_FOR_MANUAL_BUILD"; then
                echo -e "${GREEN}✓ EC2 instance ready for manual Docker build${NC}"
                echo ""
                echo -e "${BLUE}========================================${NC}"
                echo -e "${BLUE}Manual Build Instructions${NC}"
                echo -e "${BLUE}========================================${NC}"
                echo ""
                echo -e "${YELLOW}1. Connect to EC2 via SSM Session Manager:${NC}"
                echo -e "   ${GREEN}aws ssm start-session --region $REGION --target $INSTANCE_ID${NC}"
                echo ""
                echo -e "${YELLOW}2. Once connected, run these commands:${NC}"
                echo -e "   ${GREEN}cd /home/ec2-user${NC}"
                echo -e "   ${GREEN}docker-compose build indexing agent-orchestrator model-service${NC}"
                echo -e "   ${GREEN}docker-compose up -d${NC}"
                echo ""
                echo -e "${YELLOW}3. After services are up, run tests:${NC}"
                echo -e "   ${GREEN}bash test-day10-internal.sh${NC}"
                echo ""
                echo -e "${YELLOW}4. When done, exit the session:${NC}"
                echo -e "   ${GREEN}exit${NC}"
                echo ""
                echo -e "${BLUE}Instance will remain running. Press Ctrl+C when finished.${NC}"
                echo -e "${BLUE}Then run cleanup manually if needed.${NC}"
                echo ""
                
                # Keep script running, wait for user interrupt
                echo "Waiting for user to complete manual build (Press Ctrl+C to stop)..."
                while true; do
                    sleep 30
                done
            else
                echo -e "${GREEN}✓ UserData script completed${NC}"
            fi
            break
        fi
        
        # Show progress if available
        PROGRESS_CMD=$(aws ssm send-command \
            --region $REGION \
            --instance-ids $INSTANCE_ID \
            --document-name "AWS-RunShellScript" \
            --parameters 'commands=["cat /tmp/userdata-progress 2>/dev/null || echo Initializing..."]' \
            --query 'Command.CommandId' \
            --output text 2>/dev/null)
        
        if [ ! -z "$PROGRESS_CMD" ]; then
            sleep 2
            PROGRESS=$(aws ssm get-command-invocation \
                --region $REGION \
                --command-id $PROGRESS_CMD \
                --instance-id $INSTANCE_ID \
                --query 'StandardOutputContent' \
                --output text 2>/dev/null || echo "")
            
            if [ ! -z "$PROGRESS" ]; then
                echo -e "  ${YELLOW}Status: $PROGRESS${NC}"
            fi
        fi
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    echo "  Attempt $ATTEMPT/$MAX_ATTEMPTS..."
    sleep 10
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}✗ UserData script did not complete in time${NC}"
    exit 1
fi

echo ""

# Run tests via SSM
echo "[7/8] Running Day 10 integration tests via SSM..."
echo ""

COMMAND_ID=$(aws ssm send-command \
    --region $REGION \
    --instance-ids $INSTANCE_ID \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["cd /home/ec2-user && bash test-day10-internal.sh"]' \
    --timeout-seconds 600 \
    --query 'Command.CommandId' \
    --output text)

echo "Command ID: $COMMAND_ID"
echo "Waiting for test completion (may take 5-8 minutes)..."

# Poll for command completion
while true; do
    STATUS=$(aws ssm get-command-invocation \
        --region $REGION \
        --command-id $COMMAND_ID \
        --instance-id $INSTANCE_ID \
        --query 'Status' \
        --output text 2>/dev/null || echo "Pending")
    
    if [ "$STATUS" == "Success" ]; then
        echo -e "${GREEN}✓ Tests completed successfully${NC}"
        break
    elif [ "$STATUS" == "Failed" ] || [ "$STATUS" == "TimedOut" ] || [ "$STATUS" == "Cancelled" ]; then
        echo -e "${RED}✗ Tests failed with status: $STATUS${NC}"
        TEST_FAILED=1
        break
    fi
    
    echo "  Test status: $STATUS..."
    sleep 15
done

echo ""
echo "Test output:"
echo "----------------------------------------"
aws ssm get-command-invocation \
    --region $REGION \
    --command-id $COMMAND_ID \
    --instance-id $INSTANCE_ID \
    --query 'StandardOutputContent' \
    --output text
echo "----------------------------------------"
echo ""

if [ ! -z "$TEST_FAILED" ]; then
    echo "Test errors:"
    echo "----------------------------------------"
    aws ssm get-command-invocation \
        --region $REGION \
        --command-id $COMMAND_ID \
        --instance-id $INSTANCE_ID \
        --query 'StandardErrorContent' \
        --output text
    echo "----------------------------------------"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
if [ -z "$TEST_FAILED" ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}✓ Day 10 RAG implementation verified${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo -e "${YELLOW}Check test output above for details${NC}"
fi
echo -e "${BLUE}========================================${NC}"
echo ""

exit ${TEST_FAILED:-0}
