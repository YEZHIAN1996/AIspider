#!/bin/bash
# AIspider 远程 Worker 添加脚本
# Usage: ./deploy/add_remote_worker.sh <user@host>

set -e

REMOTE_HOST=$1

if [ -z "$REMOTE_HOST" ]; then
    echo "❌ 请指定远程主机: ./deploy/add_remote_worker.sh user@host"
    exit 1
fi

echo "🚀 在远程主机 ${REMOTE_HOST} 上部署 Worker..."

# 复制项目文件
echo "📦 复制项目文件..."
rsync -avz --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
    ./ ${REMOTE_HOST}:~/aispider/

# 远程执行部署
echo "🔧 远程部署..."
ssh ${REMOTE_HOST} << 'EOF'
cd ~/aispider
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py worker &
EOF

echo "✅ 远程 Worker 部署完成"
