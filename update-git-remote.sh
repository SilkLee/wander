#!/bin/bash
#
# Update Git Remote URL after GitHub repo rename
# 在GitHub仓库重命名后更新本地remote URL
#

set -e

echo "========================================"
echo "更新Git Remote URL"
echo "========================================"
echo ""

OLD_URL="https://github.com/SilkLee/wander.git"
NEW_URL="https://github.com/SilkLee/workflow-ai.git"

echo "当前remote URL:"
git remote -v
echo ""

# Extract token from current URL if present
CURRENT_URL=$(git remote get-url origin)
if [[ $CURRENT_URL == *"ghp_"* ]]; then
    # Extract token
    TOKEN=$(echo $CURRENT_URL | grep -oP 'https://\K[^@]+')
    NEW_URL_WITH_TOKEN="https://${TOKEN}@github.com/SilkLee/workflow-ai.git"
    
    echo "检测到Personal Access Token，将保留在新URL中"
    echo ""
    echo "设置新的remote URL (带token):"
    git remote set-url origin "$NEW_URL_WITH_TOKEN"
else
    echo "设置新的remote URL:"
    git remote set-url origin "$NEW_URL"
fi

echo ""
echo "更新后的remote URL:"
git remote -v
echo ""

echo "========================================"
echo "✓ Remote URL已更新"
echo "========================================"
echo ""
echo "验证连接:"
git ls-remote --heads origin | head -3
echo ""
echo "✓ 连接成功！"
