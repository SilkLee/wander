#!/bin/bash
#
# EC2 SSM Connection Script (Corporate SSL Workaround)
# Usage: bash connect-ec2.sh [instance-id]
#

set -e

# Default instance ID
INSTANCE_ID="${1:-i-0b00972987f6bfb9c}"
REGION="ap-southeast-1"

# Corporate SSL workaround
export PYTHONHTTPSVERIFY=0
export REQUESTS_CA_BUNDLE=''
export PYTHONWARNINGS="ignore:Unverified HTTPS request"

echo "========================================="
echo "连接到EC2实例: $INSTANCE_ID"
echo "========================================="
echo ""

# Check instance status
echo "检查实例状态..."
STATUS=$(aws ec2 describe-instances \
    --region "$REGION" \
    --instance-ids "$INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].State.Name' \
    --output text 2>/dev/null)

if [[ "$STATUS" != "running" ]]; then
    echo "错误: 实例状态不是 running (当前: $STATUS)"
    exit 1
fi

echo "✓ 实例正在运行"

# Check SSM status
echo "检查SSM Agent状态..."
SSM_STATUS=$(aws ssm describe-instance-information \
    --region "$REGION" \
    --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
    --query 'InstanceInformationList[0].PingStatus' \
    --output text 2>/dev/null)

if [[ "$SSM_STATUS" != "Online" ]]; then
    echo "错误: SSM Agent状态不是 Online (当前: $SSM_STATUS)"
    exit 1
fi

echo "✓ SSM Agent 在线"
echo ""
echo "========================================="
echo "开始连接... (输入 'exit' 退出)"
echo "========================================="
echo ""

# Start session (suppress warnings)
aws ssm start-session \
    --region "$REGION" \
    --target "$INSTANCE_ID" 2>/dev/null

echo ""
echo "========================================="
echo "连接已断开"
echo "========================================="
