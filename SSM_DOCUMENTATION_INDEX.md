# AWS Systems Manager (SSM) - SSH Replacement Documentation

**Created:** February 28, 2026  
**Purpose:** Complete migration guide from SSH (port 22) to AWS Systems Manager Session Manager (HTTPS/443)  
**Status:** ✓ Ready for use - All AWS CLI commands verified with official documentation

---

## 📋 Documentation Files

### 1. **SSM_SESSION_MANAGER_MIGRATION_GUIDE.md** (23 KB)
**Comprehensive reference covering all aspects of SSM migration.**

**Contents:**
- Overview of Session Manager fundamentals
- Complete IAM setup (AWS-managed & custom policies)
- EC2 instance requirements & SSM Agent verification
- AWS CLI command reference with examples
- File transfer patterns (S3-based, no SCP needed)
- Bash script patterns for automation
- Complete aws-ec2-test.sh replacement
- Troubleshooting section
- Security best practices

**Key Sections:**
- Section 2: IAM Role setup (copy-paste ready)
- Section 4: AWS CLI commands (all 8 command types)
- Section 5: File transfer without SCP
- Section 6: Reusable bash functions
- Section 7: Complete replacement script example

**Use this for:** Deep dives, implementation details, troubleshooting

---

### 2. **SSM_QUICK_REFERENCE.md** (11 KB)
**Quick lookup guide - minimal setup to working solution.**

**Contents:**
- Problem/solution comparison
- SSH vs SSM differences table
- Minimum 3-step setup
- Command translation examples (SSH → SSM)
- Required AWS CLI commands
- Bash script template
- Session Manager plugin installation
- Common mistakes
- Troubleshooting table

**Use this for:** Getting started fast, quick lookups, syntax reminders

---

### 3. **aws-ec2-ssm-examples.sh** (14 KB)
**Reusable bash functions - source and use directly in your scripts.**

**Functions included (copy-paste ready):**

#### Setup Functions:
```bash
setup_ssm_iam_role [ROLE_NAME] [REGION]
setup_ssm_instance_profile [ROLE_NAME] [PROFILE_NAME] [REGION]
```

#### Instance Functions:
```bash
launch_instance_with_ssm [IMAGE_ID] [INSTANCE_TYPE] [SECURITY_GROUP_ID] [REGION]
```

#### Wait/Polling Functions:
```bash
wait_for_ssm_agent [INSTANCE_ID] [REGION] [MAX_WAIT_SECONDS]
wait_for_command [COMMAND_ID] [INSTANCE_ID] [REGION] [MAX_WAIT_SECONDS]
```

#### Command Functions:
```bash
ssm_send_command [INSTANCE_ID] [COMMANDS_JSON] [REGION]
ssm_run_command_blocking [INSTANCE_ID] [COMMANDS_JSON] [REGION]
ssm_send_command_bulk [INSTANCE_ID1] [INSTANCE_ID2] ... [COMMANDS_JSON]
```

#### File Transfer Functions:
```bash
ssm_upload_file [LOCAL_FILE] [INSTANCE_ID] [REMOTE_PATH] [S3_BUCKET] [REGION]
ssm_download_file [INSTANCE_ID] [REMOTE_FILE] [LOCAL_DEST] [S3_BUCKET] [REGION]
```

#### Test Functions:
```bash
test_ssm_basic [INSTANCE_ID] [REGION]
test_ssm_with_errors [INSTANCE_ID] [REGION]
example_complete_workflow
```

**Usage:**
```bash
# Source in your scripts
source aws-ec2-ssm-examples.sh

# Use functions directly
wait_for_ssm_agent i-1234567890abcdef0
test_ssm_basic i-1234567890abcdef0

# Run complete example
./aws-ec2-ssm-examples.sh example
```

**Use this for:** Integration into automation scripts, CI/CD pipelines

---

### 4. **SSM_IAM_POLICIES_AND_DOCUMENTS.json** (15 KB)
**JSON reference - policies, documents, commands, troubleshooting.**

**Contents (JSON structured):**

#### IAM Policies:
- `AmazonSSMManagedInstanceCore` - AWS managed policy details
- `minimal_ssm_session_manager` - Custom minimal policy
- `minimal_ssm_send_command` - Run Command only policy
- `ssm_with_s3_output` - With S3 bucket output
- `ssm_user_limited_access` - For end-user IAM policies

#### SSM Documents:
- AWS-RunShellScript (Linux)
- AWS-RunPowerShellScript (Windows)
- AWS-ConfigureAWSPackage
- AWS-RunPatchBaseline

#### Command Examples:
- Single command execution
- Multiple commands
- Tagged instance targeting
- S3 output capture
- CloudWatch Logs streaming
- Concurrency control
- Command invocation polling
- Output parsing (JQ examples)

#### Troubleshooting Reference:
- Instance not in SSM (causes & fixes)
- Command status failures
- Command hangs
- Bash utility functions

**Use this for:** Copy-paste policies, command reference, troubleshooting

---

## 🎯 Quick Start (5 minutes)

### For Someone Who Just Wants It Working:

```bash
# 1. Create IAM role and profile
./aws-ec2-ssm-examples.sh  # Read setup section

# 2. Launch instance
INSTANCE=$(aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t2.micro \
  --iam-instance-profile Name=EC2-SSM-InstanceProfile | \
  jq -r '.Instances[0].InstanceId')

# 3. Wait for online
source aws-ec2-ssm-examples.sh
wait_for_ssm_agent $INSTANCE

# 4. Connect
aws ssm start-session --target $INSTANCE
```

---

## 🔧 Common Tasks

### Task: Run Command and Get Output
**File:** SSM_SESSION_MANAGER_MIGRATION_GUIDE.md (Section 4.4)
```bash
COMMAND_ID=$(aws ssm send-command \
  --document-name AWS-RunShellScript \
  --instance-ids i-xxx \
  --parameters 'commands=["echo test"]' \
  --query 'Command.CommandId' --output text)

sleep 5

aws ssm get-command-invocation \
  --command-id $COMMAND_ID \
  --instance-id i-xxx
```

### Task: Transfer File (Replace SCP)
**File:** SSM_SESSION_MANAGER_MIGRATION_GUIDE.md (Section 5)
**Script:** aws-ec2-ssm-examples.sh (ssm_upload_file, ssm_download_file)
```bash
source aws-ec2-ssm-examples.sh
ssm_upload_file "local-file.txt" "i-xxx" "/tmp/file.txt"
```

### Task: Run on Multiple Instances
**File:** SSM_SESSION_MANAGER_MIGRATION_GUIDE.md (Section 4.5)
```bash
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --targets "Key=tag:Environment,Values=Production" \
  --parameters 'commands=["systemctl restart nginx"]'
```

### Task: Wait for Instance Ready
**File:** SSM_SESSION_MANAGER_MIGRATION_GUIDE.md (Section 3.3)
**Script:** aws-ec2-ssm-examples.sh (wait_for_ssm_agent)
```bash
source aws-ec2-ssm-examples.sh
wait_for_ssm_agent i-xxx us-east-1 600
```

---

## 🔐 Security & IAM

**Default AWS Managed Policy:**
```
arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
```

**Custom User Policy:** See SSM_IAM_POLICIES_AND_DOCUMENTS.json
- Includes only necessary SSM permissions
- Scoped to specific regions/instances

**Trust Policy:**
```json
{
  "Service": "ec2.amazonaws.com"
}
```

---

## 🐛 Troubleshooting Quick Links

| Problem | File | Section |
|---------|------|---------|
| Instance not appearing in SSM | SSM_SESSION_MANAGER_MIGRATION_GUIDE.md | Section 8 |
| "Failed to send command" | SSM_SESSION_MANAGER_MIGRATION_GUIDE.md | Section 8 |
| Command hangs indefinitely | SSM_IAM_POLICIES_AND_DOCUMENTS.json | troubleshooting_reference |
| Session Manager plugin not installed | SSM_QUICK_REFERENCE.md | Plugin Installation |
| File transfer fails | SSM_SESSION_MANAGER_MIGRATION_GUIDE.md | Section 5 |

---

## 📊 AWS Services & Endpoints Used

### Core Services:
- **AWS Systems Manager** - Command execution, session management
- **Amazon EC2** - Instance management
- **AWS IAM** - Role and policy management
- **Amazon S3** - File transfer (optional)

### Network Endpoints:
- `ssmmessages.*.amazonaws.com:443` (Session Manager)
- `ec2messages.*.amazonaws.com:443` (Run Command)
- `s3.amazonaws.com:443` (File transfers)

### Required Outbound Access:
- Port 443 (HTTPS) - Required
- No inbound ports required

---

## 🔗 Official AWS Documentation References

1. **Session Manager Overview**
   - https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html

2. **Send Command (Run Command)**
   - https://docs.aws.amazon.com/systems-manager/latest/userguide/send-commands.html

3. **SSM Agent**
   - https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent.html

4. **IAM Roles for EC2**
   - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html

5. **AWS CLI SSM Commands**
   - https://docs.aws.amazon.com/cli/latest/reference/ssm/

6. **Managed Instances**
   - https://docs.aws.amazon.com/systems-manager/latest/userguide/managed-instances.html

---

## ✅ What You Can Do Now

After using these resources, you can:

✓ Launch EC2 instances configured for SSM (no SSH needed)  
✓ Connect to instances via Session Manager (HTTPS, not SSH)  
✓ Run commands on instances remotely  
✓ Transfer files without SCP (using S3)  
✓ Execute scripts on instances  
✓ Monitor command execution with polling  
✓ Control access via IAM (no SSH key management)  
✓ Scale to thousands of instances with tags  
✓ Work through corporate firewalls that block port 22  

---

## 🚀 Integration with Your Tools

### Terraform
```hcl
# Attach SSM role during instance creation
iam_instance_profile = aws_iam_instance_profile.ssm.name
```

### AWS CloudFormation
```yaml
IamInstanceProfile: !Ref EC2SSMInstanceProfile
```

### Ansible
```yaml
- name: Run SSM command
  ansible.builtin.command: |
    aws ssm send-command 
    --instance-ids {{ instance_id }} 
    --parameters commands=['{{ command }}']
```

### CI/CD Pipelines
```bash
# In your deployment script
source aws-ec2-ssm-examples.sh
ssm_send_command_bulk $INSTANCE_IDS '["deploy-app.sh"]'
```

---

## 📝 File Index

| File | Size | Type | Purpose |
|------|------|------|---------|
| SSM_SESSION_MANAGER_MIGRATION_GUIDE.md | 23 KB | Markdown | Complete reference guide |
| SSM_QUICK_REFERENCE.md | 11 KB | Markdown | Quick lookup guide |
| aws-ec2-ssm-examples.sh | 14 KB | Bash | Reusable functions |
| SSM_IAM_POLICIES_AND_DOCUMENTS.json | 15 KB | JSON | Policies and commands reference |
| README.md | This file | Markdown | Navigation and index |

**Total:** ~70 KB of ready-to-use, official AWS documentation and working code

---

## ❓ FAQ

**Q: Do I need SSH access after setting up SSM?**  
A: No. SSM Session Manager replaces SSH entirely.

**Q: Does SSM work if public IP is not available?**  
A: Yes. Only outbound HTTPS (443) is needed. Works in private subnets.

**Q: Can I use SSM with VPC endpoints?**  
A: Yes. Improves security by keeping traffic on AWS network.

**Q: How much does SSM cost?**  
A: No additional cost for EC2 instances. Session Manager is free.

**Q: Can I use SSM for Windows instances?**  
A: Yes. Use AWS-RunPowerShellScript instead of AWS-RunShellScript.

**Q: How do I grant other users access?**  
A: Attach IAM policy with ssm:StartSession and ssm:SendCommand permissions.

---

## 📞 Support

For issues or questions:
1. Check troubleshooting section in SSM_SESSION_MANAGER_MIGRATION_GUIDE.md
2. Review SSM_IAM_POLICIES_AND_DOCUMENTS.json troubleshooting_reference
3. Verify IAM permissions match examples
4. Check AWS CloudTrail for API errors

---

## 📄 License & Attribution

All documentation and code examples are based on:
- Official AWS documentation (Systems Manager, EC2, IAM)
- AWS CLI reference documentation
- Proven patterns from AWS best practices

All code is original and provided for use.

---

**Ready to get started?** Start with SSM_QUICK_REFERENCE.md for immediate setup, then reference SSM_SESSION_MANAGER_MIGRATION_GUIDE.md for detailed information.
