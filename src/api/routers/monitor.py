"""监控大盘路由

接入调度器进程状态、PG 统计、Redis 死信队列等真实数据。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from src.api.auth import require_roles
from src.api.deps import get_conn, get_task_service

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.get("/dashboard")
async def get_dashboard(user: dict = Depends(require_roles("admin", "operator"))):
    """监控大盘数据：进程状态 + PG 统计 + 死信队列"""
    conn = get_conn()
    task_service = get_task_service()

    # 运行中的 spider 进程状态
    runtime = await task_service.get_runtime_status()
    spiders = runtime.get("processes", [])

    # PG 统计
    stats = {}
    try:
        async with conn.pg.connection() as c:
            row = await (await c.execute(
                "SELECT COUNT(*) FROM spider_results"
            )).fetchone()
            stats["total_items"] = row[0] if row else 0

            row = await (await c.execute(
                "SELECT COUNT(*) FROM spider_logs WHERE level IN ('ERROR','CRITICAL')"
            )).fetchone()
            stats["total_errors"] = row[0] if row else 0
    except Exception:
        stats["total_items"] = 0
        stats["total_errors"] = 0

    # Redis 队列积压
    try:
        queue_size = 0
        cursor = 0
        while True:
            cursor, keys = await conn.redis.scan(cursor, match="queue:*", count=100)
            for key in keys:
                queue_size += await conn.redis.zcard(key)
            if cursor == 0:
                break
        stats["queue_size"] = queue_size
    except Exception:
        stats["queue_size"] = 0

    # 死信队列
    try:
        dlq_size = await conn.redis.llen("dlq:kafka")
        stats["dead_letter_size"] = dlq_size
    except Exception:
        stats["dead_letter_size"] = 0

    # 最近告警（从 PG 日志表取最近 ERROR）
    alerts = []
    if user.get("role") == "admin":
        try:
            async with conn.pg.connection() as c:
                cur = await c.execute(
                    "SELECT id, level, message, timestamp FROM spider_logs "
                    "WHERE level IN ('ERROR','CRITICAL') "
                    "ORDER BY timestamp DESC LIMIT 20"
                )
                for row in await cur.fetchall():
                    alerts.append({
                        "id": str(row[0]),
                        "level": row[1],
                        "message": row[2],
                        "timestamp": row[3].timestamp() if row[3] else 0,
                    })
        except Exception:
            pass

    return {"spiders": spiders, "alerts": alerts, "stats": stats}


@router.get("/health")
async def health_check():
    """健康检查（无需认证）"""
    from src.infra.health import HealthChecker
    conn = get_conn()
    checker = HealthChecker(conn)
    results = await checker.check_all()
    return results.to_dict()
