# AWS Systems Manager Session Manager - SSH to SSM Migration Guide

## Overview
This guide provides official AWS patterns for replacing SSH-based EC2 connectivity with AWS Systems Manager (SSM) Session Manager. SSM uses HTTPS/443 and does not require SSH keys or open inbound ports.

**Key Advantage**: Works through corporate firewalls blocking port 22.

---

## 1. SESSION MANAGER FUNDAMENTALS

### What is Session Manager?
- **Service**: AWS Systems Manager tool for secure remote access to EC2 instances
- **Protocol**: TLS 1.2 encrypted, uses HTTPS (443) for all communications
- **Authentication**: IAM-based (no SSH keys needed)
- **No inbound ports required**: Sessions initiated from AWS CloudAPI
- **Logging**: CloudTrail, S3, CloudWatch Logs, EventBridge integration

### Session Manager Benefits
```
✓ No open SSH ports (port 22 closed)
✓ No SSH key management
✓ Centralized IAM access control
✓ No bastion hosts needed
✓ Cross-platform (Windows, Linux, macOS)
✓ Session logging for compliance
✓ Works with instances without public IPs (via VPC Endpoints)
```

### Communication Flow
```
Local CLI/Console
    ↓ (HTTPS/TLS 1.2)
    ↓ AWS Systems Manager API
    ↓ (Signed SigV4 requests)
SSM Agent on EC2 Instance
    ↓ (outbound HTTPS to ssmmessages.* endpoints)
    ↓ Response via secure channel
Local Terminal
```

---

## 2. REQUIRED IAM SETUP

### 2.1 Create IAM Role for EC2 (with SSM permissions)

**Option A: Using AWS-Managed Policy (Recommended)**

```bash
# Create IAM role
aws iam create-role \
  --role-name EC2-SSM-Role \
  --assume-role-policy-document '{
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
  }'

# Attach AWS managed policy for SSM
aws iam attach-role-policy \
  --role-name EC2-SSM-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name EC2-SSM-InstanceProfile

# Attach role to instance profile
aws iam add-role-to-instance-profile \
  --instance-profile-name EC2-SSM-InstanceProfile \
  --role-name EC2-SSM-Role
```

**Option B: Custom Minimal IAM Policy**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel",
        "ec2messages:AcknowledgeMessage",
        "ec2messages:DeleteMessage",
        "ec2messages:FailMessage",
        "ec2messages:GetEndpoint",
        "ec2messages:GetMessages"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::ssm-command-output-*",
        "arn:aws:s3:::ssm-command-output-*/*"
      ]
    }
  ]
}
```

### 2.2 Attach IAM Role to EC2 Instance

**At Launch Time:**
```bash
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t2.micro \
  --iam-instance-profile "Name=EC2-SSM-InstanceProfile" \
  --security-group-ids sg-xxxxxxxx
```

**To Existing Instance:**
```bash
aws ec2 associate-iam-instance-profile \
  --iam-instance-profile "Name=EC2-SSM-InstanceProfile" \
  --instance-id i-1234567890abcdef0
```

---

## 3. EC2 INSTANCE SETUP REQUIREMENTS

### 3.1 SSM Agent Pre-installed AMIs

**Amazon Linux 2 / AL2023:**
- SSM Agent pre-installed ✓
- Just needs IAM role + permissions

**Ubuntu 20.04, 22.04, 24.04:**
- SSM Agent pre-installed ✓
- Just needs IAM role + permissions

**Windows Server 2016/2019/2022:**
- SSM Agent pre-installed ✓
- Just needs IAM role + permissions

**Red Hat Enterprise Linux (RHEL) 7/8/9:**
- SSM Agent pre-installed ✓

### 3.2 Verify SSM Agent Status

**From Systems Manager Console (via SSM):**
```bash
# List all managed instances
aws ssm describe-instance-information

# Get specific instance status
aws ssm describe-instance-information \
  --filters "Key=InstanceIds,Values=i-1234567890abcdef0"
```

**From EC2 Instance (via SSH/RDP before SSM works):**

Linux/Amazon Linux 2:
```bash
sudo systemctl status amazon-ssm-agent
sudo systemctl enable amazon-ssm-agent  # Ensure auto-start
sudo systemctl start amazon-ssm-agent   # Start if stopped
```

Ubuntu (Snap):
```bash
sudo systemctl status snap.amazon-ssm-agent.amazon-ssm-agent.service
sudo snap start amazon-ssm-agent
```

Windows Server (PowerShell):
```powershell
Get-Service AmazonSSMAgent
Start-Service AmazonSSMAgent  # If not running
```

### 3.3 Wait for SSM Agent Registration

**Polling Pattern (Wait for Instance to Become Managed):**

```bash
#!/bin/bash
INSTANCE_ID="i-1234567890abcdef0"
MAX_WAIT=300  # 5 minutes
ELAPSED=0
INTERVAL=5

while [ $ELAPSED -lt $MAX_WAIT ]; do
  STATUS=$(aws ssm describe-instance-information \
    --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
    --query 'InstanceInformationList[0].PingStatus' \
    --output text 2>/dev/null)
  
  if [ "$STATUS" = "Online" ]; then
    echo "✓ Instance $INSTANCE_ID is online in SSM"
    exit 0
  fi
  
  echo "Waiting for SSM Agent... (elapsed: ${ELAPSED}s)"
  sleep $INTERVAL
  ELAPSED=$((ELAPSED + INTERVAL))
done

echo "✗ Timeout: SSM Agent did not register within ${MAX_WAIT}s"
exit 1
```

---

## 4. AWS CLI COMMANDS FOR SESSION MANAGER

### 4.1 Prerequisites: Session Manager Plugin

**Install Session Manager Plugin** (required for CLI)

macOS:
```bash
brew install --cask session-manager-plugin
```

Linux (Ubuntu/Debian):
```bash
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb"
sudo dpkg -i session-manager-plugin.deb
```

Windows:
```powershell
# Via MSI installer
Invoke-WebRequest `
  -Uri "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/windows/SessionManagerPluginSetup.exe" `
  -OutFile "SessionManagerPluginSetup.exe"
.\SessionManagerPluginSetup.exe
```

Verify installation:
```bash
session-manager-plugin --version
```

### 4.2 Start Interactive Session

**Connect to Single Instance:**
```bash
aws ssm start-session \
  --target i-1234567890abcdef0 \
  --region us-east-1
```

**Connect to Instance by Tag:**
```bash
aws ssm start-session \
  --target "tag:Environment:Production" \
  --region us-east-1
```

### 4.3 Run Single Command (No Interactive Session)

**Execute Command Inline:**
```bash
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --targets "Key=InstanceIds,Values=i-1234567890abcdef0" \
  --parameters 'commands=["echo Hello World","ls -la"]' \
  --region us-east-1
```

Output:
```json
{
  "Command": {
    "CommandId": "92853adf-ba41-4cd6-9a88-142d1EXAMPLE",
    "DocumentName": "AWS-RunShellScript",
    "Status": "Pending",
    "InstanceIds": ["i-1234567890abcdef0"]
  }
}
```

### 4.4 Get Command Results

```bash
# Get command invocation details
aws ssm get-command-invocation \
  --command-id "92853adf-ba41-4cd6-9a88-142d1EXAMPLE" \
  --instance-id "i-1234567890abcdef0" \
  --region us-east-1
```

Response:
```json
{
  "CommandId": "92853adf-ba41-4cd6-9a88-142d1EXAMPLE",
  "InstanceId": "i-1234567890abcdef0",
  "Status": "Success",
  "StandardOutputContent": "Hello World\nfile1.txt\nfile2.log",
  "StandardErrorContent": "",
  "ExecutionStartDateTime": "2025-02-28T10:30:45.000Z",
  "ExecutionEndDateTime": "2025-02-28T10:30:50.000Z"
}
```

### 4.5 Send Command to Multiple Instances

**By Instance IDs (up to 50):**
```bash
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --instance-ids i-1111111111111111 i-2222222222222222 \
  --parameters 'commands=["systemctl status docker"]'
```

**By Tags (scale to 1000s):**
```bash
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --targets "Key=tag:Environment,Values=Production" "Key=tag:Role,Values=WebServer" \
  --parameters 'commands=["systemctl restart nginx"]' \
  --max-concurrency "50%"
```

### 4.6 Send Command with Output to S3

```bash
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --instance-ids i-1234567890abcdef0 \
  --parameters 'commands=["curl https://example.com","df -h"]' \
  --output-s3-bucket-name "my-ssm-output-bucket" \
  --output-s3-key-prefix "ec2-commands/" \
  --region us-east-1
```

### 4.7 Send Command with CloudWatch Logs

```bash
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --targets "Key=InstanceIds,Values=i-1234567890abcdef0" \
  --parameters 'commands=["tail -f /var/log/syslog"]' \
  --cloud-watch-output-config CloudWatchLogGroupName=/aws/ssm/commands,CloudWatchOutputEnabled=true
```

### 4.8 View Command Status Across Multiple Instances

```bash
# List all command invocations for a command
aws ssm list-command-invocations \
  --command-id "92853adf-ba41-4cd6-9a88-142d1EXAMPLE" \
  --region us-east-1 \
  --output table
```

---

## 5. FILE TRANSFER PATTERNS

### 5.1 Upload File via S3 (Replace SCP)

```bash
#!/bin/bash
# Upload local file to S3, then have EC2 download it

LOCAL_FILE="./deployment-package.tar.gz"
S3_BUCKET="my-temp-transfer-bucket"
S3_KEY="uploads/deployment-package.tar.gz"
INSTANCE_ID="i-1234567890abcdef0"
REMOTE_PATH="/tmp/deployment-package.tar.gz"

# 1. Upload to S3
aws s3 cp "$LOCAL_FILE" "s3://$S3_BUCKET/$S3_KEY"

# 2. Generate pre-signed URL (1-hour expiry)
PRESIGNED_URL=$(aws s3 presign "s3://$S3_BUCKET/$S3_KEY" \
  --expires-in 3600)

# 3. EC2 downloads via SSM send-command
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --instance-ids "$INSTANCE_ID" \
  --parameters "commands=[\"curl -o $REMOTE_PATH '$PRESIGNED_URL'\",\"tar -xzf $REMOTE_PATH -C /opt/app\"]"

echo "✓ File transferred and extracted on instance"
```

### 5.2 Download File from EC2 via S3

```bash
#!/bin/bash
# EC2 uploads file to S3, local system downloads it

INSTANCE_ID="i-1234567890abcdef0"
REMOTE_FILE="/var/log/application.log"
S3_BUCKET="my-temp-transfer-bucket"
S3_KEY="downloads/application.log"
LOCAL_DEST="./logs/"

# 1. EC2 uploads file to S3
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --instance-ids "$INSTANCE_ID" \
  --parameters "commands=[\"aws s3 cp $REMOTE_FILE s3://$S3_BUCKET/$S3_KEY\"]"

# 2. Wait for command to complete
sleep 5

# 3. Download from S3 locally
aws s3 cp "s3://$S3_BUCKET/$S3_KEY" "$LOCAL_DEST/"

echo "✓ File downloaded: $LOCAL_DEST/application.log"
```

### 5.3 Execute Script on Remote Instance

```bash
#!/bin/bash
# Execute local script on remote instance

LOCAL_SCRIPT="./configure-app.sh"
INSTANCE_ID="i-1234567890abcdef0"
S3_BUCKET="my-scripts-bucket"
SCRIPT_KEY="scripts/configure-app.sh"

# 1. Upload script to S3
aws s3 cp "$LOCAL_SCRIPT" "s3://$S3_BUCKET/$SCRIPT_KEY"

# 2. Get pre-signed URL
PRESIGNED_URL=$(aws s3 presign "s3://$S3_BUCKET/$SCRIPT_KEY" \
  --expires-in 1800)

# 3. Execute on EC2
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --instance-ids "$INSTANCE_ID" \
  --parameters "commands=[\"curl -s '$PRESIGNED_URL' | bash\"]"

echo "✓ Script executed remotely"
```

---

## 6. BASH SCRIPT PATTERNS FOR AUTOMATION

### 6.1 SSM Send Command Wrapper Function

```bash
#!/bin/bash
# Reusable function for SSM send-command with polling

ssm_send_command() {
  local INSTANCE_ID="$1"
  local COMMANDS="$2"
  local REGION="${3:-us-east-1}"
  
  # Send command
  RESPONSE=$(aws ssm send-command \
    --document-name "AWS-RunShellScript" \
    --instance-ids "$INSTANCE_ID" \
    --parameters "commands=$COMMANDS" \
    --region "$REGION" \
    --output json)
  
  COMMAND_ID=$(echo "$RESPONSE" | jq -r '.Command.CommandId')
  
  echo "Command sent: $COMMAND_ID"
  echo "$COMMAND_ID"
}

# Get command result with polling
ssm_wait_command() {
  local COMMAND_ID="$1"
  local INSTANCE_ID="$2"
  local REGION="${3:-us-east-1}"
  local MAX_WAIT=300
  local ELAPSED=0
  
  while [ $ELAPSED -lt $MAX_WAIT ]; do
    INVOCATION=$(aws ssm get-command-invocation \
      --command-id "$COMMAND_ID" \
      --instance-id "$INSTANCE_ID" \
      --region "$REGION" \
      --output json 2>/dev/null)
    
    STATUS=$(echo "$INVOCATION" | jq -r '.Status')
    
    if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" ]]; then
      echo "$INVOCATION"
      return 0
    fi
    
    echo "Status: $STATUS (elapsed: ${ELAPSED}s)"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
  done
  
  echo "ERROR: Command did not complete within ${MAX_WAIT}s"
  return 1
}

# Usage
COMMAND_ID=$(ssm_send_command "i-1234567890abcdef0" '["echo Hello","ls -la"]')
RESULT=$(ssm_wait_command "$COMMAND_ID" "i-1234567890abcdef0")
echo "Result:"
echo "$RESULT" | jq '.StandardOutputContent'
```

### 6.2 Wait for SSM Agent to Come Online

```bash
#!/bin/bash
# Poll until instance registers with SSM

wait_for_ssm_agent() {
  local INSTANCE_ID="$1"
  local REGION="${2:-us-east-1}"
  local MAX_WAIT=600  # 10 minutes
  local ELAPSED=0
  
  echo "Waiting for SSM Agent on instance $INSTANCE_ID..."
  
  while [ $ELAPSED -lt $MAX_WAIT ]; do
    PING_STATUS=$(aws ssm describe-instance-information \
      --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
      --region "$REGION" \
      --query 'InstanceInformationList[0].PingStatus' \
      --output text 2>/dev/null)
    
    if [ "$PING_STATUS" = "Online" ]; then
      echo "✓ SSM Agent online on $INSTANCE_ID"
      return 0
    fi
    
    echo "Status: $PING_STATUS (elapsed: ${ELAPSED}s)"
    sleep 10
    ELAPSED=$((ELAPSED + 10))
  done
  
  echo "✗ Timeout: SSM Agent did not come online within ${MAX_WAIT}s"
  return 1
}

wait_for_ssm_agent "i-1234567890abcdef0"
```

### 6.3 Batch Command Execution with Error Handling

```bash
#!/bin/bash
# Send command to multiple instances, handle failures

batch_ssm_send_command() {
  local INSTANCE_IDS=("$@")
  local COMMANDS='["systemctl restart docker","sleep 5","docker ps"]'
  local REGION="us-east-1"
  local FAILED_INSTANCES=()
  
  echo "Sending commands to ${#INSTANCE_IDS[@]} instances..."
  
  # Send to all instances
  declare -A COMMAND_IDS
  for INSTANCE_ID in "${INSTANCE_IDS[@]}"; do
    RESPONSE=$(aws ssm send-command \
      --document-name "AWS-RunShellScript" \
      --instance-ids "$INSTANCE_ID" \
      --parameters "commands=$COMMANDS" \
      --region "$REGION" \
      --output json 2>&1)
    
    if [ $? -eq 0 ]; then
      COMMAND_ID=$(echo "$RESPONSE" | jq -r '.Command.CommandId')
      COMMAND_IDS["$INSTANCE_ID"]="$COMMAND_ID"
      echo "  ✓ Sent to $INSTANCE_ID (cmd: $COMMAND_ID)"
    else
      echo "  ✗ Failed to send to $INSTANCE_ID"
      FAILED_INSTANCES+=("$INSTANCE_ID")
    fi
  done
  
  # Poll for results
  echo ""
  echo "Waiting for command completion..."
  local COMPLETED=0
  local TOTAL=${#COMMAND_IDS[@]}
  
  while [ $COMPLETED -lt $TOTAL ]; do
    COMPLETED=0
    for INSTANCE_ID in "${!COMMAND_IDS[@]}"; do
      COMMAND_ID=${COMMAND_IDS[$INSTANCE_ID]}
      STATUS=$(aws ssm get-command-invocation \
        --command-id "$COMMAND_ID" \
        --instance-id "$INSTANCE_ID" \
        --region "$REGION" \
        --query 'Status' \
        --output text 2>/dev/null)
      
      if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" ]]; then
        COMPLETED=$((COMPLETED + 1))
        echo "  [$COMPLETED/$TOTAL] $INSTANCE_ID: $STATUS"
      fi
    done
    
    if [ $COMPLETED -lt $TOTAL ]; then
      sleep 5
    fi
  done
  
  echo ""
  echo "Summary:"
  echo "  Successful sends: ${#COMMAND_IDS[@]}"
  echo "  Failed sends: ${#FAILED_INSTANCES[@]}"
}

# Usage
batch_ssm_send_command i-1111111111111111 i-2222222222222222 i-3333333333333333
```

---

## 7. REPLACEMENT FOR aws-ec2-test.sh

### 7.1 Before: SSH-based Script

```bash
#!/bin/bash
# OLD: SSH-based approach (BROKEN behind corporate firewall)

INSTANCE_ID="i-1234567890abcdef0"
SSH_KEY="~/.ssh/id_rsa"
SSH_USER="ec2-user"

# This fails if port 22 is blocked!
ssh -i "$SSH_KEY" "$SSH_USER@$INSTANCE_ID" "echo 'Hello from EC2'"
```

### 7.2 After: SSM-based Script

```bash
#!/bin/bash
# NEW: SSM Session Manager approach (works through firewall)

set -e

INSTANCE_ID="i-1234567890abcdef0"
REGION="us-east-1"
MAX_WAIT=300

echo "=== AWS EC2 Test (via SSM Session Manager) ==="

# 1. Verify instance exists
echo "Checking instance status..."
INSTANCE=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --region "$REGION" \
  --query 'Reservations[0].Instances[0]' \
  --output json)

if [ -z "$INSTANCE" ]; then
  echo "ERROR: Instance $INSTANCE_ID not found"
  exit 1
fi

echo "  Instance found: $(echo "$INSTANCE" | jq -r '.State.Name')"

# 2. Verify IAM role is attached
ROLE=$(echo "$INSTANCE" | jq -r '.IamInstanceProfile.Arn // "NONE"')
if [ "$ROLE" = "NONE" ]; then
  echo "ERROR: Instance has no IAM role. Cannot use SSM."
  exit 1
fi
echo "  IAM Role: $ROLE"

# 3. Wait for SSM Agent to come online
echo ""
echo "Waiting for SSM Agent to register..."
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
  PING_STATUS=$(aws ssm describe-instance-information \
    --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
    --region "$REGION" \
    --query 'InstanceInformationList[0].PingStatus' \
    --output text 2>/dev/null)
  
  if [ "$PING_STATUS" = "Online" ]; then
    echo "  ✓ SSM Agent is Online"
    break
  fi
  
  echo "  Status: $PING_STATUS (${ELAPSED}s)"
  sleep 10
  ELAPSED=$((ELAPSED + 10))
done

if [ "$PING_STATUS" != "Online" ]; then
  echo "ERROR: SSM Agent did not come online within ${MAX_WAIT}s"
  exit 1
fi

# 4. Run test commands
echo ""
echo "Executing test commands..."

RESPONSE=$(aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --instance-ids "$INSTANCE_ID" \
  --parameters 'commands=[
    "echo \"=== System Info ===\"",
    "hostname",
    "uname -a",
    "echo \"\"",
    "echo \"=== Disk Usage ===\"",
    "df -h",
    "echo \"\"",
    "echo \"=== Memory Usage ===\"",
    "free -h"
  ]' \
  --region "$REGION" \
  --output json)

COMMAND_ID=$(echo "$RESPONSE" | jq -r '.Command.CommandId')
echo "  Command sent: $COMMAND_ID"

# 5. Poll for results
echo "  Waiting for command completion..."
COMPLETED=0
while [ $COMPLETED -lt 1 ]; do
  INVOCATION=$(aws ssm get-command-invocation \
    --command-id "$COMMAND_ID" \
    --instance-id "$INSTANCE_ID" \
    --region "$REGION" \
    --output json 2>/dev/null)
  
  STATUS=$(echo "$INVOCATION" | jq -r '.Status')
  
  if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" ]]; then
    COMPLETED=1
  else
    echo "    Status: $STATUS"
    sleep 5
  fi
done

# 6. Display results
echo ""
echo "=== Command Output ==="
echo "$INVOCATION" | jq -r '.StandardOutputContent'

if [ "$(echo "$INVOCATION" | jq -r '.StandardErrorContent')" != "" ]; then
  echo ""
  echo "=== Errors ==="
  echo "$INVOCATION" | jq -r '.StandardErrorContent'
fi

STATUS=$(echo "$INVOCATION" | jq -r '.Status')
if [ "$STATUS" = "Success" ]; then
  echo ""
  echo "✓ Test completed successfully"
  exit 0
else
  echo ""
  echo "✗ Test failed with status: $STATUS"
  exit 1
fi
```

---

## 8. TROUBLESHOOTING

### Issue: Instance Not Appearing in SSM

**Checklist:**
1. ✓ IAM role attached with `AmazonSSMManagedInstanceCore` policy
2. ✓ SSM Agent installed (check with: `sudo systemctl status amazon-ssm-agent`)
3. ✓ SSM Agent running (not just installed)
4. ✓ EC2 instance has outbound access to `ssmmessages.*.amazonaws.com` (port 443)
5. ✓ Wait 2-3 minutes after instance launch for registration

**Verify Connectivity:**
```bash
# SSH into instance first (if available)
sudo curl -I https://ssmmessages.us-east-1.amazonaws.com/

# Check SSM Agent logs
sudo tail -f /var/log/amazon/ssm/amazon-ssm-agent.log
```

### Issue: "Failed to send command"

**Check:**
1. Instance is in "Online" status in SSM
2. IAM user/role has `ssm:SendCommand` permission
3. No security group blocking outbound 443

### Issue: Session Manager Plugin Not Installed

**Solution:**
```bash
# Install for your OS
session-manager-plugin --version  # Check installation

# If not installed, download from:
# https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html
```

---

## 9. SECURITY BEST PRACTICES

### 9.1 IAM Policy for Limited User Access

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SSMSendCommand",
      "Effect": "Allow",
      "Action": [
        "ssm:SendCommand",
        "ssm:GetCommandInvocation"
      ],
      "Resource": [
        "arn:aws:ec2:*:ACCOUNT-ID:instance/*",
        "arn:aws:ssm:*:ACCOUNT-ID:document/AWS-RunShellScript"
      ],
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "us-east-1"
        }
      }
    },
    {
      "Sid": "SSMStartSession",
      "Effect": "Allow",
      "Action": "ssm:StartSession",
      "Resource": "arn:aws:ec2:us-east-1:ACCOUNT-ID:instance/*"
    }
  ]
}
```

### 9.2 Enable Session Logging

```bash
# Log to CloudWatch
aws ssm update-document \
  --content file://session-logging-config.json \
  --document-type "Session" \
  --name "SessionManagerRunShell"

# Log to S3
aws ssm create-document \
  --document-type "Session" \
  --name "MySessionConfig" \
  --content file://session-s3-logging.json
```

---

## 10. AWS CLI CHEAT SHEET

| Task | Command |
|------|---------|
| List managed instances | `aws ssm describe-instance-information` |
| Start interactive session | `aws ssm start-session --target i-xxx` |
| Run command | `aws ssm send-command --instance-ids i-xxx --parameters 'commands=["cmd"]'` |
| Get command result | `aws ssm get-command-invocation --command-id xxx --instance-id i-xxx` |
| List command invocations | `aws ssm list-command-invocations --command-id xxx` |
| Terminate session | `exit` (in interactive session) |
| Wait for SSM Agent | `aws ssm describe-instance-information --filters "Key=InstanceIds,Values=i-xxx" --query 'InstanceInformationList[0].PingStatus'` |

---

## 11. KEY REFERENCES

**Official AWS Documentation:**
- Session Manager: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html
- Send Command: https://docs.aws.amazon.com/systems-manager/latest/userguide/send-commands.html
- SSM Agent: https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent.html
- IAM Roles: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html
- AWS CLI ssm: https://docs.aws.amazon.com/cli/latest/reference/ssm/

**Managed Policies:**
- `AmazonSSMManagedInstanceCore` - Minimal permissions for SSM

**Pre-installed SSM Agent AMIs:**
- Amazon Linux 2, AL2023
- Ubuntu 16.04+
- Windows Server 2012 R2+
- RHEL 7+
- SLES 15.3+
