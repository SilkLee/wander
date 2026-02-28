#!/bin/bash
# 快速创建一个测试EC2实例用于SSM连接体验
# 使用现有的IAM role，30分钟后自动终止

set -e

REGION="ap-southeast-1"
INSTANCE_TYPE="t3.micro"  # 最小实例，省钱
AMI_ID="ami-0ac0e4288aa341886"  # Amazon Linux 2023
ROLE_NAME="WorkflowAI-SSM-FixedRole"
INSTANCE_PROFILE_NAME="WorkflowAI-SSM-InstanceProfile"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}创建测试EC2实例（用于SSM连接体验）${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 设置SSL忽略
export AWS_CLI_SSL_NO_VERIFY=1

# 检查IAM role是否存在
echo "检查IAM role..."
if ! aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
    echo -e "${RED}错误: IAM role $ROLE_NAME 不存在${NC}"
    echo "请先运行 aws-ec2-test-ssm.sh 创建必要的IAM资源"
    exit 1
fi
echo -e "${GREEN}✓ IAM role 已存在${NC}"
echo ""

# UserData脚本 - 30分钟后自动终止实例
USER_DATA=$(cat <<'EOF'
#!/bin/bash
# 简单的测试环境设置

# 记录日志
exec > >(tee /var/log/userdata.log)
exec 2>&1

echo "=== 测试EC2实例初始化 ==="
echo "启动时间: $(date)"

# 安装一些有用的工具
yum install -y htop tree

# 创建欢迎消息
cat > /etc/motd << 'MOTD'
========================================
欢迎使用 WorkflowAI 测试 EC2 实例
========================================

这是一个用于SSM连接体验的临时实例
将在30分钟后自动终止

常用命令:
  - htop          查看系统资源
  - df -h         查看磁盘空间
  - free -h       查看内存使用
  - tree /home    查看目录结构

退出: 输入 exit

========================================
MOTD

# 30分钟后自动关闭实例（防止忘记）
(sleep 1800 && shutdown -h now) &

echo "初始化完成"
echo "READY" > /tmp/ready

EOF
)

# 启动EC2实例
echo "启动EC2实例..."
INSTANCE_ID=$(aws ec2 run-instances \
    --region $REGION \
    --image-id $AMI_ID \
    --instance-type $INSTANCE_TYPE \
    --iam-instance-profile Name=$INSTANCE_PROFILE_NAME \
    --user-data "$USER_DATA" \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=workflow-ai-test-ssm}]" \
    --query 'Instances[0].InstanceId' \
    --output text)

echo -e "${GREEN}✓ 实例已创建: $INSTANCE_ID${NC}"
echo ""

# 等待实例运行
echo "等待实例启动..."
aws ec2 wait instance-running --region $REGION --instance-ids $INSTANCE_ID
echo -e "${GREEN}✓ 实例正在运行${NC}"
echo ""

# 等待SSM Agent就绪
echo "等待SSM Agent就绪（可能需要1-2分钟）..."
MAX_ATTEMPTS=30
ATTEMPT=0
while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
    if aws ssm describe-instance-information \
        --region $REGION \
        --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
        --query 'InstanceInformationList[0].PingStatus' \
        --output text 2>/dev/null | grep -q "Online"; then
        echo -e "${GREEN}✓ SSM Agent 已就绪${NC}"
        break
    fi
    ATTEMPT=$((ATTEMPT + 1))
    echo "  尝试 $ATTEMPT/$MAX_ATTEMPTS..."
    sleep 5
done

if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
    echo -e "${RED}✗ SSM Agent 未能及时上线${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}EC2实例已就绪！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}连接命令：${NC}"
echo ""
echo -e "  ${GREEN}export AWS_CLI_SSL_NO_VERIFY=1${NC}"
echo -e "  ${GREEN}aws ssm start-session --region $REGION --target $INSTANCE_ID${NC}"
echo ""
echo -e "${YELLOW}或者一行命令：${NC}"
echo ""
echo -e "  ${GREEN}export AWS_CLI_SSL_NO_VERIFY=1 && aws ssm start-session --region ap-southeast-1 --target $INSTANCE_ID${NC}"
echo ""
echo -e "${YELLOW}重要提示：${NC}"
echo "  • 这是一个临时测试实例（t3.micro）"
echo "  • 将在 ${YELLOW}30分钟后自动关闭${NC} 防止遗忘"
echo "  • 退出连接: 输入 ${GREEN}exit${NC}"
echo "  • 手动终止: ${GREEN}aws ec2 terminate-instances --region $REGION --instance-ids $INSTANCE_ID${NC}"
echo ""
echo -e "${BLUE}========================================${NC}"
echo ""

# 保存instance ID到文件，方便后续清理
echo "$INSTANCE_ID" > /tmp/test-ec2-instance-id.txt
echo "实例ID已保存到: /tmp/test-ec2-instance-id.txt"
echo ""
echo "体验完成后，运行以下命令清理："
echo -e "  ${GREEN}export AWS_CLI_SSL_NO_VERIFY=1${NC}"
echo -e "  ${GREEN}aws ec2 terminate-instances --region $REGION --instance-ids $INSTANCE_ID${NC}"
