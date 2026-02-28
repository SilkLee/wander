# AWS SSH to SSM Migration - Quick Reference

## Problem
- Corporate firewall blocks port 22 (SSH)
- Cannot use traditional SSH to connect to EC2 instances
- Need alternative that works over HTTPS (port 443)

## Solution
**AWS Systems Manager Session Manager** - SSH replacement that uses HTTPS instead of SSH protocol

---

## Key Differences: SSH vs SSM

| Aspect | SSH (Blocked) | SSM Session Manager (Works) |
|--------|---------------|---------------------------|
| **Protocol** | SSH (port 22) | HTTPS (port 443) |
| **Firewall** | ✗ Blocked by corporate FW | ✓ Uses standard HTTPS |
| **Authentication** | SSH keys (pem files) | IAM credentials |
| **Setup** | ssh -i key.pem user@host | aws ssm start-session --target i-xxx |
| **File Transfer** | scp file user@host:/path | S3 pre-signed URLs + SSM commands |
| **Access Control** | OS-level (SSH keys) | Centralized IAM policies |

---

## Minimum Setup (3 Steps)

### Step 1: Create IAM Role with SSM Permissions

```bash
# Create role
aws iam create-role \
  --role-name EC2-SSM-Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "ec2.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Attach managed policy
aws iam attach-role-policy \
  --role-name EC2-SSM-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name EC2-SSM-InstanceProfile

# Add role to profile
aws iam add-role-to-instance-profile \
  --instance-profile-name EC2-SSM-InstanceProfile \
  --role-name EC2-SSM-Role
```

### Step 2: Launch EC2 with IAM Role

```bash
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t2.micro \
  --iam-instance-profile Name=EC2-SSM-InstanceProfile \
  --region us-east-1
```

### Step 3: Wait for SSM Agent Registration & Connect

```bash
# Wait for online status
INSTANCE_ID="i-1234567890abcdef0"
aws ssm describe-instance-information \
  --filters Key=InstanceIds,Values=$INSTANCE_ID \
  --query 'InstanceInformationList[0].PingStatus'

# Once Online, connect
aws ssm start-session --target $INSTANCE_ID

# Or run command directly
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --instance-ids $INSTANCE_ID \
  --parameters 'commands=["echo Hello"]'
```

---

## Command Translation: SSH → SSM

### Interactive Terminal

**SSH (Blocked):**
```bash
ssh -i mykey.pem ec2-user@ec2-instance.amazonaws.com
```

**SSM (Works):**
```bash
aws ssm start-session --target i-1234567890abcdef0
```

### Run Single Command

**SSH (Blocked):**
```bash
ssh -i mykey.pem ec2-user@host "df -h"
```

**SSM (Works):**
```bash
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --instance-ids i-1234567890abcdef0 \
  --parameters 'commands=["df -h"]'
```

### Copy File TO Instance

**SCP (Blocked):**
```bash
scp -i mykey.pem file.txt ec2-user@host:/tmp/
```

**SSM (Works):**
```bash
# 1. Upload file to S3
aws s3 cp file.txt s3://my-bucket/uploads/file.txt

# 2. Get pre-signed URL
PRESIGNED=$(aws s3 presign s3://my-bucket/uploads/file.txt --expires-in 3600)

# 3. Download via SSM
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --instance-ids i-xxx \
  --parameters "commands=[\"curl -o /tmp/file.txt '$PRESIGNED'\"]"
```

### Copy File FROM Instance

**SCP (Blocked):**
```bash
scp -i mykey.pem ec2-user@host:/var/log/app.log ./
```

**SSM (Works):**
```bash
# 1. Upload from instance to S3
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --instance-ids i-xxx \
  --parameters 'commands=["aws s3 cp /var/log/app.log s3://my-bucket/downloads/"]'

# 2. Download locally
aws s3 cp s3://my-bucket/downloads/app.log ./
```

### Execute Script

**SSH (Blocked):**
```bash
scp -i mykey.pem setup.sh ec2-user@host:/tmp/
ssh -i mykey.pem ec2-user@host "bash /tmp/setup.sh"
```

**SSM (Works):**
```bash
# 1. Upload script to S3
aws s3 cp setup.sh s3://my-bucket/scripts/setup.sh

# 2. Get pre-signed URL
PRESIGNED=$(aws s3 presign s3://my-bucket/scripts/setup.sh --expires-in 3600)

# 3. Execute via SSM
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --instance-ids i-xxx \
  --parameters "commands=[\"curl -s '$PRESIGNED' | bash\"]"
```

---

## Required AWS CLI Commands

### 1. Verify Instance is Ready for SSM

```bash
aws ssm describe-instance-information \
  --filters Key=InstanceIds,Values=i-1234567890abcdef0 \
  --query 'InstanceInformationList[0].{Id:InstanceId,Status:PingStatus,OS:PlatformType}'
```

Expected output:
```
{
    "Id": "i-1234567890abcdef0",
    "Status": "Online",
    "OS": "Linux"
}
```

### 2. Send Command and Get Result

```bash
# Send command
COMMAND_ID=$(aws ssm send-command \
  --document-name AWS-RunShellScript \
  --instance-ids i-1234567890abcdef0 \
  --parameters 'commands=["ls -la /tmp"]' \
  --query 'Command.CommandId' \
  --output text)

# Wait a moment for execution
sleep 5

# Get result
aws ssm get-command-invocation \
  --command-id $COMMAND_ID \
  --instance-id i-1234567890abcdef0 \
  --query 'StandardOutputContent' \
  --output text
```

### 3. Run on Multiple Instances (by tag)

```bash
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --targets Key=tag:Environment,Values=Production \
  --parameters 'commands=["systemctl restart nginx"]'
```

### 4. Capture Output to S3

```bash
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --instance-ids i-1234567890abcdef0 \
  --parameters 'commands=["df -h","free -h"]' \
  --output-s3-bucket-name my-ssm-output \
  --output-s3-key-prefix logs/
```

Output location: `s3://my-ssm-output/logs/[CommandId]/i-1234567890abcdef0/`

---

## Bash Script Template: Replace aws-ec2-test.sh

```bash
#!/bin/bash
# New SSM-based test script (replaces old SSH version)

set -e

INSTANCE_ID="${1:-i-1234567890abcdef0}"
REGION="${2:-us-east-1}"

echo "=== EC2 Test via SSM Session Manager ==="

# Step 1: Check instance exists and has IAM role
INSTANCE=$(aws ec2 describe-instances \
  --instance-ids "$INSTANCE_ID" \
  --region "$REGION" \
  --query 'Reservations[0].Instances[0]')

if [ -z "$INSTANCE" ]; then
  echo "ERROR: Instance not found"
  exit 1
fi

ROLE=$(echo "$INSTANCE" | jq -r '.IamInstanceProfile.Arn // "NONE"')
if [ "$ROLE" = "NONE" ]; then
  echo "ERROR: Instance missing IAM role"
  exit 1
fi

echo "Instance: $INSTANCE_ID (Role: $ROLE)"

# Step 2: Wait for SSM Agent
echo "Waiting for SSM Agent..."
for i in {1..30}; do
  STATUS=$(aws ssm describe-instance-information \
    --filters Key=InstanceIds,Values="$INSTANCE_ID" \
    --region "$REGION" \
    --query 'InstanceInformationList[0].PingStatus' \
    --output text 2>/dev/null)
  
  if [ "$STATUS" = "Online" ]; then
    echo "✓ SSM Agent Online"
    break
  fi
  
  echo "  Waiting... ($STATUS)"
  sleep 10
done

# Step 3: Run test
echo "Running system test..."

CMD_ID=$(aws ssm send-command \
  --document-name AWS-RunShellScript \
  --instance-ids "$INSTANCE_ID" \
  --region "$REGION" \
  --parameters 'commands=[
    "echo Testing System",
    "hostname",
    "df -h",
    "free -h"
  ]' \
  --query 'Command.CommandId' \
  --output text)

echo "Command: $CMD_ID"

# Step 4: Poll for result
sleep 5
RESULT=$(aws ssm get-command-invocation \
  --command-id "$CMD_ID" \
  --instance-id "$INSTANCE_ID" \
  --region "$REGION" \
  --output json)

echo ""
echo "=== Output ==="
echo "$RESULT" | jq -r '.StandardOutputContent'

STATUS=$(echo "$RESULT" | jq -r '.Status')
if [ "$STATUS" = "Success" ]; then
  echo ""
  echo "✓ Test successful"
  exit 0
else
  echo ""
  echo "✗ Test failed: $STATUS"
  exit 1
fi
```

---

## Installing Session Manager Plugin (for interactive sessions)

Only needed if using `aws ssm start-session` (interactive terminal).
Not needed for `aws ssm send-command`.

**macOS:**
```bash
brew install --cask session-manager-plugin
```

**Ubuntu/Debian:**
```bash
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/ubuntu_64bit/session-manager-plugin.deb" -o "session-manager-plugin.deb"
sudo dpkg -i session-manager-plugin.deb
```

**Windows (PowerShell):**
```powershell
$installer = "SessionManagerPluginSetup.exe"
$url = "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/windows/$installer"
Invoke-WebRequest -Uri $url -OutFile $installer
& ".\$installer" /quiet
```

---

## Security: IAM Policies for Users

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:StartSession",
        "ssm:SendCommand",
        "ssm:GetCommandInvocation"
      ],
      "Resource": "arn:aws:ec2:us-east-1:ACCOUNT-ID:instance/*"
    },
    {
      "Effect": "Allow",
      "Action": "ssm:DescribeInstanceInformation",
      "Resource": "*"
    }
  ]
}
```

---

## Common Mistakes

❌ **Forgetting to attach IAM role to instance**
- Instance won't appear in SSM

❌ **Attaching wrong IAM policy**
- Permissions too restrictive or wrong service

❌ **Not waiting for SSM Agent to come online**
- Agent takes 2-3 minutes to register after instance launch

❌ **Using old SSH commands instead of SSM**
- Will fail if port 22 blocked

❌ **Not quoting JSON parameters correctly**
- Use single quotes on Linux, escape on Windows

---

## Documentation Files Created

1. **SSM_SESSION_MANAGER_MIGRATION_GUIDE.md** - Complete guide with all details
2. **aws-ec2-ssm-examples.sh** - Reusable bash functions and complete examples
3. **SSM_IAM_POLICIES_AND_DOCUMENTS.json** - JSON reference for policies and commands
4. **QUICK_REFERENCE.md** - This file - for quick lookups

---

## Next Steps

1. ✓ Review `SSM_SESSION_MANAGER_MIGRATION_GUIDE.md` for full details
2. ✓ Source `aws-ec2-ssm-examples.sh` into your scripts
3. ✓ Update `aws-ec2-test.sh` using the template provided
4. ✓ Test with: `./aws-ec2-ssm-examples.sh example`
5. ✓ Integrate SSM patterns into your CI/CD pipeline

---

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Instance not in SSM list | Check IAM role attached + policy + SSM Agent running |
| "UnauthorizedOperation" | Verify IAM credentials + region |
| Session times out | Check security group allows outbound 443 |
| File transfer fails | Verify S3 bucket exists + instance has S3 permissions |
| Command hangs | Instance likely offline; check SSM Agent logs |

**References:**
- [AWS SSM Session Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html)
- [AWS CLI SSM Commands](https://docs.aws.amazon.com/cli/latest/reference/ssm/)
- [IAM Policies for EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html)
