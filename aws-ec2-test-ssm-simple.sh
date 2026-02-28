#!/bin/bash

# AWS EC2 Automated Testing for Day 10 RAG Integration (SSM Version - Simple)
# Uses pre-created IAM role (no IAM permissions needed for test execution)
# Prerequisites: Root user must create WorkflowAI-SSM-FixedRole first (see below)

set -e

REGION="ap-southeast-1"
INSTANCE_TYPE="t3.medium"
AMI_ID="ami-0ac0e4288aa341886"  # Amazon Linux 2023 in ap-southeast-1
INSTANCE_NAME="workflow-ai-day10-test"
INSTANCE_PROFILE_NAME="WorkflowAI-SSM-InstanceProfile"  # Fixed, pre-created
S3_BUCKET_NAME="workflow-ai-test-$(date +%s | md5sum | head -c 8)"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Day 10 RAG Test - EC2 SSM (Simple)${NC}"
echo -e "${BLUE}(No SSH or IAM permissions required)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Verify AWS credentials
echo "Verifying AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}ERROR: AWS credentials not configured${NC}"
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
    
    # Delete temporary archive
    rm -f /tmp/workflow-ai.tar.gz
    
    exit $EXIT_CODE
}

trap cleanup EXIT INT TERM

# Check if instance profile exists
echo "[1/6] Checking IAM instance profile..."
if ! aws iam get-instance-profile --instance-profile-name $INSTANCE_PROFILE_NAME &>/dev/null; then
    echo -e "${RED}ERROR: Instance profile '${INSTANCE_PROFILE_NAME}' does not exist${NC}"
    echo ""
    echo -e "${YELLOW}Please ask root user to create it first:${NC}"
    echo ""
    echo "# 1. Create IAM role with SSM permissions"
    echo "cat > /tmp/trust-policy.json << 'EOF'"
    echo '{'
    echo '  "Version": "2012-10-17",'
    echo '  "Statement": [{'
    echo '    "Effect": "Allow",'
    echo '    "Principal": {"Service": "ec2.amazonaws.com"},'
    echo '    "Action": "sts:AssumeRole"'
    echo '  }]'
    echo '}'
    echo 'EOF'
    echo ""
    echo "aws iam create-role \\"
    echo "    --role-name WorkflowAI-SSM-FixedRole \\"
    echo "    --assume-role-policy-document file:///tmp/trust-policy.json"
    echo ""
    echo "aws iam attach-role-policy \\"
    echo "    --role-name WorkflowAI-SSM-FixedRole \\"
    echo "    --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
    echo ""
    echo "aws iam attach-role-policy \\"
    echo "    --role-name WorkflowAI-SSM-FixedRole \\"
    echo "    --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess"
    echo ""
    echo "# 2. Create instance profile"
    echo "aws iam create-instance-profile \\"
    echo "    --instance-profile-name WorkflowAI-SSM-InstanceProfile"
    echo ""
    echo "aws iam add-role-to-instance-profile \\"
    echo "    --instance-profile-name WorkflowAI-SSM-InstanceProfile \\"
    echo "    --role-name WorkflowAI-SSM-FixedRole"
    echo ""
    exit 1
fi
echo -e "${GREEN}✓ Instance profile exists${NC}"
echo ""

# Create S3 bucket for code transfer
echo "[2/6] Creating temporary S3 bucket..."
aws s3 mb s3://${S3_BUCKET_NAME} --region $REGION
echo -e "${GREEN}✓ S3 bucket created: ${S3_BUCKET_NAME}${NC}"
echo ""

# Package and upload code to S3
echo "[3/6] Uploading code to S3..."
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

# UserData script
USER_DATA=$(cat <<EOF
#!/bin/bash
set -e
yum install -y git
curl -SL https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
usermod -aG docker ec2-user
systemctl start docker
systemctl enable docker
mkdir -p /home/ec2-user/workflow-ai
aws s3 cp s3://${S3_BUCKET_NAME}/workflow-ai.tar.gz /home/ec2-user/workflow-ai.tar.gz --region ${REGION}
cd /home/ec2-user
tar xzf workflow-ai.tar.gz
chown -R ec2-user:ec2-user /home/ec2-user/workflow-ai
rm -f /home/ec2-user/workflow-ai.tar.gz
touch /tmp/userdata-complete
EOF
)

# Launch EC2 instance
echo "[4/6] Launching EC2 instance with SSM..."
echo -e "${YELLOW}Instance type: ${INSTANCE_TYPE} (~\$0.05/hour)${NC}"
echo ""

INSTANCE_ID=$(aws ec2 run-instances \
    --region $REGION \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --iam-instance-profile Name=$INSTANCE_PROFILE_NAME \
    --user-data "$USER_DATA" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$INSTANCE_NAME}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

echo -e "${GREEN}✓ Instance launched: ${INSTANCE_ID}${NC}"
echo ""

# Wait for instance and SSM
echo "[5/6] Waiting for instance and SSM agent (2-3 minutes)..."
aws ec2 wait instance-running --region $REGION --instance-ids $INSTANCE_ID
echo -e "${GREEN}✓ Instance running${NC}"

# Wait for SSM agent
MAX_ATTEMPTS=40
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
    echo "  Waiting for SSM agent... $ATTEMPT/$MAX_ATTEMPTS (Status: $SSM_STATUS)"
    sleep 10
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}✗ SSM agent timeout${NC}"
    exit 1
fi

# Wait for UserData
echo "Waiting for Docker installation..."
ATTEMPT=0
while [ $ATTEMPT -lt 30 ]; do
    COMMAND_ID=$(aws ssm send-command \
        --region $REGION \
        --instance-ids $INSTANCE_ID \
        --document-name "AWS-RunShellScript" \
        --parameters 'commands=["test -f /tmp/userdata-complete && echo COMPLETE || echo WAITING"]' \
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
        
        if echo "$RESULT" | grep -q "COMPLETE"; then
            echo -e "${GREEN}✓ UserData complete${NC}"
            break
        fi
    fi
    
    ATTEMPT=$((ATTEMPT + 1))
    echo "  Attempt $ATTEMPT/30..."
    sleep 10
done

echo ""

# Run tests
echo "[6/6] Running Day 10 tests via SSM..."
echo ""

COMMAND_ID=$(aws ssm send-command \
    --region $REGION \
    --instance-ids $INSTANCE_ID \
    --document-name "AWS-RunShellScript" \
    --parameters 'commands=["cd /home/ec2-user/workflow-ai && bash test-day10-internal.sh"]' \
    --timeout-seconds 600 \
    --query 'Command.CommandId' \
    --output text)

echo "Command ID: $COMMAND_ID"
echo "Waiting for tests (5-8 minutes)..."

# Poll for completion
while true; do
    STATUS=$(aws ssm get-command-invocation \
        --region $REGION \
        --command-id $COMMAND_ID \
        --instance-id $INSTANCE_ID \
        --query 'Status' \
        --output text 2>/dev/null || echo "Pending")
    
    if [ "$STATUS" == "Success" ]; then
        echo -e "${GREEN}✓ Tests passed${NC}"
        break
    elif [ "$STATUS" == "Failed" ] || [ "$STATUS" == "TimedOut" ]; then
        echo -e "${RED}✗ Tests failed: $STATUS${NC}"
        TEST_FAILED=1
        break
    fi
    
    echo "  Status: $STATUS..."
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
    echo "Errors:"
    aws ssm get-command-invocation \
        --region $REGION \
        --command-id $COMMAND_ID \
        --instance-id $INSTANCE_ID \
        --query 'StandardErrorContent' \
        --output text
fi

echo ""
echo -e "${BLUE}========================================${NC}"
if [ -z "$TEST_FAILED" ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}✓ Day 10 RAG verified${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
fi
echo -e "${BLUE}========================================${NC}"
echo ""

exit ${TEST_FAILED:-0}
