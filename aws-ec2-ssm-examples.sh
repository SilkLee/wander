#!/bin/bash
# AWS EC2 SSM Session Manager - Ready-to-use Example Scripts
# Location: aws-ec2-ssm-examples.sh
# Usage: Source this file or extract individual functions

set -e

###############################################################################
# 1. SETUP FUNCTIONS - IAM Role and Instance Profile Creation
###############################################################################

setup_ssm_iam_role() {
  local ROLE_NAME="${1:-EC2-SSM-Role}"
  local REGION="${2:-us-east-1}"
  
  echo "Creating IAM role: $ROLE_NAME"
  
  # Create role
  aws iam create-role \
    --role-name "$ROLE_NAME" \
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
    }' \
    --region "$REGION" 2>/dev/null || echo "  (role may already exist)"
  
  # Attach policy
  aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore" \
    --region "$REGION" 2>/dev/null || echo "  (policy may already be attached)"
  
  echo "✓ IAM role ready: $ROLE_NAME"
}

setup_ssm_instance_profile() {
  local ROLE_NAME="${1:-EC2-SSM-Role}"
  local PROFILE_NAME="${2:-EC2-SSM-InstanceProfile}"
  local REGION="${3:-us-east-1}"
  
  echo "Creating instance profile: $PROFILE_NAME"
  
  # Create instance profile
  aws iam create-instance-profile \
    --instance-profile-name "$PROFILE_NAME" \
    --region "$REGION" 2>/dev/null || echo "  (profile may already exist)"
  
  # Add role to profile
  aws iam add-role-to-instance-profile \
    --instance-profile-name "$PROFILE_NAME" \
    --role-name "$ROLE_NAME" \
    --region "$REGION" 2>/dev/null || echo "  (role may already be in profile)"
  
  echo "✓ Instance profile ready: $PROFILE_NAME"
}

###############################################################################
# 2. LAUNCH INSTANCE WITH SSM CAPABILITY
###############################################################################

launch_instance_with_ssm() {
  local IMAGE_ID="${1:-ami-0c55b159cbfafe1f0}"  # Amazon Linux 2
  local INSTANCE_TYPE="${2:-t2.micro}"
  local SECURITY_GROUP_ID="${3}"
  local REGION="${4:-us-east-1}"
  
  local PROFILE_NAME="EC2-SSM-InstanceProfile"
  
  echo "Launching EC2 instance with SSM capability..."
  
  RESPONSE=$(aws ec2 run-instances \
    --image-id "$IMAGE_ID" \
    --instance-type "$INSTANCE_TYPE" \
    --iam-instance-profile "Name=$PROFILE_NAME" \
    --security-group-ids "${SECURITY_GROUP_ID:-default}" \
    --region "$REGION" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=SSM-Test},{Key=ManagedBy,Value=SSM}]" \
    --output json)
  
  INSTANCE_ID=$(echo "$RESPONSE" | jq -r '.Instances[0].InstanceId')
  
  echo "✓ Instance launched: $INSTANCE_ID"
  echo "  (Waiting for SSM Agent registration...)"
  
  wait_for_ssm_agent "$INSTANCE_ID" "$REGION"
  
  echo "$INSTANCE_ID"
}

###############################################################################
# 3. POLLING AND WAIT FUNCTIONS
###############################################################################

wait_for_ssm_agent() {
  local INSTANCE_ID="$1"
  local REGION="${2:-us-east-1}"
  local MAX_WAIT="${3:-600}"  # 10 minutes default
  local ELAPSED=0
  
  echo "Waiting for SSM Agent to register on $INSTANCE_ID..."
  
  while [ $ELAPSED -lt "$MAX_WAIT" ]; do
    PING_STATUS=$(aws ssm describe-instance-information \
      --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
      --region "$REGION" \
      --query 'InstanceInformationList[0].PingStatus' \
      --output text 2>/dev/null)
    
    if [ "$PING_STATUS" = "Online" ]; then
      echo "✓ SSM Agent is Online on $INSTANCE_ID"
      return 0
    fi
    
    printf "  Status: %-10s (elapsed: %3ds)\r" "$PING_STATUS" "$ELAPSED"
    sleep 10
    ELAPSED=$((ELAPSED + 10))
  done
  
  echo ""
  echo "✗ Timeout: SSM Agent did not come online within ${MAX_WAIT}s on $INSTANCE_ID"
  return 1
}

wait_for_command() {
  local COMMAND_ID="$1"
  local INSTANCE_ID="$2"
  local REGION="${3:-us-east-1}"
  local MAX_WAIT="${4:-300}"  # 5 minutes default
  local ELAPSED=0
  
  echo "Waiting for command $COMMAND_ID on $INSTANCE_ID..."
  
  while [ $ELAPSED -lt "$MAX_WAIT" ]; do
    INVOCATION=$(aws ssm get-command-invocation \
      --command-id "$COMMAND_ID" \
      --instance-id "$INSTANCE_ID" \
      --region "$REGION" \
      --output json 2>/dev/null)
    
    STATUS=$(echo "$INVOCATION" | jq -r '.Status')
    
    if [[ "$STATUS" == "Success" || "$STATUS" == "Failed" ]]; then
      echo "✓ Command completed: $STATUS"
      echo "$INVOCATION"
      return 0
    fi
    
    printf "  Status: %-10s (elapsed: %3ds)\r" "$STATUS" "$ELAPSED"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
  done
  
  echo ""
  echo "✗ Timeout: Command did not complete within ${MAX_WAIT}s"
  return 1
}

###############################################################################
# 4. COMMAND EXECUTION FUNCTIONS
###############################################################################

ssm_send_command() {
  local INSTANCE_ID="$1"
  local COMMANDS="$2"
  local REGION="${3:-us-east-1}"
  
  RESPONSE=$(aws ssm send-command \
    --document-name "AWS-RunShellScript" \
    --instance-ids "$INSTANCE_ID" \
    --parameters "commands=$COMMANDS" \
    --region "$REGION" \
    --output json)
  
  COMMAND_ID=$(echo "$RESPONSE" | jq -r '.Command.CommandId')
  echo "$COMMAND_ID"
}

ssm_send_command_bulk() {
  local INSTANCE_IDS=("${@:1:$#-1}")
  local COMMANDS="${@: -1}"
  local REGION="us-east-1"
  
  echo "Sending command to ${#INSTANCE_IDS[@]} instances..."
  
  declare -A COMMAND_IDS
  for INSTANCE_ID in "${INSTANCE_IDS[@]}"; do
    COMMAND_ID=$(ssm_send_command "$INSTANCE_ID" "$COMMANDS" "$REGION")
    COMMAND_IDS["$INSTANCE_ID"]="$COMMAND_ID"
    echo "  ✓ $INSTANCE_ID -> $COMMAND_ID"
  done
  
  # Return associative array reference (in bash 4.3+)
  for KEY in "${!COMMAND_IDS[@]}"; do
    echo "${KEY}:${COMMAND_IDS[$KEY]}"
  done
}

ssm_run_command_blocking() {
  local INSTANCE_ID="$1"
  local COMMANDS="$2"
  local REGION="${3:-us-east-1}"
  
  COMMAND_ID=$(ssm_send_command "$INSTANCE_ID" "$COMMANDS" "$REGION")
  RESULT=$(wait_for_command "$COMMAND_ID" "$INSTANCE_ID" "$REGION")
  echo "$RESULT"
}

###############################################################################
# 5. FILE TRANSFER FUNCTIONS
###############################################################################

ssm_upload_file() {
  local LOCAL_FILE="$1"
  local INSTANCE_ID="$2"
  local REMOTE_PATH="$3"
  local S3_BUCKET="${4:-ssm-file-transfer-$(date +%s)}"
  local REGION="${5:-us-east-1}"
  
  if [ ! -f "$LOCAL_FILE" ]; then
    echo "ERROR: Local file not found: $LOCAL_FILE"
    return 1
  fi
  
  # Use random key to avoid conflicts
  local S3_KEY="transfers/$(date +%s)-$(basename "$LOCAL_FILE")"
  
  echo "Uploading $LOCAL_FILE to S3 ($S3_BUCKET/$S3_KEY)..."
  
  # Ensure bucket exists
  aws s3 ls "s3://$S3_BUCKET" --region "$REGION" >/dev/null 2>&1 || \
    aws s3 mb "s3://$S3_BUCKET" --region "$REGION"
  
  # Upload file
  aws s3 cp "$LOCAL_FILE" "s3://$S3_BUCKET/$S3_KEY" --region "$REGION"
  
  # Generate pre-signed URL (1 hour)
  PRESIGNED_URL=$(aws s3 presign "s3://$S3_BUCKET/$S3_KEY" \
    --expires-in 3600 --region "$REGION")
  
  echo "Downloading to $INSTANCE_ID:$REMOTE_PATH..."
  
  # Send download command
  COMMANDS="[\"mkdir -p \$(dirname $REMOTE_PATH)\",\"curl -o $REMOTE_PATH '$PRESIGNED_URL'\",\"ls -lh $REMOTE_PATH\"]"
  
  RESULT=$(ssm_run_command_blocking "$INSTANCE_ID" "$COMMANDS" "$REGION")
  
  echo "✓ File uploaded and downloaded"
  echo "$RESULT" | jq -r '.StandardOutputContent'
}

ssm_download_file() {
  local INSTANCE_ID="$1"
  local REMOTE_FILE="$2"
  local LOCAL_DEST="${3:-.}"
  local S3_BUCKET="${4:-ssm-file-transfer-$(date +%s)}"
  local REGION="${5:-us-east-1}"
  
  local S3_KEY="transfers/$(date +%s)-$(basename "$REMOTE_FILE")"
  
  echo "Uploading $REMOTE_FILE from $INSTANCE_ID to S3..."
  
  # Ensure bucket exists
  aws s3 ls "s3://$S3_BUCKET" --region "$REGION" >/dev/null 2>&1 || \
    aws s3 mb "s3://$S3_BUCKET" --region "$REGION"
  
  # EC2 uploads to S3
  COMMANDS="[\"aws s3 cp $REMOTE_FILE s3://$S3_BUCKET/$S3_KEY\"]"
  ssm_run_command_blocking "$INSTANCE_ID" "$COMMANDS" "$REGION"
  
  # Download to local
  echo "Downloading to $LOCAL_DEST..."
  aws s3 cp "s3://$S3_BUCKET/$S3_KEY" "$LOCAL_DEST/" --region "$REGION"
  
  echo "✓ File downloaded to $LOCAL_DEST/$(basename "$REMOTE_FILE")"
}

###############################################################################
# 6. TEST FUNCTIONS
###############################################################################

test_ssm_basic() {
  local INSTANCE_ID="$1"
  local REGION="${2:-us-east-1}"
  
  echo "=== Running Basic SSM Test on $INSTANCE_ID ==="
  echo ""
  
  COMMANDS='[
    "echo \"=== System Information ===\"",
    "hostname",
    "uname -a",
    "echo \"\"",
    "echo \"=== Disk Usage ===\"",
    "df -h",
    "echo \"\"",
    "echo \"=== Memory ===\"",
    "free -h",
    "echo \"\"",
    "echo \"=== Date ===\"",
    "date"
  ]'
  
  RESULT=$(ssm_run_command_blocking "$INSTANCE_ID" "$COMMANDS" "$REGION")
  
  echo "$RESULT" | jq -r '.StandardOutputContent'
}

test_ssm_with_errors() {
  local INSTANCE_ID="$1"
  local REGION="${2:-us-east-1}"
  
  echo "=== Running Error Handling Test ==="
  echo ""
  
  COMMANDS='[
    "echo \"Command 1: Success\"",
    "ls /tmp",
    "echo \"Command 3: Checking file that does not exist\"",
    "cat /nonexistent/file.txt || echo \"(File not found - expected)\"",
    "echo \"Command 5: All done\""
  ]'
  
  RESULT=$(ssm_run_command_blocking "$INSTANCE_ID" "$COMMANDS" "$REGION")
  
  echo "STDOUT:"
  echo "$RESULT" | jq -r '.StandardOutputContent'
  
  echo ""
  echo "STDERR:"
  echo "$RESULT" | jq -r '.StandardErrorContent'
}

###############################################################################
# 7. EXAMPLE: COMPLETE WORKFLOW
###############################################################################

example_complete_workflow() {
  echo "=== SSM Complete Workflow Example ==="
  echo ""
  
  # 1. Setup IAM
  echo "Step 1: Setting up IAM..."
  setup_ssm_iam_role "MyEC2SSMRole"
  setup_ssm_instance_profile "MyEC2SSMRole" "MyEC2SSMProfile"
  echo ""
  
  # 2. Launch instance
  echo "Step 2: Launching EC2 instance..."
  INSTANCE_ID=$(launch_instance_with_ssm \
    "ami-0c55b159cbfafe1f0" \
    "t2.micro" \
    "" \
    "us-east-1")
  echo ""
  
  # 3. Run test
  echo "Step 3: Running system test..."
  test_ssm_basic "$INSTANCE_ID" "us-east-1"
  echo ""
  
  # 4. Upload file
  echo "Step 4: Uploading test file..."
  echo "Hello from SSM!" > /tmp/test-file.txt
  ssm_upload_file "/tmp/test-file.txt" "$INSTANCE_ID" "/tmp/received-file.txt"
  echo ""
  
  # 5. Verify
  echo "Step 5: Verifying uploaded file..."
  COMMANDS='["cat /tmp/received-file.txt"]'
  ssm_run_command_blocking "$INSTANCE_ID" "$COMMANDS" "us-east-1"
  echo ""
  
  echo "✓ Complete workflow finished!"
  echo ""
  echo "Instance: $INSTANCE_ID"
  echo "Region: us-east-1"
  echo ""
  echo "To terminate: aws ec2 terminate-instances --instance-ids $INSTANCE_ID"
}

###############################################################################
# 8. DISPLAY HELP
###############################################################################

show_help() {
  cat <<EOF
AWS EC2 SSM Session Manager - Function Library

SETUP FUNCTIONS:
  setup_ssm_iam_role [ROLE_NAME] [REGION]
    Create IAM role with SSM permissions
  
  setup_ssm_instance_profile [ROLE_NAME] [PROFILE_NAME] [REGION]
    Create instance profile for EC2

INSTANCE FUNCTIONS:
  launch_instance_with_ssm [IMAGE_ID] [INSTANCE_TYPE] [SECURITY_GROUP_ID] [REGION]
    Launch EC2 instance with SSM capability

WAIT FUNCTIONS:
  wait_for_ssm_agent [INSTANCE_ID] [REGION] [MAX_WAIT_SECONDS]
    Poll until SSM Agent is Online
  
  wait_for_command [COMMAND_ID] [INSTANCE_ID] [REGION] [MAX_WAIT_SECONDS]
    Poll until command completes

COMMAND FUNCTIONS:
  ssm_send_command [INSTANCE_ID] [COMMANDS_JSON] [REGION]
    Send command and return COMMAND_ID
  
  ssm_run_command_blocking [INSTANCE_ID] [COMMANDS_JSON] [REGION]
    Send command and wait for result

FILE TRANSFER FUNCTIONS:
  ssm_upload_file [LOCAL_FILE] [INSTANCE_ID] [REMOTE_PATH] [S3_BUCKET] [REGION]
    Upload file from local to EC2
  
  ssm_download_file [INSTANCE_ID] [REMOTE_FILE] [LOCAL_DEST] [S3_BUCKET] [REGION]
    Download file from EC2 to local

TEST FUNCTIONS:
  test_ssm_basic [INSTANCE_ID] [REGION]
    Run basic system information test
  
  test_ssm_with_errors [INSTANCE_ID] [REGION]
    Test error handling

EXAMPLES:
  example_complete_workflow
    Run complete setup, launch, test, and file transfer workflow

USAGE:
  1. Source this file: source aws-ec2-ssm-examples.sh
  2. Call functions directly: wait_for_ssm_agent i-1234567890abcdef0
  3. Run example: example_complete_workflow

REQUIREMENTS:
  - AWS CLI configured with credentials
  - jq installed (for JSON parsing)
  - Session Manager plugin installed (for interactive sessions)

EOF
}

# If script is run directly (not sourced)
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  case "${1:-help}" in
    help|--help|-h)
      show_help
      ;;
    example)
      example_complete_workflow
      ;;
    *)
      echo "Unknown command: $1"
      show_help
      exit 1
      ;;
  esac
fi
