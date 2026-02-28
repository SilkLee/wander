#!/bin/bash

# AWS CLI Configuration Script for WSL
# This script will configure AWS CLI with your credentials

echo "=========================================="
echo "AWS CLI Configuration for Day 10 Testing"
echo "=========================================="
echo ""

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "ERROR: AWS CLI not installed. Installing..."
    cd /tmp
    curl -s "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
    unzip -q awscliv2.zip
    sudo ./aws/install
    echo "AWS CLI installed successfully"
    echo ""
fi

# Prompt for credentials
echo "Please provide your AWS credentials:"
echo "(You can find these in AWS Console > IAM > Users > Security credentials)"
echo ""

read -p "AWS Access Key ID: " AWS_ACCESS_KEY_ID
read -sp "AWS Secret Access Key: " AWS_SECRET_ACCESS_KEY
echo ""
read -p "Default region [ap-southeast-1]: " AWS_REGION
AWS_REGION=${AWS_REGION:-ap-southeast-1}

echo ""
echo "Configuring AWS CLI..."

# Create ~/.aws directory if it doesn't exist
mkdir -p ~/.aws

# Write credentials
cat > ~/.aws/credentials <<EOF
[default]
aws_access_key_id = ${AWS_ACCESS_KEY_ID}
aws_secret_access_key = ${AWS_SECRET_ACCESS_KEY}
EOF

# Write config
cat > ~/.aws/config <<EOF
[default]
region = ${AWS_REGION}
output = json
EOF

# Set restrictive permissions
chmod 600 ~/.aws/credentials
chmod 600 ~/.aws/config

echo ""
echo "✓ AWS CLI configured successfully!"
echo ""
echo "Testing connection..."
aws sts get-caller-identity

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ AWS credentials verified!"
    echo ""
    echo "You can now run: bash aws-ec2-test.sh"
else
    echo ""
    echo "✗ AWS credentials verification failed"
    echo "Please check your Access Key ID and Secret Access Key"
    exit 1
fi
