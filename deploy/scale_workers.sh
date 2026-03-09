#!/bin/bash
# AIspider Worker 扩展脚本
# Usage: ./deploy/scale_workers.sh <count>

set -e

WORKER_COUNT=${1:-4}

echo "🚀 扩展 Worker 到 ${WORKER_COUNT} 个实例..."

# 使用 docker-compose 扩展
if command -v docker-compose &> /dev/null; then
    docker-compose up -d --scale worker=${WORKER_COUNT}
    echo "✅ Worker 已扩展到 ${WORKER_COUNT} 个实例"
else
    echo "❌ 未找到 docker-compose 命令"
    exit 1
fi

# 显示运行状态
echo ""
echo "📊 当前 Worker 状态:"
docker-compose ps worker
