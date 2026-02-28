# Day 10 RAG Integration Testing - AWS EC2 Automation

## Overview

This automation will:
1. ✅ Install AWS CLI in WSL (already done)
2. Configure your AWS credentials
3. Launch a temporary EC2 instance (t3.medium, ~$0.05/hour)
4. Install Docker and dependencies automatically
5. Copy WorkflowAI code to EC2
6. Run Day 10 integration tests
7. **Automatically cleanup** (terminate instance, delete resources)

**Total cost**: Less than $0.05 (instance runs ~10-15 minutes)

---

## Step 1: Configure AWS Credentials

You need your AWS Access Key ID and Secret Access Key:

### Get your credentials from AWS Console:
1. Open https://ap-southeast-1.console.aws.amazon.com/iam/
2. Click **Users** (left sidebar)
3. Click your username
4. Click **Security credentials** tab
5. Under "Access keys", click **Create access key**
6. Choose "Command Line Interface (CLI)"
7. Check "I understand..." → Click **Next**
8. Click **Create access key**
9. **IMPORTANT**: Copy both keys immediately (you won't see them again)

### Configure AWS CLI:

Open PowerShell and run:

```powershell
wsl -d xde-22 -e bash aws-setup.sh
```

It will prompt for:
- **AWS Access Key ID**: (paste from AWS Console)
- **AWS Secret Access Key**: (paste from AWS Console)
- **Default region**: Press Enter (defaults to ap-southeast-1)

The script will verify your credentials by calling `aws sts get-caller-identity`.

---

## Step 2: Run Automated Tests

Once credentials are configured, run:

```powershell
wsl -d xde-22 -e bash aws-ec2-test.sh
```

### What happens:
```
[1/8] Creating SSH key pair...          (5 seconds)
[2/8] Creating security group...        (5 seconds)
[3/8] Launching EC2 instance...         (10 seconds)
[4/8] Waiting for instance to start...  (30-60 seconds)
[5/8] Waiting for SSH and Docker...     (2-3 minutes)
[6/8] Copying code to EC2...            (30 seconds)
[7/8] Running Day 10 tests...           (2-3 minutes)
[8/8] Cleaning up AWS resources...      (30 seconds)
```

**Total time**: 6-10 minutes

---

## What Gets Tested

The script runs `test-day10-internal.sh` on EC2, which tests:

1. ✅ Elasticsearch health
2. ✅ Indexing Service health + model loading
3. ✅ Agent Orchestrator health
4. ✅ Knowledge Base population (20 documents)
5. ✅ Semantic search
6. ✅ Hybrid search (semantic + keyword)
7. ✅ RAG-enhanced log analysis
8. ✅ Context-aware failure diagnosis

---

## Cost Breakdown

- **EC2 instance**: t3.medium @ $0.0416/hour × 0.2 hours = **$0.008**
- **Data transfer**: ~100MB upload (free tier)
- **EBS storage**: 8GB × 0.2 hours = **$0.0003**
- **Total**: **< $0.01** (less than 1 cent)

Resources are **automatically terminated** after tests complete.

---

## Troubleshooting

### If credential verification fails:
```bash
# Check configuration
wsl -d xde-22 -e bash -c "aws configure list"

# Test connection
wsl -d xde-22 -e bash -c "aws sts get-caller-identity"
```

### If EC2 launch fails:
- Check IAM permissions: Your user needs `ec2:*` permissions
- Check account limits: You need at least 1 available vCPU in ap-southeast-1

### If tests fail:
- Check EC2 logs: SSH into instance before it terminates
- Review test output in terminal

---

## Manual Cleanup (if script fails)

If the script is interrupted, cleanup manually:

```bash
# List instances
wsl -d xde-22 -e bash -c "aws ec2 describe-instances --region ap-southeast-1 --filters 'Name=tag:Name,Values=workflow-ai-day10-test' --query 'Reservations[].Instances[].[InstanceId,State.Name]' --output table"

# Terminate instance
wsl -d xde-22 -e bash -c "aws ec2 terminate-instances --region ap-southeast-1 --instance-ids <INSTANCE_ID>"

# Delete security group (after instance terminated)
wsl -d xde-22 -e bash -c "aws ec2 delete-security-group --region ap-southeast-1 --group-id <SG_ID>"

# Delete key pair
wsl -d xde-22 -e bash -c "aws ec2 delete-key-pair --region ap-southeast-1 --key-name <KEY_NAME>"
```

---

## After Testing

Once tests pass:
- ✅ Day 10 RAG implementation verified on clean cloud VM
- ✅ Elasticsearch + Indexing + Agent integration confirmed
- ✅ Ready to proceed to **Day 11: Multi-agent orchestration (LangGraph)**

---

## Files Created

- `aws-setup.sh` - AWS credential configuration
- `aws-ec2-test.sh` - Automated EC2 testing script
- `test-day10-internal.sh` - Docker internal test script (already exists)

---

**Ready to start?**

1. Run: `wsl -d xde-22 -e bash aws-setup.sh`
2. Run: `wsl -d xde-22 -e bash aws-ec2-test.sh`
3. Wait 6-10 minutes
4. See results!
