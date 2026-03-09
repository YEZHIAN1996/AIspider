#!/bin/bash
# AIspider 健康检查脚本
# Usage: ./deploy/health_check.sh

set -e

echo "🔍 AIspider 健康检查..."
echo ""

# 检查是否使用 Docker 部署
if docker ps | grep -q aispider; then
    echo "📦 检测到 Docker 部署模式"
    echo ""

    # 通过 API 健康检查接口检查所有组件
    echo "1️⃣ 检查所有组件状态..."
    HEALTH=$(curl -s http://localhost:8000/api/v1/monitor/health)

    if echo "$HEALTH" | grep -q '"healthy":true'; then
        echo "   ✅ 所有组件正常"
        echo ""
        echo "   详细状态："
        echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
    else
        echo "   ❌ 部分组件异常"
        echo "$HEALTH" | python3 -m json.tool 2>/dev/null || echo "$HEALTH"
        exit 1
    fi
else
    echo "💻 检测到本地部署模式"
    echo ""

    # 检查 API 服务
    echo "1️⃣ 检查 API 服务..."
    if curl -s http://localhost:8000/metrics > /dev/null; then
        echo "   ✅ API 服务正常"
    else
        echo "   ❌ API 服务异常"
    fi

    # 检查 Redis
    echo "2️⃣ 检查 Redis..."
    if redis-cli ping > /dev/null 2>&1; then
        echo "   ✅ Redis 正常"
    else
        echo "   ❌ Redis 异常"
    fi

    # 检查 PostgreSQL
    echo "3️⃣ 检查 PostgreSQL..."
    if pg_isready -h localhost > /dev/null 2>&1; then
        echo "   ✅ PostgreSQL 正常"
    else
        echo "   ❌ PostgreSQL 异常"
    fi

    # 检查 Kafka
    echo "4️⃣ 检查 Kafka..."
    if nc -z localhost 9092 > /dev/null 2>&1; then
        echo "   ✅ Kafka 正常"
    else
        echo "   ❌ Kafka 异常"
    fi
fi

echo ""
echo "✅ 健康检查完成"
