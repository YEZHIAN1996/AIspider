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
ssh -t ${REMOTE_HOST} << 'EOF'
set -e

cd ~/aispider

# 检查并安装系统依赖
echo "📦 检查系统依赖..."
if ! dpkg -l | grep -q python3-venv; then
    echo "安装 python3-venv..."
    sudo apt update
    sudo apt install -y python3-venv python3-pip
fi

# 创建虚拟环境
echo "🔧 创建虚拟环境..."
python3 -m venv .venv

# 激活虚拟环境并安装依赖
echo "📦 安装 Python 依赖..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 启动 Worker（使用 nohup 后台运行）
echo "🚀 启动 Worker..."
nohup python3 main.py worker > worker.log 2>&1 &
echo $! > worker.pid

echo "✅ Worker 已启动，PID: $(cat worker.pid)"
echo "📝 日志文件: ~/aispider/worker.log"
EOF

echo ""
echo "✅ 远程 Worker 部署完成"
echo "💡 查看日志: ssh ${REMOTE_HOST} 'tail -f ~/aispider/worker.log'"
echo "💡 停止 Worker: ssh ${REMOTE_HOST} 'kill \$(cat ~/aispider/worker.pid)'"
